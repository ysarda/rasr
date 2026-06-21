"""
Stratified null-data sampler for RASR.

Builds a varied "normal" training set by sampling NEXRAD scans uniformly across:
  - DATE: stratified by month over a date range (guarantees seasonal coverage)
  - STATION: uniform random over the full active_sites list (covers coastal/
             mountain/inland station types present in that list)
  - TIME OF DAY: a random valid scan within each chosen station-day

This replaces single-day null sets, which make the model flag any unseen
day/scene as anomalous rather than learning a broad notion of "normal".

Usage:
  python scripts/sample_null_data.py --num-samples 20000
  python scripts/sample_null_data.py --num-samples 5000 \
      --start-date 2025-06-01 --end-date 2026-05-31 --workers 12
"""

import argparse
import random
import sys
from calendar import monthrange
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path

import yaml

sys.path.append(str(Path(__file__).parent.parent))
from rasr.get.get import get_s3_client, get_station_files, download_s3_file
from rasr.util.fileio import is_valid_nexrad_file


def load_active_sites(config_path="config.yaml"):
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    sites = cfg.get("active_sites", [])
    if not sites:
        raise ValueError("No active_sites found in config.yaml")
    return sites


def load_excluded_dates(yaml_path="falls_events.yaml"):
    """Dates of known fall events — skip so they don't contaminate the null set."""
    excluded = set()
    p = Path(yaml_path)
    if not p.exists():
        return excluded
    with open(p) as f:
        data = yaml.safe_load(f)
    for ev in data.get("events", []):
        d = ev.get("date")
        if d:
            excluded.add(d)  # 'YYYY-MM-DD'
    return excluded


def month_buckets(start: date, end: date):
    """List of (year, month) tuples spanning [start, end] inclusive."""
    buckets = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        buckets.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return buckets


def random_day_in_month(year, month, start, end, excluded):
    """Pick a random valid day within (year, month), respecting range + exclusions."""
    ndays = monthrange(year, month)[1]
    for _ in range(20):  # retry a few times to dodge excluded/out-of-range days
        day = random.randint(1, ndays)
        d = date(year, month, day)
        if d < start or d > end:
            continue
        if d.isoformat() in excluded:
            continue
        return d
    return None


def already_have(out_dir, station):
    """Set of filenames already downloaded for a station (for dedup)."""
    sdir = out_dir / station
    if not sdir.exists():
        return set()
    return {p.name for p in sdir.iterdir()}


def main():
    ap = argparse.ArgumentParser(description="Stratified NEXRAD null-data sampler")
    ap.add_argument("--num-samples", type=int, default=20000,
                    help="Target number of scans to download (default: 20000)")
    ap.add_argument("--start-date", type=str, default="2025-06-01",
                    help="Start of date range, YYYY-MM-DD (default: 2025-06-01)")
    ap.add_argument("--end-date", type=str, default="2026-05-31",
                    help="End of date range, YYYY-MM-DD (default: 2026-05-31)")
    ap.add_argument("--out-dir", type=str, default="data/null",
                    help="Output directory (default: data/null)")
    ap.add_argument("--workers", type=int, default=12,
                    help="Concurrent download workers (default: 12)")
    ap.add_argument("--per-draw", type=int, default=1,
                    help="Scans to take per (station, day) draw (default: 1)")
    ap.add_argument("--seed", type=int, default=None, help="Random seed")
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sites = load_active_sites()
    excluded = load_excluded_dates()
    buckets = month_buckets(start, end)

    print(f"Stratified null sampler")
    print(f"  Target samples:  {args.num_samples}")
    print(f"  Date range:      {start} to {end}  ({len(buckets)} month buckets)")
    print(f"  Stations:        {len(sites)}")
    print(f"  Excluded dates:  {len(excluded)} (known fall events)")
    print(f"  Output:          {out_dir}")
    print()

    s3 = get_s3_client()

    # Plan draws: cycle month buckets evenly so every month is represented.
    # Each draw = (month bucket -> random day, random station) -> list -> pick file(s).
    planned = []  # (s3_key, station, local_path)
    seen_keys = set()
    draws_needed = args.num_samples
    attempts = 0
    max_attempts = args.num_samples * 6  # guard against dead station-days

    print("Planning downloads (listing S3)...")
    bucket_idx = 0
    while len(planned) < draws_needed and attempts < max_attempts:
        attempts += 1
        year, month = buckets[bucket_idx % len(buckets)]
        bucket_idx += 1

        d = random_day_in_month(year, month, start, end, excluded)
        if d is None:
            continue
        station = random.choice(sites)

        keys = get_station_files(s3, station, str(d.year), f"{d.month:02d}", f"{d.day:02d}")
        valid = [k for k in keys if is_valid_nexrad_file(k.split("/")[-1])]
        if not valid:
            continue

        have = already_have(out_dir, station)
        random.shuffle(valid)
        taken = 0
        for k in valid:
            if taken >= args.per_draw:
                break
            fn = k.split("/")[-1]
            if k in seen_keys or fn in have:
                continue
            seen_keys.add(k)
            planned.append((k, station, str(out_dir / station / fn)))
            taken += 1

        if len(planned) % 500 == 0 and len(planned) > 0:
            print(f"  planned {len(planned)}/{draws_needed} (attempts {attempts})")

    print(f"\nPlanned {len(planned)} downloads. Starting {args.workers} workers...\n")

    # Ensure station dirs exist
    for _, station, _ in planned:
        (out_dir / station).mkdir(parents=True, exist_ok=True)

    def worker(key, local_path):
        client = get_s3_client()  # boto3 clients are not thread-safe
        return download_s3_file(client, key, local_path, max_retries=4)

    ok = fail = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(worker, k, lp): k for k, _, lp in planned}
        for i, fut in enumerate(as_completed(futs), 1):
            if fut.result():
                ok += 1
            else:
                fail += 1
            if i % 500 == 0 or i == len(planned):
                print(f"  downloaded {i}/{len(planned)}  (ok={ok}, fail={fail})")

    # Coverage report
    by_station = {}
    by_month = {}
    for _, station, lp in planned:
        by_station[station] = by_station.get(station, 0) + 1
        fn = Path(lp).name  # KXXXYYYYMMDD_...
        ym = fn[4:10]  # YYYYMM
        by_month[ym] = by_month.get(ym, 0) + 1

    print(f"\n{'='*50}")
    print(f"Done. {ok} downloaded, {fail} failed.")
    print(f"Stations covered: {len(by_station)}/{len(sites)}")
    print(f"Months covered:   {len(by_month)}")
    print(f"Per-month counts: {dict(sorted(by_month.items()))}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
