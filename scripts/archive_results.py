"""
RASR Pipeline v2.0
as of 2025

Script for porting all detections and processed radar data into separate archives

@authors: Carson Lansdowne
"""

import os
import shutil
from datetime import datetime, timedelta
from rasr.config import get_config
from rasr.util.fileio import clear_files, get_list_of_files, make_dir

if __name__ == "__main__":
    # Load configuration
    config = get_config()

    # Date parameters
    now = datetime.now()
    today = datetime.today()
    yesterday = today - timedelta(1)
    date_str = today.strftime("%m:%d:%Y")
    yesterday_str = yesterday.strftime("%m:%d:%Y")

    # Create archive directories
    base_archive_dir = config.archive_dir
    daily_archive_dir = os.path.join(base_archive_dir, date_str)
    daily_work_dir = date_str

    folders = [base_archive_dir, daily_archive_dir, daily_work_dir]
    for folder in folders:
        make_dir(folder)

    # Get current files
    fall_files = get_list_of_files(config.falls_dir)
    vis_files = get_list_of_files(config.vis_dir)

    # Process visualization files
    for file in vis_files:
        daily_vis_dir = os.path.join(daily_work_dir, "vis")
        archive_vis_dir = os.path.join(daily_archive_dir, "vis")

        make_dir(daily_vis_dir)
        make_dir(archive_vis_dir)

        shutil.copy(file, daily_vis_dir)
        shutil.copy(file, archive_vis_dir)

    clear_files(config.vis_dir)

    # Process detection files
    for file in fall_files:
        daily_falls_dir = os.path.join(daily_work_dir, "falls")
        archive_falls_dir = os.path.join(daily_archive_dir, "falls")

        make_dir(daily_falls_dir)
        make_dir(archive_falls_dir)

        shutil.copy(file, daily_falls_dir)
        shutil.copy(file, archive_falls_dir)

    clear_files(config.falls_dir)

    # Clean up yesterday's working directory
    if os.path.isdir(yesterday_str):
        shutil.rmtree(yesterday_str)
        print(f"{yesterday_str} removed")

    # Check for detections
    detections = get_list_of_files(config.falls_dir)
    print(f"Found {len(detections)} detections to process")
