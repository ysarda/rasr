"""
RASR Get v3
Rewritten to use boto3 for direct AWS S3 downloads

@authors: Yash Sarda, Carson Lansdowne, Benjamin Miller
"""

from datetime import datetime, timedelta, date
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
from botocore import UNSIGNED
from botocore.client import Config

from rasr.util.fileio import is_valid_nexrad_file


# NEXRAD AWS S3 configuration
NEXRAD_BUCKET = 'unidata-nexrad-level2'
NEXRAD_REGION = 'us-east-1'


def get_s3_client():
    """Create and return an S3 client configured for NEXRAD data."""
    return boto3.client(
        's3',
        region_name=NEXRAD_REGION,
        config=Config(signature_version=UNSIGNED, user_agent_extra='Resource')
    )


def date_range(start_date, end_date):
    """Generate date range between two dates."""
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def time_in_range(time_str, time_range):
    """
    Check if a time string is in the given range.

    Args:
        time_str: Time string in HHMMSS format
        time_range: [start, end] time range in HHMMSS format

    Returns:
        True if time is in range, False otherwise
    """
    try:
        time_int = int(time_str)
        return time_range[0] <= time_int <= time_range[1]
    except (ValueError, TypeError):
        return False


def extract_time_from_filename(filename):
    """
    Extract time from NEXRAD filename.

    NEXRAD files follow format: SITEYYYYYMMDD_HHMMSS_V06
    Example: KTLX20240101_000004_V06

    Args:
        filename: NEXRAD filename

    Returns:
        Time string in HHMMSS format or None
    """
    try:
        parts = filename.split('_')
        if len(parts) >= 2:
            time_str = parts[1]  # HHMMSS part (index 1, not 2)
            return time_str
    except Exception:
        pass
    return None


def get_station_files(s3_client, station, year, month, day):
    """
    Get list of files for a specific radar station and date from S3.

    Args:
        s3_client: boto3 S3 client
        station: Radar station ID (e.g., 'KTLX')
        year: Year string (e.g., '2024')
        month: Month string with leading zero (e.g., '01')
        day: Day string with leading zero (e.g., '15')

    Returns:
        List of S3 keys for matching files
    """
    prefix = f"{year}/{month}/{day}/{station}/"

    files = []
    paginator = s3_client.get_paginator('list_objects_v2')

    try:
        for page in paginator.paginate(Bucket=NEXRAD_BUCKET, Prefix=prefix):
            if 'Contents' in page:
                files.extend([obj['Key'] for obj in page['Contents']])
    except Exception as e:
        print(f"Error listing files for {station}: {e}")

    return files


def download_s3_file(s3_client, s3_key, local_path, max_retries=3):
    """
    Download a file from S3 with retry logic.

    Args:
        s3_client: boto3 S3 client
        s3_key: S3 object key
        local_path: Local file path to save to
        max_retries: Maximum number of retry attempts

    Returns:
        True if successful, False otherwise
    """
    for attempt in range(max_retries):
        try:
            s3_client.download_file(NEXRAD_BUCKET, s3_key, local_path)
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Retry {attempt + 1}/{max_retries} for {os.path.basename(local_path)}: {e}")
            else:
                print(f"Failed to download {os.path.basename(local_path)}: {e}")
                return False
    return False


def run_get(sites, date_list, time_range, data_dir, link_dir=None, tracker=None, config=None):
    """
    Download radar data for given sites and date range using boto3.

    Args:
        sites: List of radar site IDs
        date_list: [origin_year, origin_month, origin_day, end_year, end_month, end_day]
        time_range: [start_time, end_time] in HHMMSS format
        data_dir: Directory to save data files
        link_dir: Directory for temporary link files (unused, kept for compatibility)
        tracker: DownloadTracker instance (optional)
        config: Config instance (optional)
    """
    # Parse input
    origin_year, origin_month, origin_day = date_list[0:3]
    end_year, end_month, end_day = date_list[3:6]

    # Get download settings
    if config:
        max_retries = config.download_retries
        concurrent_downloads = config.concurrent_downloads
    else:
        max_retries = 5
        concurrent_downloads = 6

    # Setup date range
    start_date = date(origin_year, origin_month, origin_day)
    end_date = date(end_year, end_month, end_day)

    # Initialize S3 client
    s3_client = get_s3_client()

    try:
        for single_date in date_range(start_date, end_date):
            year = str(single_date.year)
            month = f"{single_date.month:02d}"
            day = f"{single_date.day:02d}"

            print(f"\n----------------------------------------")
            print(f"Downloading data for {month}/{day}/{year}")
            print(f"----------------------------------------")

            # Process each radar site
            for site_id in sites:
                print(f'\nDownloading data from radar: "{site_id}"')

                try:
                    # Get available files for this radar and date
                    s3_files = get_station_files(s3_client, site_id, year, month, day)

                    if not s3_files:
                        print(f"No files found for {site_id} on {month}/{day}/{year}")
                        continue

                    print(f"Found {len(s3_files)} total files for {site_id}")

                    # Filter files by validity, time range, and check if already downloaded
                    files_to_download = []
                    skipped_invalid = 0
                    for s3_key in s3_files:
                        filename = s3_key.split('/')[-1]

                        # Check if valid NEXRAD file (exclude _MDM, _SLC, etc.)
                        if not is_valid_nexrad_file(filename):
                            skipped_invalid += 1
                            continue

                        time_str = extract_time_from_filename(filename)

                        if time_str and time_in_range(time_str, time_range):
                            # Check if already downloaded
                            if tracker and tracker.is_downloaded(filename):
                                print(f"Skipping {filename} - already downloaded")
                                continue
                            files_to_download.append((s3_key, filename))

                    if skipped_invalid > 0:
                        print(f"Filtered out {skipped_invalid} non-standard files (_MDM, _SLC, etc.)")

                    if not files_to_download:
                        print(f"No files in time range {time_range[0]:06d}-{time_range[1]:06d}")
                        continue

                    print(f"Downloading {len(files_to_download)} files in time range")

                    # Create site-specific directory
                    site_data_dir = os.path.join(data_dir, site_id)
                    os.makedirs(site_data_dir, exist_ok=True)

                    # Download files with concurrent threads
                    success_count = 0
                    failed_count = 0

                    def download_worker(s3_key, filename):
                        """Worker function for downloading a single file."""
                        # Create a new S3 client for this thread (boto3 clients are not thread-safe)
                        thread_s3_client = get_s3_client()
                        local_path = os.path.join(site_data_dir, filename)
                        if download_s3_file(thread_s3_client, s3_key, local_path, max_retries):
                            if tracker:
                                tracker.mark_downloaded(filename, file_path=local_path)
                            print(f"Downloaded: {filename}")
                            return True
                        return False

                    # Use ThreadPoolExecutor for concurrent downloads
                    with ThreadPoolExecutor(max_workers=concurrent_downloads) as executor:
                        futures = {
                            executor.submit(download_worker, s3_key, filename): filename
                            for s3_key, filename in files_to_download
                        }

                        for future in as_completed(futures):
                            if future.result():
                                success_count += 1
                            else:
                                failed_count += 1

                    print(f"Download complete: {success_count} succeeded, {failed_count} failed")

                except Exception as e:
                    print(f"Error downloading from {site_id}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

    except KeyboardInterrupt:
        print(f"\n\nDownload interrupted by user")
        print(f"NOTE: Partial downloads may have occurred. Check data directory.")
