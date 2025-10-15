"""
RASR Get v2.0
Main script for data collection
as of 2025

See README for details

@authors: Benjamin Miller, Robby Keh, Yash Sarda
"""

import sys
from datetime import datetime, timedelta
from functools import partial
from multiprocessing import Pool

from rasr.config import get_config
from rasr.get.get import run_get
from rasr.util.fileio import make_dir
from rasr.util.sites import load_radar_sites
from rasr.util.tracker import get_tracker


if __name__ == "__main__":
    # Load configuration
    config = get_config()
    tracker = get_tracker()

    # Ensure directories exist
    folders = [config.links_dir, config.data_dir, config.vis_dir, config.falls_dir]
    for folder in folders:
        make_dir(folder)

    # Get date range (default: yesterday to today)
    now = datetime.now()
    today = datetime.today()
    yesterday = today - timedelta(1)

    date_list = [
        yesterday.year,
        yesterday.month,
        yesterday.day,
        now.year,
        now.month,
        now.day,
    ]

    # Get time range from config
    timerange = config.time_range

    # Get number of workers
    if len(sys.argv) > 1:
        run_num = int(sys.argv[1])
    else:
        run_num = config.max_workers

    # Load radar sites
    radar_sites = load_radar_sites()

    print(f"Starting RASR data collection")
    print(f"Date range: {yesterday.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}")
    print(f"Time range: {timerange[0]:06d} to {timerange[1]:06d}")
    print(f"Sites to process: {len(radar_sites)}")
    print(f"Parallel workers: {run_num}")
    print(f"Data directory: {config.data_dir}")

    # Setup partial function with config
    run_function_partial = partial(
        run_get,
        date_list=date_list,
        time_range=timerange,
        data_dir=config.data_dir,
        link_dir=config.links_dir,
        tracker=tracker,
        config=config,
    )

    # Run parallel downloads
    pool = Pool(processes=run_num)
    pool.map(run_function_partial, [[site] for site in radar_sites])
    pool.close()
    pool.join()

    # Print statistics
    stats = tracker.get_stats()
    print(f"\nCollection complete!")
    print(f"Total files tracked: {stats['total_files']}")
