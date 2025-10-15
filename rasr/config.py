"""
Simple configuration loader for RASR
Loads from config.yaml and provides easy access to settings
"""

import yaml
from pathlib import Path
from typing import Any, Dict
from multiprocessing import cpu_count


class Config:
    """Simple configuration class."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config = self._load_config()
        self._ensure_directories()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def _ensure_directories(self):
        """Create required directories if they don't exist."""
        dirs = [
            self.data_dir,
            self.falls_dir,
            self.vis_dir,
            self.links_dir,
            self.archive_dir,
        ]
        for d in dirs:
            Path(d).mkdir(parents=True, exist_ok=True)

    def get(self, key: str, default=None):
        """Get configuration value with optional default."""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value

    # Directory properties
    @property
    def data_dir(self) -> str:
        return self.get('data_dir', 'data')

    @property
    def falls_dir(self) -> str:
        return self.get('falls_dir', 'falls')

    @property
    def vis_dir(self) -> str:
        return self.get('vis_dir', 'vis')

    @property
    def links_dir(self) -> str:
        return self.get('links_dir', 'links')

    @property
    def archive_dir(self) -> str:
        return self.get('archive_dir', 'archive')

    # Processing properties
    @property
    def max_workers(self) -> int:
        workers = self.get('max_workers')
        return workers if workers is not None else cpu_count()

    @property
    def batch_size(self) -> int:
        return self.get('batch_size', 160)

    @property
    def confidence_threshold(self) -> float:
        return self.get('confidence_threshold', 0.75)

    @property
    def visualization(self) -> bool:
        return self.get('visualization', True)

    # Data collection properties
    @property
    def time_range(self) -> list:
        tr = self.get('time_range', {})
        return [tr.get('start', 0), tr.get('end', 235959)]

    @property
    def download_retries(self) -> int:
        return self.get('download_retries', 5)

    @property
    def concurrent_downloads(self) -> int:
        return self.get('concurrent_downloads', 20)

    # Model properties
    @property
    def model_path(self) -> str:
        return self.get('model_path', 'RASRmodl.pth')

    @property
    def model_classes(self) -> list:
        return self.get('model_classes', ['fall'])

    # NOAA properties
    @property
    def noaa_base_url(self) -> str:
        return self.get('noaa_base_url', 'https://www.ncdc.noaa.gov/nexradinv/bdp-download.jsp')

    @property
    def radar_product(self) -> str:
        return self.get('radar_product', 'AAL2')

    # Database
    @property
    def database_path(self) -> str:
        return self.get('database_path', 'rasr.db')


# Singleton instance
_config = None


def get_config() -> Config:
    """Get or create config singleton."""
    global _config
    if _config is None:
        _config = Config()
    return _config
