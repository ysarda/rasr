"""
Training script for Spatio-Temporal Autoencoder

Phase 1: Unsupervised training on null data to learn "normal" radar patterns
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from torch.cuda.amp import GradScaler, autocast
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse
from tqdm import tqdm
import json
from datetime import datetime

# Add parent directory to path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from rasr.models.radar_dataset import RadarSweepDataset, collate_radar_batch
from rasr.models.spatiotemporal_autoencoder import SpatioTemporalAutoencoder


def masked_mse_loss(reconstruction, data, mask, signal_weight=0.95):
    """
    Weighted MSE loss: signal pixels get signal_weight, empty pixels get (1 - signal_weight).
    Keeps focus on reconstructing real signal while still penalizing hallucinated noise.
    """
    # Sweep validity mask: (B, T) -> (B, T, 1, 1, 1)
    sweep_mask = mask.unsqueeze(2).unsqueeze(3).unsqueeze(4).float()
    # Per-pixel weights: signal vs empty
    signal_mask = (data != 0).float()
    weights = signal_mask * signal_weight + (1 - signal_mask) * (1 - signal_weight)
    weights = weights * sweep_mask
    # Weighted MSE
    diff_sq = (reconstruction - data) ** 2
    return (diff_sq * weights).sum() / weights.sum().clamp(min=1)


def train_epoch(model, dataloader, optimizer, device, scaler=None, signal_weight=0.95):
    """Train for one epoch with optional mixed precision."""
    model.train()
    total_loss = 0
    num_batches = 0
    use_amp = scaler is not None

    progress_bar = tqdm(dataloader, desc="Training")
    for data, mask, metadata in progress_bar:
        # Skip if entire batch failed to load
        if data is None:
            continue

        # Move to device
        data = data.to(device)
        mask = mask.to(device)

        optimizer.zero_grad()

        # Forward pass with optional mixed precision
        if use_amp:
            with autocast():
                reconstruction, latent = model(data, mask)
                loss = masked_mse_loss(reconstruction, data, mask, signal_weight)

            # Backward pass with scaler
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            scaler.step(optimizer)
            scaler.update()
        else:
            reconstruction, latent = model(data, mask)
            loss = masked_mse_loss(reconstruction, data, mask, signal_weight)

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

        # Track loss
        total_loss += loss.item()
        num_batches += 1

        # Update progress bar
        progress_bar.set_postfix({'loss': loss.item()})

    return total_loss / num_batches if num_batches > 0 else 0.0


def validate_epoch(model, dataloader, device, use_amp=False, signal_weight=0.95):
    """Validate for one epoch with optional mixed precision."""
    model.eval()
    total_loss = 0
    anomaly_scores = []
    num_batches = 0

    with torch.no_grad():
        for data, mask, metadata in tqdm(dataloader, desc="Validation"):
            data = data.to(device)
            mask = mask.to(device)

            # Forward pass with optional mixed precision
            if use_amp:
                with autocast():
                    reconstruction, latent = model(data, mask)
                    loss = masked_mse_loss(reconstruction, data, mask, signal_weight)
            else:
                reconstruction, latent = model(data, mask)
                loss = masked_mse_loss(reconstruction, data, mask, signal_weight)

            total_loss += loss.item()
            num_batches += 1

            # Compute anomaly scores (use sample-level max-over-sweeps)
            _, sample_scores = model.compute_anomaly_score(data, reconstruction, mask)
            anomaly_scores.extend(sample_scores.cpu().numpy().tolist())

    return total_loss / num_batches, np.array(anomaly_scores)


def save_checkpoint(model, optimizer, epoch, train_loss, val_loss, checkpoint_dir,
                    scaler=None, scheduler=None, train_losses=None, val_losses=None, best_val_loss=None):
    """Save model checkpoint (overwrites latest)."""
    checkpoint_path = checkpoint_dir / "latest_checkpoint.pt"

    checkpoint = {
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'scheduler_state_dict': scheduler.state_dict() if scheduler is not None else None,
        'train_loss': train_loss,
        'val_loss': val_loss,
        'train_losses': train_losses,
        'val_losses': val_losses,
        'best_val_loss': best_val_loss,
    }

    if scaler is not None:
        checkpoint['scaler_state_dict'] = scaler.state_dict()

    torch.save(checkpoint, checkpoint_path)

    print(f"Checkpoint saved: {checkpoint_path}")


def visualize_reconstructions(model, dataloader, device, save_dir, field_names=None,
                              num_samples=4, epoch=None, fixed_batch=None):
    """Visualize reconstructions. If epoch is given, saves numbered frames for timelapse.

    Returns the fixed_batch (data, mask) so the same samples are used every epoch.
    """
    model.eval()

    # Use fixed batch for consistency across epochs
    if fixed_batch is not None:
        data, mask = fixed_batch
    else:
        data, mask, metadata = next(iter(dataloader))
    data = data.to(device)
    mask = mask.to(device)

    with torch.no_grad():
        reconstruction, _ = model(data, mask)

    num_samples = min(num_samples, data.size(0))
    suffix = f'_epoch{epoch:04d}' if epoch is not None else ''

    for sample_idx in range(num_samples):
        valid_sweeps = mask[sample_idx].nonzero(as_tuple=True)[0]
        if len(valid_sweeps) == 0:
            continue

        sweep_idx = valid_sweeps[0].item()
        original = data[sample_idx, sweep_idx].cpu().numpy()
        recon = reconstruction[sample_idx, sweep_idx].cpu().numpy()

        num_fields = original.shape[0]
        names = field_names or [f'Field {i}' for i in range(num_fields)]

        if num_fields == 1:
            fig, axes = plt.subplots(1, 2, figsize=(10, 5))
            axes[0].imshow(original[0], cmap='RdBu_r', vmin=-1, vmax=1)
            axes[0].set_title(f'Original {names[0]}')
            axes[0].axis('off')
            axes[1].imshow(recon[0], cmap='RdBu_r', vmin=-1, vmax=1)
            axes[1].set_title(f'Reconstructed {names[0]}')
            axes[1].axis('off')
        else:
            fig, axes = plt.subplots(2, max(num_fields, 2), figsize=(5 * max(num_fields, 2), 8))
            for field_idx in range(num_fields):
                axes[0, field_idx].imshow(original[field_idx], cmap='RdBu_r', vmin=-1, vmax=1)
                axes[0, field_idx].set_title(f'Original {names[field_idx]}')
                axes[0, field_idx].axis('off')
                axes[1, field_idx].imshow(recon[field_idx], cmap='RdBu_r', vmin=-1, vmax=1)
                axes[1, field_idx].set_title(f'Reconstructed {names[field_idx]}')
                axes[1, field_idx].axis('off')
            for field_idx in range(num_fields, axes.shape[1]):
                axes[0, field_idx].axis('off')
                axes[1, field_idx].axis('off')

        if epoch is not None:
            fig.suptitle(f'Epoch {epoch}', fontsize=14, fontweight='bold')

        plt.tight_layout()
        save_path = save_dir / f'reconstruction_sample_{sample_idx}{suffix}.png'
        plt.savefig(save_path, dpi=100, bbox_inches='tight')
        plt.close()

    return (data.cpu(), mask.cpu())


def plot_training_curves(train_losses, val_losses, save_dir):
    """Plot training and validation loss curves. Overwrites the same file for live viewing."""
    plt.figure(figsize=(10, 6))
    epochs = range(1, len(train_losses) + 1)
    plt.plot(epochs, train_losses, label='Training Loss')
    plt.plot(epochs, val_losses, label='Validation Loss')
    plt.xlabel('Epoch')
    plt.ylabel('MSE Loss')
    plt.title('Training and Validation Loss')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    save_path = save_dir / 'training_curves.png'
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def build_timelapse_gif(save_dir, num_samples=4, fps=5):
    """Compile per-epoch reconstruction frames into a GIF."""
    from PIL import Image
    import glob

    for sample_idx in range(num_samples):
        pattern = str(save_dir / f'reconstruction_sample_{sample_idx}_epoch*.png')
        frames_paths = sorted(glob.glob(pattern))
        if not frames_paths:
            continue

        frames = [Image.open(p) for p in frames_paths]
        gif_path = save_dir / f'reconstruction_timelapse_sample_{sample_idx}.gif'
        frames[0].save(
            gif_path, save_all=True, append_images=frames[1:],
            duration=1000 // fps, loop=0
        )
        print(f"Timelapse GIF saved to {gif_path}")


def load_config(config_path):
    """Load training config from JSON, with defaults for any missing keys."""
    defaults = {
        "data_dir": "data/null",
        "checkpoint_dir": "checkpoints",
        "batch_size": 4,
        "num_epochs": 50,
        "learning_rate": 1e-4,
        "val_split": 0.15,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "mixed_precision": True,
        "image_size": 128,
        "spatial_latent_dim": 512,
        "temporal_hidden_dim": 256,
        "max_sweeps": 12,
        "cache_dir": None,
        "max_samples": None,
        "preload_workers": 8,
        "fields": ["velocity", "reflectivity", "spectrum_width"],
        "resume": None,
        "signal_weight": 0.95,
    }
    with open(config_path) as f:
        user_cfg = json.load(f)
    defaults.update(user_cfg)
    return argparse.Namespace(**defaults)


def main():
    parser = argparse.ArgumentParser(description='Train Spatio-Temporal Autoencoder')
    parser.add_argument('config', nargs='?', default='configs/train_poc.json',
                        help='Path to JSON config file (default: configs/train_poc.json)')
    cli_args = parser.parse_args()
    args = load_config(cli_args.config)

    # Create checkpoint directory
    checkpoint_dir = Path(args.checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Create visualization directory
    vis_dir = checkpoint_dir / 'visualizations'
    vis_dir.mkdir(exist_ok=True)

    # Save hyperparameters
    with open(checkpoint_dir / 'config.json', 'w') as f:
        json.dump(vars(args), f, indent=2)

    print(f"Training Spatio-Temporal Autoencoder")
    print(f"Device: {args.device}")
    print(f"Mixed precision: {args.mixed_precision}")
    print(f"Data directory: {args.data_dir}")
    print(f"Checkpoint directory: {checkpoint_dir}")
    print()

    # Load dataset
    print("Loading dataset...")
    image_size = (args.image_size, args.image_size)
    fields = args.fields
    full_dataset = RadarSweepDataset(
        data_dir=args.data_dir,
        fields=fields,
        image_size=image_size,
        max_sweeps=args.max_sweeps,
        cache_dir=args.cache_dir,
        max_samples=args.max_samples,
        preload_workers=args.preload_workers,
    )

    # Split into train/val
    val_size = int(len(full_dataset) * args.val_split)
    train_size = len(full_dataset) - val_size
    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])

    print(f"Train size: {train_size}")
    print(f"Val size: {val_size}")
    print()

    # Create dataloaders (num_workers=0 since data is preloaded in memory)
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=collate_radar_batch,
        num_workers=0,
        pin_memory=True if args.device == 'cuda' else False
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=collate_radar_batch,
        num_workers=0,
        pin_memory=True if args.device == 'cuda' else False
    )

    # Create model
    print("Creating model...")
    model = SpatioTemporalAutoencoder(
        num_fields=len(fields),
        image_size=image_size,
        spatial_latent_dim=args.spatial_latent_dim,
        temporal_hidden_dim=args.temporal_hidden_dim,
        max_sweeps=args.max_sweeps
    )

    model = model.to(args.device)
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    print()

    # Create optimizer
    optimizer = optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-5)

    # Learning rate scheduler
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5, verbose=True)

    # Mixed precision scaler
    scaler = GradScaler() if args.mixed_precision and args.device == 'cuda' else None
    if scaler:
        print("Using mixed precision training (fp16)")

    # Resume from checkpoint if specified
    start_epoch = 1
    train_losses = []
    val_losses = []
    best_val_loss = float('inf')

    resume_path = args.resume
    if resume_path == "latest":
        latest = checkpoint_dir / "latest_checkpoint.pt"
        resume_path = str(latest) if latest.exists() else None

    if resume_path and Path(resume_path).exists():
        print(f"Resuming from {resume_path}")
        ckpt = torch.load(resume_path, map_location=args.device, weights_only=False)
        model.load_state_dict(ckpt['model_state_dict'])
        optimizer.load_state_dict(ckpt['optimizer_state_dict'])
        if ckpt.get('scheduler_state_dict') and scheduler is not None:
            scheduler.load_state_dict(ckpt['scheduler_state_dict'])
        if scaler is not None and ckpt.get('scaler_state_dict'):
            scaler.load_state_dict(ckpt['scaler_state_dict'])
        start_epoch = ckpt['epoch'] + 1
        train_losses = ckpt.get('train_losses', [])
        val_losses = ckpt.get('val_losses', [])
        best_val_loss = ckpt.get('best_val_loss', float('inf'))
        print(f"Resumed at epoch {start_epoch}, best val loss: {best_val_loss:.6f}")

    # Training loop
    print("Starting training...")
    fixed_batch = None  # Will be set on first visualization for consistency

    for epoch in range(start_epoch, args.num_epochs + 1):
        print(f"\nEpoch {epoch}/{args.num_epochs}")
        print("-" * 50)

        # Train
        train_loss = train_epoch(model, train_loader, optimizer, args.device, scaler, args.signal_weight)
        train_losses.append(train_loss)

        # Validate
        val_loss, val_anomaly_scores = validate_epoch(model, val_loader, args.device, use_amp=scaler is not None, signal_weight=args.signal_weight)
        val_losses.append(val_loss)

        print(f"Train Loss: {train_loss:.6f}")
        print(f"Val Loss: {val_loss:.6f}")
        print(f"Val Anomaly Score: {val_anomaly_scores.mean():.6f} ± {val_anomaly_scores.std():.6f}")

        # Update learning rate
        scheduler.step(val_loss)

        # Always save latest (for resuming)
        save_checkpoint(model, optimizer, epoch, train_loss, val_loss, checkpoint_dir,
                        scaler=scaler, scheduler=scheduler,
                        train_losses=train_losses, val_losses=val_losses, best_val_loss=best_val_loss)

        # Save reconstruction frames every epoch (for timelapse) and update training curve
        fixed_batch = visualize_reconstructions(
            model, val_loader, args.device, vis_dir,
            field_names=fields, epoch=epoch, fixed_batch=fixed_batch
        )
        plot_training_curves(train_losses, val_losses, vis_dir)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), checkpoint_dir / 'best_model.pt')
            print(f"New best model saved! (val_loss={val_loss:.6f})")

    # Build timelapse GIFs from saved frames
    print("\nTraining complete!")
    build_timelapse_gif(vis_dir)

    # Save final model
    torch.save(model.state_dict(), checkpoint_dir / 'final_model.pt')
    print(f"\nFinal model saved to {checkpoint_dir / 'final_model.pt'}")


if __name__ == "__main__":
    main()
