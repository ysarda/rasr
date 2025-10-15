"""
Simple file-based tracking for downloads
Tracks what's been downloaded to avoid re-downloading
"""

import os
import json
from datetime import datetime
from pathlib import Path


class DownloadTracker:
    """Track downloaded files using a simple JSON file."""

    def __init__(self, tracker_file="downloads.json"):
        self.tracker_file = tracker_file
        self.downloads = self._load()

    def _load(self):
        """Load tracking data from file."""
        if not os.path.exists(self.tracker_file):
            return {}

        try:
            with open(self.tracker_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save(self):
        """Save tracking data to file."""
        with open(self.tracker_file, 'w') as f:
            json.dump(self.downloads, f, indent=2)

    def is_downloaded(self, filename):
        """Check if a file has already been downloaded."""
        return filename in self.downloads

    def mark_downloaded(self, filename, site_id=None, file_path=None):
        """Mark a file as downloaded."""
        self.downloads[filename] = {
            'download_time': datetime.now().isoformat(),
            'site_id': site_id,
            'file_path': file_path
        }
        self._save()

    def get_stats(self):
        """Get download statistics."""
        return {
            'total_files': len(self.downloads),
            'tracker_file': self.tracker_file
        }


# Singleton instance
_tracker = None


def get_tracker(tracker_file=None):
    """Get or create tracker singleton."""
    global _tracker
    if _tracker is None:
        _tracker = DownloadTracker(tracker_file or "downloads.json")
    return _tracker
