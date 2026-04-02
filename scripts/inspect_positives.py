"""
Inspect positive (meteorite fall) samples with per-sweep anomaly scores.

Generates a ranked report and visualizations of the highest-scoring sweeps
to help identify which sweeps contain actual meteorite signatures.
"""

import torch
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse
import json
from tqdm import tqdm

import sys
sys.path.append(str(Path(__file__).parent.parent))

from rasr.models.radar_dataset import RadarSweepDataset, collate_radar_batch
from rasr.models.spatiotemporal_autoencoder import SpatioTemporalAutoencoder
from torch.utils.data import DataLoader


def inspect_positives(model, dataloader, device, output_dir, top_n=20):
    """Compute per-sweep scores and visualize top anomalous sweeps."""
    model.eval()

    all_sweep_records = []  # (score, sample_idx, sweep_idx, metadata)
    all_data = []

    with torch.no_grad():
        sample_offset = 0
        for data, mask, metadata in tqdm(dataloader, desc="Scoring positives"):
            data = data.to(device)
            mask = mask.to(device)

            reconstruction, _ = model(data, mask)
            per_sweep_scores, _ = model.compute_anomaly_score(data, reconstruction, mask)

            batch_size = data.size(0)
            for b in range(batch_size):
                for s in range(mask.size(1)):
                    if mask[b, s]:
                        all_sweep_records.append({
                            'score': per_sweep_scores[b, s].item(),
                            'sample_idx': sample_offset + b,
                            'sweep_idx': s,
                            'filename': metadata[b]['filename'],
                            'station': metadata[b]['station'],
                        })

            all_data.append((data.cpu(), reconstruction.cpu(), mask.cpu(), metadata))
            sample_offset += batch_size

    # Sort by score descending
    all_sweep_records.sort(key=lambda r: r['score'], reverse=True)

    # Save ranked CSV
    csv_path = output_dir / 'positive_sweep_scores.csv'
    with open(csv_path, 'w') as f:
        f.write('rank,score,filename,station,sweep_idx\n')
        for i, rec in enumerate(all_sweep_records):
            f.write(f"{i+1},{rec['score']:.6f},{rec['filename']},{rec['station']},{rec['sweep_idx']}\n")
    print(f"Sweep scores saved to {csv_path}")

    # Print top sweeps
    print(f"\nTop {top_n} anomalous sweeps:")
    print(f"{'Rank':>4}  {'Score':>10}  {'Sweep':>5}  {'Station':<8}  Filename")
    print("-" * 70)
    for i, rec in enumerate(all_sweep_records[:top_n]):
        print(f"{i+1:>4}  {rec['score']:>10.6f}  {rec['sweep_idx']:>5}  {rec['station']:<8}  {rec['filename']}")

    # Visualize top N sweeps: original, reconstruction, difference
    vis_dir = output_dir / 'top_sweeps'
    vis_dir.mkdir(exist_ok=True)

    # Build flat index for quick lookup
    flat_data = []
    flat_recon = []
    flat_mask = []
    flat_metadata = []
    for data, recon, mask, metadata in all_data:
        for b in range(data.size(0)):
            flat_data.append(data[b])
            flat_recon.append(recon[b])
            flat_mask.append(mask[b])
            flat_metadata.append(metadata[b])

    for i, rec in enumerate(all_sweep_records[:top_n]):
        si = rec['sample_idx']
        sw = rec['sweep_idx']

        orig = flat_data[si][sw].numpy()     # (num_fields, H, W)
        recon = flat_recon[si][sw].numpy()
        diff = np.abs(orig - recon)

        num_fields = orig.shape[0]
        fig, axes = plt.subplots(num_fields, 3, figsize=(12, 4 * num_fields),
                                 squeeze=False)

        for f in range(num_fields):
            axes[f, 0].imshow(orig[f], cmap='RdBu_r', vmin=-1, vmax=1)
            axes[f, 0].set_title('Original')
            axes[f, 0].axis('off')

            axes[f, 1].imshow(recon[f], cmap='RdBu_r', vmin=-1, vmax=1)
            axes[f, 1].set_title('Reconstruction')
            axes[f, 1].axis('off')

            axes[f, 2].imshow(diff[f], cmap='hot', vmin=0, vmax=0.5)
            axes[f, 2].set_title('|Difference|')
            axes[f, 2].axis('off')

        fig.suptitle(
            f"Rank {i+1} | Score: {rec['score']:.4f} | "
            f"{rec['station']}/{rec['filename']} | Sweep {sw}",
            fontsize=11, fontweight='bold'
        )
        plt.tight_layout()
        plt.savefig(vis_dir / f'rank_{i+1:03d}.png', dpi=150, bbox_inches='tight')
        plt.close()

    print(f"\nTop {top_n} sweep visualizations saved to {vis_dir}")

    # Summary stats per file
    print(f"\nPer-file summary (max sweep score):")
    file_scores = {}
    for rec in all_sweep_records:
        key = f"{rec['station']}/{rec['filename']}"
        if key not in file_scores:
            file_scores[key] = rec['score']
        else:
            file_scores[key] = max(file_scores[key], rec['score'])

    sorted_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
    print(f"{'Rank':>4}  {'Max Score':>10}  File")
    print("-" * 50)
    for i, (fname, score) in enumerate(sorted_files[:20]):
        print(f"{i+1:>4}  {score:>10.6f}  {fname}")


def main():
    parser = argparse.ArgumentParser(description='Inspect positive samples')
    parser.add_argument('config', nargs='?', default='configs/train_poc.json')
    parser.add_argument('--positive_data_dir', default='data/positive')
    parser.add_argument('--output_dir', default='evaluation_results/inspect_positives')
    parser.add_argument('--top_n', type=int, default=20)
    args = parser.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)

    device = cfg.get('device', 'cuda' if torch.cuda.is_available() else 'cpu')
    image_size = (cfg['image_size'], cfg['image_size'])
    fields = cfg.get('fields', ['reflectivity'])
    checkpoint_dir = Path(cfg['checkpoint_dir'])

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load model
    model = SpatioTemporalAutoencoder(
        num_fields=len(fields),
        image_size=image_size,
        spatial_latent_dim=cfg['spatial_latent_dim'],
        temporal_hidden_dim=cfg['temporal_hidden_dim'],
        max_sweeps=cfg['max_sweeps'],
    )
    model_path = checkpoint_dir / 'best_model.pt'
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    model = model.to(device)
    model.eval()
    print(f"Loaded model from {model_path}")

    # Load positive dataset
    positive_dataset = RadarSweepDataset(
        data_dir=args.positive_data_dir,
        fields=fields,
        image_size=image_size,
        max_sweeps=cfg['max_sweeps'],
        cache_dir=cfg.get('cache_dir'),
        preload_workers=cfg.get('preload_workers', 8),
    )
    loader = DataLoader(positive_dataset, batch_size=cfg['batch_size'],
                        shuffle=False, collate_fn=collate_radar_batch, num_workers=0)

    inspect_positives(model, loader, device, output_dir, top_n=args.top_n)


if __name__ == '__main__':
    main()
