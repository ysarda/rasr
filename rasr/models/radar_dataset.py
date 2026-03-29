"""
PyTorch Dataset for NEXRAD Level II Radar Data
Loads multi-sweep, multi-field sequences for anomaly detection
"""

import os
import numpy as np
import pyart
import torch
from torch.utils.data import Dataset
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from typing import List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.append(str(Path(__file__).parent.parent))
from rasr.util.fileio import is_valid_nexrad_file


class RadarSweepDataset(Dataset):
    """
    PyTorch Dataset for NEXRAD radar sequences.

    Loads multi-sweep, multi-field radar data and converts to normalized tensors.

    Args:
        data_dir: Directory containing NEXRAD files (e.g., data/positive/ or data/null/)
        fields: List of radar fields to extract (default: ['velocity', 'reflectivity', 'spectrum_width'])
        image_size: Target image size (H, W) after downsampling (default: 512x512)
        max_sweeps: Maximum number of sweeps to include (default: 12)
        station_filter: Optional list of stations to include (default: all)
        transform: Optional transform to apply to tensors
    """

    def __init__(
        self,
        data_dir: str,
        fields: List[str] = None,
        image_size: Tuple[int, int] = (128, 128),
        max_sweeps: int = 12,
        station_filter: Optional[List[str]] = None,
        transform=None,
        cache_dir: Optional[str] = None,
        max_samples: Optional[int] = None,
        preload_workers: int = 8,
    ):
        self.data_dir = Path(data_dir)
        self.fields = fields or ['velocity', 'reflectivity', 'spectrum_width']
        self.image_size = image_size
        self.max_sweeps = max_sweeps
        self.transform = transform
        self.cache_dir = (Path(cache_dir) / Path(data_dir).name) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Field normalization parameters (from domain knowledge)
        self.field_norms = {
            'velocity': 70.0,  # m/s (max radial velocity)
            'reflectivity': 80.0,  # dBZ (max reflectivity)
            'spectrum_width': 20.0,  # m/s (max spectrum width)
            'cross_correlation_ratio': 1.0,  # Correlation coefficient [0, 1]
            'differential_reflectivity': 8.0,  # dB
            'differential_phase': 180.0,  # degrees
        }

        # Collect all radar files
        self.radar_files = self._collect_files(station_filter)
        if max_samples and max_samples < len(self.radar_files):
            self.radar_files = self.radar_files[:max_samples]
        print(f"Found {len(self.radar_files)} radar files from {data_dir}")

        # Preload everything into memory so training isn't I/O-bound
        self._preloaded = self._parallel_preload(num_workers=preload_workers)

    def _collect_files(self, station_filter):
        """Collect all radar files from data directory."""
        files = []

        # Iterate through station directories
        for station_dir in sorted(self.data_dir.iterdir()):
            if not station_dir.is_dir():
                continue

            station_id = station_dir.name
            if station_filter and station_id not in station_filter:
                continue

            # Collect all radar files in this station
            for radar_file in sorted(station_dir.iterdir()):
                # Filter for valid NEXRAD Level II files
                if radar_file.suffix in ['.gz', ''] and is_valid_nexrad_file(radar_file.name):
                    files.append(radar_file)

        return files

    def _parallel_preload(self, num_workers=8):
        """Preload all samples into memory using parallel workers."""
        n = len(self.radar_files)
        print(f"Preloading {n} files with {num_workers} workers...")
        results = [None] * n

        def _load_with_idx(i):
            return i, self._load_item(i)

        loaded = 0
        failed = 0
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(_load_with_idx, i) for i in range(n)]
            for future in as_completed(futures):
                i, item = future.result()
                results[i] = item
                if item is None:
                    failed += 1
                loaded += 1
                if loaded % 50 == 0 or loaded == n:
                    print(f"  {loaded}/{n} loaded ({failed} failed)")

        preloaded = [r for r in results if r is not None]
        print(f"Preloaded {len(preloaded)} valid samples")
        return preloaded

    def __len__(self):
        return len(self._preloaded)

    def __getitem__(self, idx):
        return self._preloaded[idx]

    def _load_item(self, idx):
        """Load and process a single radar file from disk."""
        radar_file = self.radar_files[idx]

        # Return cached tensor if available
        if self.cache_dir is not None:
            fields_tag = '-'.join(f[:3] for f in self.fields)
            cache_key = f"{radar_file.parent.name}_{radar_file.name}_s{self.max_sweeps}_{fields_tag}_{'x'.join(map(str,self.image_size))}.pt"
            cache_path = self.cache_dir / cache_key
            if cache_path.exists():
                try:
                    return torch.load(cache_path, weights_only=False)
                except Exception:
                    pass

        try:
            radar = pyart.io.read(str(radar_file))
            num_sweeps = min(radar.nsweeps, self.max_sweeps)

            data = np.zeros((self.max_sweeps, len(self.fields), *self.image_size), dtype=np.float32)
            mask = np.zeros(self.max_sweeps, dtype=bool)

            for sweep_idx in range(num_sweeps):
                sweep_data = self._extract_sweep(radar, sweep_idx)
                if sweep_data is not None:
                    data[sweep_idx] = sweep_data
                    mask[sweep_idx] = True

            if not mask.any():
                return None

            data_tensor = torch.from_numpy(data)
            mask_tensor = torch.from_numpy(mask)
            metadata = {
                'file_path': str(radar_file),
                'station': radar_file.parent.name,
                'filename': radar_file.name,
                'num_sweeps': int(mask.sum()),
            }

            if self.transform:
                data_tensor = self.transform(data_tensor)

            result = data_tensor, mask_tensor, metadata
            if self.cache_dir is not None:
                torch.save(result, cache_path)

            return result

        except Exception as e:
            print(f"Error loading {radar_file.name}: {e}")
            return None

    def _extract_sweep(self, radar, sweep_idx):
        """
        Extract multi-field data for a single sweep and convert to image.

        Args:
            radar: PyART radar object
            sweep_idx: Sweep index (elevation angle)

        Returns:
            sweep_data: Array of shape (num_fields, H, W) or None on error
        """
        try:
            # Initialize array for this sweep
            sweep_data = np.zeros((len(self.fields), *self.image_size), dtype=np.float32)

            # Process each field
            for field_idx, field_name in enumerate(self.fields):
                # Extract field data for this sweep
                field_data = self._field_to_image(radar, field_name, sweep_idx)

                if field_data is not None:
                    sweep_data[field_idx] = field_data

            return sweep_data

        except Exception as e:
            return None

    def _field_to_image(self, radar, field_name, sweep_idx):
        """
        Convert a radar field to normalized image array using direct gridding.

        Args:
            radar: PyART radar object
            field_name: Name of field ('velocity', 'reflectivity', etc.)
            sweep_idx: Sweep index

        Returns:
            Normalized array of shape (H, W) or None if field unavailable
        """
        try:
            # Check if field exists in radar data
            radar_field_name = self._get_radar_field_name(field_name, radar)
            if radar_field_name is None:
                return np.zeros(self.image_size, dtype=np.float32)

            sweep_slice = radar.get_slice(sweep_idx)
            field_data = radar.fields[radar_field_name]['data'][sweep_slice]  # (rays, gates)
            azimuth = radar.azimuth['data'][sweep_slice]  # (rays,)
            ranges = radar.range['data']                   # (gates,)

            # Handle masked array for entire sweep at once
            if hasattr(field_data, 'mask'):
                field_data = np.ma.filled(field_data, 0).astype(np.float32)
            else:
                field_data = np.asarray(field_data, dtype=np.float32)

            grid_size = self.image_size[0]
            max_range = 250000  # 250 km in meters

            # Vectorized polar → Cartesian: broadcast over (rays, gates)
            az_rad = np.deg2rad(azimuth)                                           # (rays,)
            x = ranges[np.newaxis, :] * np.sin(az_rad[:, np.newaxis])             # (rays, gates)
            y = ranges[np.newaxis, :] * np.cos(az_rad[:, np.newaxis])             # (rays, gates)

            xi = ((x + max_range) / (2 * max_range) * (grid_size - 1)).astype(np.int32)
            yi = ((y + max_range) / (2 * max_range) * (grid_size - 1)).astype(np.int32)

            valid = (xi >= 0) & (xi < grid_size) & (yi >= 0) & (yi < grid_size)

            image = np.zeros(self.image_size, dtype=np.float32)
            image[grid_size - 1 - yi[valid], xi[valid]] = field_data[valid]

            norm_factor = self.field_norms.get(field_name, 1.0)
            return np.clip(image / norm_factor, -1.0, 1.0)

        except Exception:
            return np.zeros(self.image_size, dtype=np.float32)

    def _get_radar_field_name(self, field_name, radar):
        """
        Map common field names to actual radar field names.

        Different radars may use different naming conventions.
        """
        field_mapping = {
            'velocity': ['velocity', 'VEL', 'radial_velocity'],
            'reflectivity': ['reflectivity', 'REF', 'DBZ', 'reflectivity_horizontal'],
            'spectrum_width': ['spectrum_width', 'SW', 'WIDTH'],
            'cross_correlation_ratio': ['cross_correlation_ratio', 'RHOHV', 'RHO', 'correlation_coefficient'],
            'differential_reflectivity': ['differential_reflectivity', 'ZDR', 'diff_reflectivity'],
            'differential_phase': ['differential_phase', 'PHIDP', 'diff_phase'],
        }

        if field_name not in field_mapping:
            return None

        # Check which variant exists in this radar file
        for variant in field_mapping[field_name]:
            if variant in radar.fields:
                return variant

        return None


