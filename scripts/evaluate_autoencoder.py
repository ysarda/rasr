"""
Evaluation script for Spatio-Temporal Autoencoder

Tests anomaly detection by comparing reconstruction error on:
- Null data (normal — should have low anomaly scores)
- Positive data (confirmed falls — should have high anomaly scores)
"""

import torch
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse
from tqdm import tqdm
import json
from sklearn.metrics import roc_curve, auc, precision_recall_curve, confusion_matrix

import sys
sys.path.append(str(Path(__file__).parent.parent))

from rasr.models.radar_dataset import RadarSweepDataset, collate_radar_batch
from rasr.models.spatiotemporal_autoencoder import SpatioTemporalAutoencoder
from torch.utils.data import DataLoader


def compute_anomaly_scores(model, dataloader, device):
    """Compute anomaly scores for all samples in dataloader."""
    model.eval()
    all_scores = []
    all_metadata = []

    with torch.no_grad():
        for data, mask, metadata in tqdm(dataloader, desc="Computing anomaly scores"):
            data = data.to(device)
            mask = mask.to(device)

            reconstruction, _ = model(data, mask)
            scores = model.compute_anomaly_score(data, reconstruction, mask)

            all_scores.extend(scores.cpu().numpy().tolist())
            all_metadata.extend(metadata)

    return np.array(all_scores), all_metadata


def plot_score_distributions(null_scores, positive_scores, save_path):
    """Plot histograms of anomaly scores for null vs positive data."""
    plt.figure(figsize=(12, 6))

    plt.subplot(1, 2, 1)
    bins = np.linspace(min(null_scores.min(), positive_scores.min()),
                       max(null_scores.max(), positive_scores.max()), 50)
    plt.hist(null_scores, bins=bins, alpha=0.6, label='Null (Normal)', color='blue', density=True)
    plt.hist(positive_scores, bins=bins, alpha=0.6, label='Positive (Falls)', color='red', density=True)
    plt.xlabel('Anomaly Score (Reconstruction Error)')
    plt.ylabel('Density')
    plt.title('Anomaly Score Distribution')
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 2, 2)
    plt.boxplot([null_scores, positive_scores], labels=['Null', 'Positive'])
    plt.ylabel('Anomaly Score')
    plt.title('Anomaly Score Comparison')
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Score distributions saved to {save_path}")


