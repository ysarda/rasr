"""Debug script to check what the data loader is producing."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import numpy as np
import matplotlib.pyplot as plt

from rasr.models.radar_dataset import RadarSweepDataset

# Load dataset
print("Loading dataset...")
dataset = RadarSweepDataset(
    data_dir='data/null',
    fields=['velocity', 'reflectivity', 'spectrum_width'],
    image_size=(512, 512),
    max_sweeps=12
)

print(f"Dataset size: {len(dataset)}")

# Load first sample
print("\nLoading first sample...")
result = dataset[0]

if result is None:
    print("ERROR: First sample returned None!")
else:
    data, mask, metadata = result
    print(f"Data shape: {data.shape}")
    print(f"Mask shape: {mask.shape}")
    print(f"Valid sweeps: {mask.sum().item()}")
    print(f"Metadata: {metadata}")

    # Check data statistics
    print(f"\nData statistics:")
    print(f"  Min: {data.min():.4f}")
    print(f"  Max: {data.max():.4f}")
    print(f"  Mean: {data.mean():.4f}")
    print(f"  Std: {data.std():.4f}")
    print(f"  Non-zero count: {(data != 0).sum().item()}")
    print(f"  Total elements: {data.numel()}")

    # Check per-field statistics for ALL valid sweeps
    valid_idx = mask.nonzero(as_tuple=True)[0]
    field_names = ['velocity', 'reflectivity', 'spectrum_width']

    print(f"\nPer-sweep statistics:")
    for sweep_idx in valid_idx:
        sweep_idx = sweep_idx.item()
        non_zero_fields = []
        for i, name in enumerate(field_names):
            field_data = data[sweep_idx, i]
            nz = (field_data != 0).sum().item()
            if nz > 0:
                non_zero_fields.append(f"{name}:{nz}")
        print(f"  Sweep {sweep_idx}: {', '.join(non_zero_fields) if non_zero_fields else 'empty'}")

    # Save a debug visualization - find a sweep with the most data
    print("\nSaving debug visualization...")

    # Find sweep with most non-zero values
    best_sweep = 0
    best_count = 0
    for sweep_idx in valid_idx:
        sweep_idx = sweep_idx.item()
        count = (data[sweep_idx] != 0).sum().item()
        if count > best_count:
            best_count = count
            best_sweep = sweep_idx

    print(f"Using sweep {best_sweep} with {best_count} non-zero values")

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    field_names = ['Velocity', 'Reflectivity', 'Spectrum Width']

    for i, name in enumerate(field_names):
        field_data = data[best_sweep, i].numpy()

        # Raw data
        im = axes[0, i].imshow(field_data, cmap='RdBu_r', vmin=-1, vmax=1)
        axes[0, i].set_title(f'{name} (sweep {best_sweep})')
        plt.colorbar(im, ax=axes[0, i])

        # Histogram (exclude zeros for better visualization)
        non_zero = field_data[field_data != 0]
        if len(non_zero) > 0:
            axes[1, i].hist(non_zero.flatten(), bins=50)
            axes[1, i].set_title(f'{name} histogram (non-zero only, n={len(non_zero)})')
        else:
            axes[1, i].set_title(f'{name} histogram (all zeros)')
        axes[1, i].set_xlabel('Value')
        axes[1, i].set_ylabel('Count')

    plt.tight_layout()
    plt.savefig('checkpoints/visualizations/debug_dataloader.png', dpi=150)
    plt.close()
    print("Saved to checkpoints/visualizations/debug_dataloader.png")