def collate_radar_batch(batch):
    """
    Custom collate function for DataLoader to handle variable-length sequences.
    Filters out None values (failed loads).

    Args:
        batch: List of (data, mask, metadata) tuples or None values

    Returns:
        Batched tensors with proper padding, or None if entire batch is invalid
    """
    # Filter out None values (failed loads)
    batch = [item for item in batch if item is not None]

    # If entire batch failed, return None (will be handled by training loop)
    if len(batch) == 0:
        return None, None, None

    data_list, mask_list, metadata_list = zip(*batch)

    # Stack into batches
    data_batch = torch.stack(data_list, dim=0)  # (B, max_sweeps, num_fields, H, W)
    mask_batch = torch.stack(mask_list, dim=0)  # (B, max_sweeps)

    return data_batch, mask_batch, list(metadata_list)


# Example usage and testing
if __name__ == "__main__":
    # Test dataset loading
    dataset = RadarSweepDataset(
        data_dir='data/null',
        fields=['velocity', 'reflectivity', 'spectrum_width'],
        image_size=(128, 128),
        max_sweeps=12
    )

    print(f"Dataset size: {len(dataset)}")

    if len(dataset) > 0:
        # Load first sample
        data, mask, metadata = dataset[0]
        print(f"\nFirst sample:")
        print(f"  Data shape: {data.shape}")  # (max_sweeps, num_fields, H, W)
        print(f"  Mask shape: {mask.shape}")  # (max_sweeps,)
        print(f"  Valid sweeps: {mask.sum().item()}")
        print(f"  Metadata: {metadata}")

        # Test DataLoader
        from torch.utils.data import DataLoader
        loader = DataLoader(
            dataset,
            batch_size=2,
            shuffle=True,
            collate_fn=collate_radar_batch,
            num_workers=0
        )

        data_batch, mask_batch, metadata_batch = next(iter(loader))
        print(f"\nBatched data shape: {data_batch.shape}")  # (B, max_sweeps, num_fields, H, W)
        print(f"Batched mask shape: {mask_batch.shape}")  # (B, max_sweeps)
