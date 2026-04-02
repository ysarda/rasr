"""
Visualization script for trained autoencoder model.
Shows original, reconstruction, and error maps.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import torch
import numpy as np
import matplotlib.pyplot as plt
import argparse

from rasr.models.radar_dataset import RadarSweepDataset, collate_radar_batch
from rasr.models.spatiotemporal_autoencoder import SpatioTemporalAutoencoder
from torch.utils.data import DataLoader


def visualize_reconstructions(model, dataset, device, output_dir, num_samples=5):
    """Generate visualization of original vs reconstruction."""
    model.eval()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    field_names = ['Velocity', 'Reflectivity', 'Spectrum Width']

    for sample_idx in range(min(num_samples, len(dataset))):
        result = dataset[sample_idx]
        if result is None:
            continue

        data, mask, metadata = result

        # Add batch dimension
        data = data.unsqueeze(0).to(device)
        mask = mask.unsqueeze(0).to(device)

        with torch.no_grad():
            reconstruction, latent = model(data, mask)

        # Move to CPU for visualization
        data = data.cpu().numpy()[0]  # (sweeps, fields, H, W)
        reconstruction = reconstruction.cpu().numpy()[0]
        mask = mask.cpu().numpy()[0]

        # Find sweep with most data
        valid_sweeps = np.where(mask)[0]
        if len(valid_sweeps) == 0:
            continue

        best_sweep = valid_sweeps[0]
        best_count = 0
        for sweep_idx in valid_sweeps:
            count = np.sum(data[sweep_idx] != 0)
            if count > best_count:
                best_count = count
                best_sweep = sweep_idx

        # Create visualization: 3 rows (original, reconstruction, error) x 3 cols (fields)
        fig, axes = plt.subplots(3, 3, figsize=(15, 12))

        for field_idx, field_name in enumerate(field_names):
            orig = data[best_sweep, field_idx]
            recon = reconstruction[best_sweep, field_idx]
            error = np.abs(orig - recon)

            # Original
            im0 = axes[0, field_idx].imshow(orig, cmap='RdBu_r', vmin=-1, vmax=1)
            axes[0, field_idx].set_title(f'Original {field_name}')
            axes[0, field_idx].axis('off')
            plt.colorbar(im0, ax=axes[0, field_idx], fraction=0.046)

            # Reconstruction
            im1 = axes[1, field_idx].imshow(recon, cmap='RdBu_r', vmin=-1, vmax=1)
            axes[1, field_idx].set_title(f'Reconstructed {field_name}')
            axes[1, field_idx].axis('off')
            plt.colorbar(im1, ax=axes[1, field_idx], fraction=0.046)

            # Error
            im2 = axes[2, field_idx].imshow(error, cmap='hot', vmin=0, vmax=0.5)
            axes[2, field_idx].set_title(f'Error {field_name} (MAE: {error.mean():.4f})')
            axes[2, field_idx].axis('off')
            plt.colorbar(im2, ax=axes[2, field_idx], fraction=0.046)

        plt.suptitle(f'Sample: {metadata["filename"]} (Sweep {best_sweep})', fontsize=14)
        plt.tight_layout()

        save_path = output_dir / f'reconstruction_{sample_idx}.png'
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"Saved: {save_path}")


def visualize_anomaly_scores(model, dataset, device, output_dir, num_samples=20):
    """Compute and visualize anomaly scores."""
    model.eval()
    output_dir = Path(output_dir)

    scores = []
    filenames = []

    loader = DataLoader(
        dataset,
        batch_size=1,
        shuffle=False,
        collate_fn=collate_radar_batch,
        num_workers=0
    )

    print(f"\nComputing anomaly scores for {min(num_samples, len(dataset))} samples...")

    for i, (data, mask, metadata) in enumerate(loader):
        if i >= num_samples:
            break
        if data is None:
            continue

        data = data.to(device)
        mask = mask.to(device)

        with torch.no_grad():
            reconstruction, _ = model(data, mask)
            _, sample_score = model.compute_anomaly_score(data, reconstruction, mask)

        scores.append(sample_score.cpu().numpy()[0])
        filenames.append(metadata[0]['filename'])

    # Plot anomaly score distribution
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(range(len(scores)), scores)
    ax.set_xlabel('Sample Index')
    ax.set_ylabel('Anomaly Score (MSE)')
    ax.set_title('Anomaly Scores for Samples')
    ax.axhline(y=np.mean(scores), color='r', linestyle='--', label=f'Mean: {np.mean(scores):.4f}')
    ax.legend()

    plt.tight_layout()
    save_path = output_dir / 'anomaly_scores.png'
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"Saved: {save_path}")

    # Print statistics
    print(f"\nAnomaly Score Statistics:")
    print(f"  Mean: {np.mean(scores):.6f}")
    print(f"  Std:  {np.std(scores):.6f}")
    print(f"  Min:  {np.min(scores):.6f}")
    print(f"  Max:  {np.max(scores):.6f}")


def visualize_latent_space(model, dataset, device, output_dir, num_samples=50):
    """Visualize latent space representations."""
    model.eval()
    output_dir = Path(output_dir)

    latents = []

    loader = DataLoader(
        dataset,
        batch_size=1,
        shuffle=False,
        collate_fn=collate_radar_batch,
        num_workers=0
    )

    print(f"\nExtracting latent representations...")

    for i, (data, mask, metadata) in enumerate(loader):
        if i >= num_samples:
            break
        if data is None:
            continue

        data = data.to(device)
        mask = mask.to(device)

        with torch.no_grad():
            _, latent = model(data, mask)
            # latent shape: (batch, seq_len, hidden_dim*2)
            # Take mean across sequence
            latent_mean = latent.mean(dim=1).cpu().numpy()[0]
            latents.append(latent_mean)

    latents = np.array(latents)
    print(f"Latent shape: {latents.shape}")

    # Visualize first few dimensions
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # Heatmap of latent vectors
    im = axes[0, 0].imshow(latents[:, :64], aspect='auto', cmap='RdBu_r')
    axes[0, 0].set_xlabel('Latent Dimension')
    axes[0, 0].set_ylabel('Sample')
    axes[0, 0].set_title('Latent Representations (first 64 dims)')
    plt.colorbar(im, ax=axes[0, 0])

    # Distribution of latent values
    axes[0, 1].hist(latents.flatten(), bins=50)
    axes[0, 1].set_xlabel('Value')
    axes[0, 1].set_ylabel('Count')
    axes[0, 1].set_title('Latent Value Distribution')

    # Mean activation per dimension
    axes[1, 0].bar(range(min(64, latents.shape[1])), np.mean(np.abs(latents[:, :64]), axis=0))
    axes[1, 0].set_xlabel('Latent Dimension')
    axes[1, 0].set_ylabel('Mean |Activation|')
    axes[1, 0].set_title('Mean Absolute Activation per Dimension')

    # Variance per dimension
    axes[1, 1].bar(range(min(64, latents.shape[1])), np.var(latents[:, :64], axis=0))
    axes[1, 1].set_xlabel('Latent Dimension')
    axes[1, 1].set_ylabel('Variance')
    axes[1, 1].set_title('Variance per Dimension')

    plt.tight_layout()
    save_path = output_dir / 'latent_space.png'
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"Saved: {save_path}")


def main():
    parser = argparse.ArgumentParser(description='Visualize trained autoencoder')
    parser.add_argument('--model_path', type=str, default='checkpoints/best_model.pt',
                        help='Path to trained model')
    parser.add_argument('--data_dir', type=str, default='data/null',
                        help='Directory containing radar data')
    parser.add_argument('--output_dir', type=str, default='checkpoints/visualizations',
                        help='Output directory for visualizations')
    parser.add_argument('--num_samples', type=int, default=5,
                        help='Number of samples to visualize')
    parser.add_argument('--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu',
                        help='Device to use')
    parser.add_argument('--image_size', type=int, default=128,
                        help='Image size (height=width) for radar grid (default: 128)')

    args = parser.parse_args()

    print(f"Loading model from {args.model_path}")
    print(f"Device: {args.device}")

    # Create model
    image_size = (args.image_size, args.image_size)
    model = SpatioTemporalAutoencoder(
        num_fields=3,
        image_size=image_size,
        spatial_latent_dim=512,
        temporal_hidden_dim=256,
        max_sweeps=12
    )

    # Load weights
    model.load_state_dict(torch.load(args.model_path, map_location=args.device))
    model = model.to(args.device)
    model.eval()

    print(f"Model loaded successfully")

    # Load dataset
    print(f"\nLoading dataset from {args.data_dir}")
    dataset = RadarSweepDataset(
        data_dir=args.data_dir,
        fields=['velocity', 'reflectivity', 'spectrum_width'],
        image_size=image_size,
        max_sweeps=12
    )

    # Generate visualizations
    print(f"\n{'='*50}")
    print("Generating reconstruction visualizations...")
    print('='*50)
    visualize_reconstructions(model, dataset, args.device, args.output_dir, args.num_samples)

    print(f"\n{'='*50}")
    print("Computing anomaly scores...")
    print('='*50)
    visualize_anomaly_scores(model, dataset, args.device, args.output_dir, num_samples=20)

    print(f"\n{'='*50}")
    print("Visualizing latent space...")
    print('='*50)
    visualize_latent_space(model, dataset, args.device, args.output_dir, num_samples=50)

    print(f"\nAll visualizations saved to {args.output_dir}")


if __name__ == "__main__":
    main()