def plot_roc_curve(null_scores, positive_scores, save_path):
    """Plot ROC curve."""
    y_true = np.concatenate([np.zeros(len(null_scores)), np.ones(len(positive_scores))])
    y_scores = np.concatenate([null_scores, positive_scores])

    fpr, tpr, thresholds = roc_curve(y_true, y_scores)
    roc_auc = auc(fpr, tpr)

    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.3f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', label='Random')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate (Recall)')
    plt.title('ROC Curve')
    plt.legend(loc="lower right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"ROC curve saved to {save_path}")

    return fpr, tpr, thresholds, roc_auc


def plot_precision_recall_curve(null_scores, positive_scores, save_path):
    """Plot Precision-Recall curve."""
    y_true = np.concatenate([np.zeros(len(null_scores)), np.ones(len(positive_scores))])
    y_scores = np.concatenate([null_scores, positive_scores])

    precision, recall, thresholds = precision_recall_curve(y_true, y_scores)
    pr_auc = auc(recall, precision)

    plt.figure(figsize=(8, 6))
    plt.plot(recall, precision, color='darkorange', lw=2, label=f'PR curve (AUC = {pr_auc:.3f})')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve')
    plt.legend(loc="lower left")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Precision-Recall curve saved to {save_path}")

    return precision, recall, thresholds, pr_auc


def find_optimal_threshold(null_scores, positive_scores, target_fpr=0.01):
    """Find optimal threshold that achieves target false positive rate."""
    y_true = np.concatenate([np.zeros(len(null_scores)), np.ones(len(positive_scores))])
    y_scores = np.concatenate([null_scores, positive_scores])

    fpr, tpr, thresholds = roc_curve(y_true, y_scores)

    idx = np.argmin(np.abs(fpr - target_fpr))
    threshold = thresholds[idx]

    y_pred = (y_scores >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return threshold, {
        'threshold': float(threshold),
        'fpr': float(fpr[idx]),
        'tpr': float(tpr[idx]),
        'precision': float(precision),
        'recall': float(recall),
        'f1_score': float(f1),
        'true_positives': int(tp),
        'false_positives': int(fp),
        'true_negatives': int(tn),
        'false_negatives': int(fn),
    }


def main():
    parser = argparse.ArgumentParser(description='Evaluate Spatio-Temporal Autoencoder')
    parser.add_argument('config', nargs='?', default='configs/train_poc.json',
                        help='Training config (used to reconstruct model architecture)')
    parser.add_argument('--positive_data_dir', type=str, default='data/positive',
                        help='Directory containing positive (fall) radar data')
    parser.add_argument('--output_dir', type=str, default='evaluation_results',
                        help='Directory to save evaluation results')
    parser.add_argument('--target_fpr', type=float, default=0.01,
                        help='Target false positive rate for threshold selection')
    parser.add_argument('--max_samples', type=int, default=None,
                        help='Limit samples per dataset (for quick testing)')
    args = parser.parse_args()

    # Load training config to get model architecture
    with open(args.config) as f:
        cfg = json.load(f)

    device = cfg.get('device', 'cuda' if torch.cuda.is_available() else 'cpu')
    image_size = (cfg['image_size'], cfg['image_size'])
    fields = cfg.get('fields', ['velocity', 'reflectivity', 'spectrum_width'])
    checkpoint_dir = Path(cfg['checkpoint_dir'])

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load model with same architecture as training
    print("Loading model...")
    model = SpatioTemporalAutoencoder(
        num_fields=len(fields),
        image_size=image_size,
        spatial_latent_dim=cfg['spatial_latent_dim'],
        temporal_hidden_dim=cfg['temporal_hidden_dim'],
        max_sweeps=cfg['max_sweeps'],
    )

    model_path = checkpoint_dir / 'best_model.pt'
    state_dict = torch.load(model_path, map_location=device, weights_only=True)
    model.load_state_dict(state_dict)
    model = model.to(device)
    model.eval()
    print(f"Loaded {model_path}")
    print(f"  Fields: {fields}")
    print(f"  Image size: {image_size}")
    print(f"  Params: {sum(p.numel() for p in model.parameters()):,}")
    print()

    # Load null dataset (subsample for eval speed)
    print("Loading null dataset...")
    null_dataset = RadarSweepDataset(
        data_dir=cfg['data_dir'],
        fields=fields,
        image_size=image_size,
        max_sweeps=cfg['max_sweeps'],
        cache_dir=cfg.get('cache_dir'),
        max_samples=args.max_samples,
        preload_workers=cfg.get('preload_workers', 8),
    )
    null_loader = DataLoader(null_dataset, batch_size=cfg['batch_size'],
                             shuffle=False, collate_fn=collate_radar_batch, num_workers=0)

    # Load positive dataset (use cache so repeated evals skip raw loading)
    print("Loading positive dataset...")
    positive_dataset = RadarSweepDataset(
        data_dir=args.positive_data_dir,
        fields=fields,
        image_size=image_size,
        max_sweeps=cfg['max_sweeps'],
        cache_dir=cfg.get('cache_dir'),
        preload_workers=cfg.get('preload_workers', 8),
    )
    positive_loader = DataLoader(positive_dataset, batch_size=cfg['batch_size'],
                                 shuffle=False, collate_fn=collate_radar_batch, num_workers=0)

    print(f"\nNull samples: {len(null_dataset)}")
    print(f"Positive samples: {len(positive_dataset)}")
    print()

    # Compute anomaly scores
    print("Computing anomaly scores...")
    null_scores, null_metadata = compute_anomaly_scores(model, null_loader, device)
    positive_scores, positive_metadata = compute_anomaly_scores(model, positive_loader, device)

    print(f"\nNull scores:     {null_scores.mean():.6f} +/- {null_scores.std():.6f}")
    print(f"Positive scores: {positive_scores.mean():.6f} +/- {positive_scores.std():.6f}")
    print()

    # Generate plots
    plot_score_distributions(null_scores, positive_scores, output_dir / 'score_distributions.png')
    fpr, tpr, _, roc_auc = plot_roc_curve(null_scores, positive_scores, output_dir / 'roc_curve.png')
    precision, recall, _, pr_auc = plot_precision_recall_curve(
        null_scores, positive_scores, output_dir / 'precision_recall_curve.png')

    # Find optimal threshold
    threshold, metrics = find_optimal_threshold(null_scores, positive_scores, args.target_fpr)

    print(f"Optimal Threshold: {threshold:.6f}")
    print(f"  FPR:       {metrics['fpr']:.4f}")
    print(f"  Recall:    {metrics['tpr']:.4f}")
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  F1:        {metrics['f1_score']:.4f}")
    print(f"  TP: {metrics['true_positives']}  FP: {metrics['false_positives']}  "
          f"TN: {metrics['true_negatives']}  FN: {metrics['false_negatives']}")

    # Save results
    results = {
        'config': args.config,
        'model_path': str(model_path),
        'null_dataset_size': len(null_dataset),
        'positive_dataset_size': len(positive_dataset),
        'null_score_mean': float(null_scores.mean()),
        'null_score_std': float(null_scores.std()),
        'positive_score_mean': float(positive_scores.mean()),
        'positive_score_std': float(positive_scores.std()),
        'roc_auc': float(roc_auc),
        'pr_auc': float(pr_auc),
        'optimal_threshold': metrics,
    }

    with open(output_dir / 'evaluation_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {output_dir}")


if __name__ == "__main__":
    main()
