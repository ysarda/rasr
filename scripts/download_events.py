"""
Download NEXRAD Level II files for specific re-entry events into data/positive.

Pulls a tight time window around each event so the positive set contains the
scans that actually saw the object. Files land in data/positive/<STATION>/ and
coexist with any other event already in that station folder (the evaluator keys
events by (station, date), so dates disambiguate).
"""

import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from rasr.get.get import get_s3_client, get_station_files, download_s3_file
from rasr.util.fileio import is_valid_nexrad_file

# (station, YYYY, MM, DD, start_hhmmss, end_hhmmss)  -- UTC
EVENTS = [
    # Starship F5 booster catch at Starbase (~12:32 UTC)
    ("KBRO", "2024", "10", "13", "121000", "124000"),
    # Crew-7 trunk re-entry over Canton NC (~00:00-00:15 UTC), two stations
    ("KGSP", "2024", "05", "22", "234500", "002000"),
    ("KMRX", "2024", "05", "22", "234500", "002000"),
    # ISS EP9 battery pallet over Naples FL (documented null/sub-threshold case)
    ("KAMX", "2024", "03", "08", "100000", "120000"),
]

OUT_DIR = Path("data/positive")
TS_RE = re.compile(r"(\w{4})(\d{8})_(\d{6})")


def in_window(fn, start, end):
    m = TS_RE.search(fn)
    if not m:
        return False
    hhmmss = m.group(3)
    if start <= end:
        return start <= hhmmss <= end
    # wrap past midnight (start > end): the window also includes the day before's
    # late hours; we list a single day, so accept >=start OR <=end
    return hhmmss >= start or hhmmss <= end


def main():
    s3 = get_s3_client()
    planned = []
    for station, y, mo, d, start, end in EVENTS:
        keys = get_station_files(s3, station, y, mo, d)
        valid = [k for k in keys
                 if is_valid_nexrad_file(k.split("/")[-1]) and in_window(k.split("/")[-1], start, end)]
        print(f"{station} {y}-{mo}-{d} [{start}-{end}]: {len(valid)} files in window "
              f"(of {len(keys)} listed)")
        for k in valid:
            fn = k.split("/")[-1]
            planned.append((k, str(OUT_DIR / station / fn)))

    for _, lp in planned:
        Path(lp).parent.mkdir(parents=True, exist_ok=True)

    def worker(key, lp):
        if Path(lp).exists():
            return True
        client = get_s3_client()
        return download_s3_file(client, key, lp, max_retries=4)

    ok = fail = 0
    print(f"\nDownloading {len(planned)} files...")
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(worker, k, lp): lp for k, lp in planned}
        for fut in as_completed(futs):
            if fut.result():
                ok += 1
            else:
                fail += 1
    print(f"Done. ok={ok} fail={fail}")


if __name__ == "__main__":
    main()
