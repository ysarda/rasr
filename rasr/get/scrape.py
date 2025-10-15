"""
RASR Scrape v3
Legacy web scraping functions - kept for backward compatibility
Note: Primary download method now uses nexradaws (see get.py)

@authors: Benjamin Miller, Robby Keh, Yash Sarda, Carson Lansdowne
"""

import requests
import time
from bs4 import BeautifulSoup, SoupStrainer

# NOTE: These functions are deprecated in favor of nexradaws
# They are kept for backward compatibility or fallback scenarios


def save_links(page_url, link_file="links/data_links.txt"):
    """
    Fetch and save links from NOAA page.

    Args:
        page_url: URL to scrape
        link_file: File to save links to

    Returns:
        List of links found
    """
    link_time_num = [str(i).zfill(6) for i in range(0, 235960)]
    links = []

    response = requests.get(page_url)

    try:
        with open(link_file, "w") as f:
            for link in BeautifulSoup(
                response.text, "html.parser", parse_only=SoupStrainer("a")
            ):
                if (
                    link.has_attr("href")
                    and ("amazonaws" in link["href"])
                    or any(s in link for s in link_time_num)
                ):
                    f.write("{}\n".format(link["href"]))
                    links.append(link["href"])
    except OSError as e:
        print(f"Error saving links: {e}")

    return links


def download_content(link, max_retries=5, retry_delay=2, timeout=300):
    """
    Download content with retry logic.

    Args:
        link: URL to download
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds
        timeout: Request timeout in seconds

    Returns:
        Response object or None if failed
    """
    num_retries = 0
    response = None

    while num_retries < max_retries:
        try:
            response = requests.get(link, timeout=timeout)
            response.raise_for_status()
            break
        except Exception as e:
            print(f"{link} errored {num_retries}: {e}, retrying...")
            num_retries += 1
            time.sleep(retry_delay)

    return response


def write_to_file(filename, dirname, response):
    """Write response content to file."""
    filepath = f"{dirname}/{filename}"
    with open(filepath, "wb") as f:
        f.write(response.content)
    return filepath


def download_link(link, dirname, timerange, tracker=None, max_retries=5):
    """
    Download a radar file if it's in the time range and hasn't been downloaded.

    Args:
        link: URL to download
        dirname: Directory to save file
        timerange: [start, end] time range in HHMMSS format
        tracker: DownloadTracker instance (optional)
        max_retries: Maximum retry attempts

    Returns:
        Downloaded file path or None
    """
    try:
        # Extract filename and metadata
        filename = link.split("/")[-1]

        # Check if already downloaded
        if tracker and tracker.is_downloaded(filename):
            print(f"Skipping {filename} - already downloaded")
            return None

        # Parse filename to check time range
        namer = link.split("links")[-1]

        # Skip MDM summary files
        if namer.split("_")[-1] == "MDM":
            return None

        namer_tmp = namer.split("_")[1] if len(namer.split("_")) > 1 else ""

        # Check if file is in time range
        in_time_range = False

        if namer.split("_")[1] == "gz" if len(namer.split("_")) > 1 else False:
            # .gz files
            time_str = namer_tmp.split(".")[0]
            if time_str.isdigit() and int(time_str) in range(timerange[0], timerange[1]):
                in_time_range = True
                filename = f"{link.split('/')[-1]}.gz"

        elif namer.split(".")[0] != "":
            # Regular files
            time_str = namer_tmp.split(".")[0] if "." in namer_tmp else namer_tmp
            if time_str.isdigit() and int(time_str) in range(timerange[0], timerange[1]):
                in_time_range = True
                filename = link.split("/")[-1]

        if not in_time_range:
            return None

        # Download the file
        response = download_content(link, max_retries=max_retries)
        if not response:
            print(f"No response from {link}")
            return None

        # Write to file
        filepath = write_to_file(filename, dirname, response)

        # Mark as downloaded
        if tracker:
            tracker.mark_downloaded(filename, file_path=filepath)

        print(f"Downloaded: {filename}")
        return filepath

    except Exception as e:
        print(f"Error downloading {link}: {e}")
        return None
