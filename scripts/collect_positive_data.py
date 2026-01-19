"""
RASR Confirmed Falls Data Collection
Collects radar data for confirmed meteorite fall events

This script reads falls_events.yaml and downloads NEXRAD radar data
for each confirmed event, saving to data/positive/ for ML training.

@authors: Yash Sarda, Benjamin Miller
"""

import sys
import yaml
from datetime import datetime
from functools import partial
from multiprocessing import Pool
from pathlib import Path

from rasr.config import get_config
from rasr.get.get import run_get
from rasr.util.fileio import make_dir


def load_fall_events(yaml_path="falls_events.yaml"):
    """Load confirmed fall events from YAML file."""
    if not Path(yaml_path).exists():
        raise FileNotFoundError(f"Falls events file not found: {yaml_path}")

    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    return data.get('events', [])


def parse_time_to_hhmmss(time_str):
    """Convert HH:MM:SS string to HHMMSS integer."""
    # Remove colons and convert to int
    return int(time_str.replace(':', ''))


def parse_event_time_range(event):
    """Extract date range and time range from event."""
    # Parse date (YYYY-MM-DD)
    date_obj = datetime.strptime(event['date'], '%Y-%m-%d')

    # Parse time range (HH:MM:SS)
    time_start = parse_time_to_hhmmss(event['time_start_utc'])
    time_end = parse_time_to_hhmmss(event['time_end_utc'])

    # date_range() in get.py doesn't include the end date
    # So we need to add 1 day to ensure the event date is included
    from datetime import timedelta
    next_day = date_obj + timedelta(days=1)

    date_list = [
        date_obj.year,
        date_obj.month,
        date_obj.day,
        next_day.year,
        next_day.month,
        next_day.day,
    ]

    time_range = [time_start, time_end]

    return date_list, time_range


def download_event(event, config, verbose=True):
    """Download radar data for a single event."""
    event_name = event['name']
    radar_stations = event.get('radar_stations', [])

    if not radar_stations:
        if verbose:
            print(f"  ⚠ No radar stations specified for '{event_name}', skipping")
        return 0

    if verbose:
        print(f"\n{'='*70}")
        print(f"Event: {event_name}")
        print(f"Date: {event['date']}")
        print(f"Time: {event['time_start_utc']} to {event['time_end_utc']}")
        print(f"Location: {event['location']['latitude']}, {event['location']['longitude']}")
        print(f"Radar stations: {', '.join(radar_stations)}")
        print(f"{'='*70}")

    # Parse event time range
    date_list, time_range = parse_event_time_range(event)

    # Setup partial function with config
    run_function_partial = partial(
        run_get,
        date_list=date_list,
        time_range=time_range,
        data_dir=config.positive_data_dir,
        link_dir=None,
        tracker=None,
        config=config,
    )

    # Download from each radar station
    if verbose:
        print(f"Downloading from {len(radar_stations)} radar station(s)...")

    # Run downloads sequentially for each event (can parallelize stations)
    for station in radar_stations:
        run_function_partial([station])

    return len(radar_stations)


def main():
    # Load configuration
    config = get_config()

    # Ensure data directory exists
    make_dir(config.positive_data_dir)

    # Load fall events
    print("Loading confirmed fall events from falls_events.yaml...")
    try:
        events = load_fall_events()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure falls_events.yaml exists in the project root.")
        sys.exit(1)

    print(f"Found {len(events)} confirmed fall events\n")

    # Check for specific event argument
    if len(sys.argv) > 1:
        event_name = sys.argv[1]
        # Filter to specific event
        events = [e for e in events if e['name'].lower() == event_name.lower()]
        if not events:
            print(f"Error: Event '{event_name}' not found in falls_events.yaml")
            sys.exit(1)
        print(f"Processing single event: {events[0]['name']}\n")

    # Print summary
    print("RASR Confirmed Falls Data Collection")
    print(f"Total events to process: {len(events)}")
    print(f"Data directory: {config.positive_data_dir}")
    print()

    # Track statistics
    total_stations = 0
    processed_events = 0
    skipped_events = 0

    # Process each event
    for i, event in enumerate(events, 1):
        try:
            stations_count = download_event(event, config, verbose=True)
            if stations_count > 0:
                total_stations += stations_count
                processed_events += 1
            else:
                skipped_events += 1
        except Exception as e:
            print(f"  ✗ Error processing event '{event['name']}': {e}")
            skipped_events += 1
            continue

    # Print final statistics
    print(f"\n{'='*70}")
    print("Collection Complete!")
    print(f"{'='*70}")
    print(f"Events processed: {processed_events}/{len(events)}")
    print(f"Events skipped: {skipped_events}")
    print(f"Total radar stations queried: {total_stations}")
    print(f"\nPositive training data saved to: {config.positive_data_dir}")
    print()


if __name__ == "__main__":
    main()
