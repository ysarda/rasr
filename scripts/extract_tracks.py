"""
Extract track feature vectors for the supervised classifier.

Runs the signature + descent-coherence detector over positive (event) and null
files and writes one row per track to a CSV. Labels:
  1 = track in a positive file within dist_km of the known event location
  0 = any track in a null file
Tracks in positive files that are NOT near the truth are ambiguous (could be
real clutter) and are skipped to keep labels clean.

The `group` column (event name for positives, scan id for negatives) is used for
grouped cross-validation so the classifier is tested on held-out events, never on
a sibling track of a training example.
"""

import argparse
import csv
import glob
import os
import random
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import yaml

import sys
sys.path.append(str(Path(__file__).parent))
from signature_detector import haversine_km
from descent_coherence import detect_tracks

FN_RE = re.compile(r"(\w{4})(\d{8})_(\d{6})")

FEATURES = [
    'n_elev', 'n_gates', 'gates_per_beam', 'beam_extent_km',
    'alt_span_m', 'alt_max_m', 'alt_min_m', 'monotonicity', 'non_met',
    'frac_isolated',
    'rho_min', 'rho_mean', 'range_alt_corr', 'range_span_km', 'horiz_disp_km',
    'vmean_abs', 'vmax_abs', 'frac_inbound', 'vel_std', 'n_with_vel',
    'refl_mean', 'refl_max', 'coherence_score',
]
META = ['label', 'group', 'station', 'file', 'dist_km']


def parse_station_date(fname):
    m = FN_RE.search(fname)
    return (m.group(1), m.group(2)) if m else (None, None)


def _track_min_dist(track, lat, lon):
    return min(haversine_km(lat, lon, a, b) for a, b in track['members_latlon'])


def _worker(args):
    """Return list of CSV rows for one file."""
    path, truth, dist_km, group, corridor, min_alt = args
    station, _ = parse_station_date(os.path.basename(path))
    try:
        tracks = detect_tracks(path, corridor_km=corridor, min_alt_m=min_alt)
    except Exception:
        return []
    rows = []
    for t in tracks:
        f = t['features']
        if truth is not None:                       # positive file
            d = _track_min_dist(t, truth[0], truth[1])
            if d > dist_km:
                continue                            # ambiguous -> skip
            label, grp, dist = 1, group, d
        else:                                       # null file
            label, grp, dist = 0, group, ''
        row = {'label': label, 'group': grp, 'station': station,
               'file': os.path.basename(path), 'dist_km': dist}
        row.update({k: f[k] for k in FEATURES})
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--events', default='falls_events.yaml')
    ap.add_argument('--positive_dir', default='data/positive')
    ap.add_argument('--null_dir', default='data/null')
    ap.add_argument('--out', default='data/tracks.csv')
    ap.add_argument('--dist_km', type=float, default=25.0)
    ap.add_argument('--null_sample', type=int, default=250)
    ap.add_argument('--corridor_km', type=float, default=10.0)
    ap.add_argument('--min_alt_m', type=float, default=300.0)
    ap.add_argument('--workers', type=int, default=10)
    ap.add_argument('--seed', type=int, default=0)
    args = ap.parse_args()

    ev = yaml.safe_load(open(args.events))
    key2ev = {}
    for e in ev['events']:
        loc = e.get('location', {})
        if loc.get('latitude') is None:
            continue
        date = e['date'].replace('-', '')
        for s in e.get('radar_stations', []):
            key2ev[(s, date)] = (loc['latitude'], loc['longitude'], e['name'])

    jobs = []
    # positives
    for path in glob.glob(os.path.join(args.positive_dir, '*', '*')):
        fn = os.path.basename(path)
        if fn.endswith('_MDM'):
            continue
        st, date = parse_station_date(fn)
        if (st, date) in key2ev:
            lat, lon, name = key2ev[(st, date)]
            jobs.append((path, (lat, lon), args.dist_km, name, args.corridor_km, args.min_alt_m))

    # null sample
    rng = random.Random(args.seed)
    null_files = glob.glob(os.path.join(args.null_dir, '*', '*'))
    null_files = [f for f in null_files if not f.endswith('_MDM')]
    rng.shuffle(null_files)
    for path in null_files[:args.null_sample]:
        grp = 'null::' + os.path.basename(path)
        jobs.append((path, None, args.dist_km, grp, args.corridor_km, args.min_alt_m))

    n_pos_files = sum(1 for j in jobs if j[1] is not None)
    print(f"Extracting tracks from {n_pos_files} positive files + "
          f"{len(jobs) - n_pos_files} null files...")

    all_rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_worker, j) for j in jobs]
        for i, fut in enumerate(as_completed(futs), 1):
            all_rows.extend(fut.result())
            if i % 50 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} files, {len(all_rows)} tracks")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=META + FEATURES)
        w.writeheader()
        w.writerows(all_rows)

    n_pos = sum(1 for r in all_rows if r['label'] == 1)
    print(f"\nWrote {len(all_rows)} tracks to {args.out}")
    print(f"  positives: {n_pos}  (from {len(set(r['group'] for r in all_rows if r['label']==1))} events)")
    print(f"  negatives: {len(all_rows) - n_pos}")


if __name__ == '__main__':
    main()
