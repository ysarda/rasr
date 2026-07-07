"""
Evaluate the signature + descent-coherence detector against known events.

Events are keyed by (station, date) so the same station can host different events
on different dates (e.g. KGSP/KMRX host both Ingalls NC and Crew-7). For each
event we run the coherence detector on its files and record the score of the best
track whose footprint falls within dist_km of the known location. Null scans give
the false-alarm side: the max track score per scan. We then sweep the score
threshold to show the recall vs false-alarm tradeoff and pick an operating point.
"""

import argparse
import glob
import os
import re
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import yaml

import sys
sys.path.append(str(Path(__file__).parent))
from signature_detector import haversine_km
from descent_coherence import detect_tracks

FN_RE = re.compile(r"(\w{4})(\d{8})_(\d{6})")


def parse_station_date(fname):
    m = FN_RE.search(fname)
    if not m:
        return None, None
    return m.group(1), m.group(2)   # station, YYYYMMDD


def track_min_dist(track, lat, lon):
    return min(haversine_km(lat, lon, a, b) for a, b in track['members_latlon'])


def _worker(args):
    """Returns (path, max_score_any, best_near_score, best_near_dist, error)."""
    path, truth, corridor, min_alt = args
    try:
        tracks = detect_tracks(path, corridor_km=corridor, min_alt_m=min_alt)
    except Exception as e:
        return path, 0.0, 0.0, None, None, f"{type(e).__name__}: {e}"
    if not tracks:
        return path, 0.0, 0.0, None, None, None
    max_any = max(t['score'] for t in tracks)
    best_near, best_dist, min_dist = 0.0, None, None
    if truth is not None:
        lat, lon, dist_km = truth
        for t in tracks:
            d = track_min_dist(t, lat, lon)
            if min_dist is None or d < min_dist:
                min_dist = d
            if d <= dist_km and t['score'] > best_near:
                best_near, best_dist = t['score'], d
    return path, max_any, best_near, best_dist, min_dist, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--events', default='falls_events.yaml')
    ap.add_argument('--positive_dir', default='data/positive')
    ap.add_argument('--null_dir', default='data/null')
    ap.add_argument('--dist_km', type=float, default=25.0)
    ap.add_argument('--null_sample', type=int, default=120)
    ap.add_argument('--workers', type=int, default=10)
    ap.add_argument('--corridor_km', type=float, default=10.0)
    ap.add_argument('--min_alt_m', type=float, default=300.0)
    args = ap.parse_args()

    # events keyed by (station, YYYYMMDD)
    ev = yaml.safe_load(open(args.events))
    key2ev = {}
    for e in ev['events']:
        loc = e.get('location', {})
        if loc.get('latitude') is None:
            continue
        date = e['date'].replace('-', '')
        for s in e.get('radar_stations', []):
            key2ev[(s, date)] = (loc['latitude'], loc['longitude'], e['name'])

    # gather positive files that match an event by (station, date)
    pos_jobs = []
    for path in glob.glob(os.path.join(args.positive_dir, '*', '*')):
        fn = os.path.basename(path)
        if fn.endswith('_MDM'):
            continue
        st, date = parse_station_date(fn)
        if (st, date) in key2ev:
            lat, lon, name = key2ev[(st, date)]
            pos_jobs.append((path, (lat, lon, args.dist_km), args.corridor_km, args.min_alt_m, name))

    n_events = len(set(name for *_, name in pos_jobs))
    print(f"Coherence eval: {len(pos_jobs)} positive files / {n_events} events; "
          f"corridor={args.corridor_km}km min_alt={args.min_alt_m}m dist={args.dist_km}km")

    # run positives
    best_per_event = {}   # name -> (score, dist, station)
    min_dist_event = {}   # name -> closest track member to truth (any score)
    errors = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_worker, j[:4]): j for j in pos_jobs}
        for fut in as_completed(futs):
            j = futs[fut]
            name = j[4]
            _, _max, near, dist, min_d, err = fut.result()
            if err:
                errors.append((name, os.path.basename(j[0]), err))
                continue
            if min_d is not None:
                cur_d = min_dist_event.get(name)
                if cur_d is None or min_d < cur_d:
                    min_dist_event[name] = min_d
            cur = best_per_event.get(name)
            if cur is None or near > cur[0]:
                st, _ = parse_station_date(os.path.basename(j[0]))
                best_per_event[name] = (near, dist, st)
    if errors:
        print(f"\n!! {len(errors)} positive files FAILED (excluded from best-score table):")
        for name, fn, err in errors:
            print(f"   {name:<26}{fn:<28}{err[:60]}")

    # run null
    null_files = []
    for st in sorted(os.listdir(args.null_dir)):
        fl = glob.glob(os.path.join(args.null_dir, st, '*'))
        if fl:
            null_files.append(fl[0])
    null_files = null_files[:args.null_sample]
    null_scores = []
    null_errors = 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_worker, (f, None, args.corridor_km, args.min_alt_m)) for f in null_files]
        for fut in as_completed(futs):
            _, max_any, _, _, _, err = fut.result()
            if err:
                null_errors += 1
                continue
            null_scores.append(max_any)
    if null_errors:
        print(f"!! {null_errors} null files FAILED (excluded)")
    null_scores = np.array(null_scores)

    # per-event table
    print("\n" + "=" * 74)
    print("PER-EVENT best near-truth track score")
    print(f"{'event':<26}{'station':<8}{'score':>7}{'dist_km':>9}{'nearest_any':>13}")
    ev_scores = []
    for name in sorted(best_per_event):
        sc, dist, st = best_per_event[name]
        ev_scores.append(sc)
        ds = f"{dist:.1f}" if dist is not None else "  -"
        md = min_dist_event.get(name)
        ms = f"{md:.1f}" if md is not None else "  -"
        print(f"{name:<26}{st:<8}{sc:>7.3f}{ds:>9}{ms:>13}")
    ev_scores = np.array(ev_scores)

    # threshold sweep
    print("\n" + "=" * 74)
    print(f"RECALL vs FALSE-ALARM  (null scans n={len(null_scores)})")
    print(f"{'thresh':>7}{'recall':>9}{'events_hit':>12}{'null_FA_rate':>14}{'FA_per_scan':>13}")
    for T in [0.30, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]:
        rec = (ev_scores >= T).mean()
        hit = int((ev_scores >= T).sum())
        fa = (null_scores >= T).mean()
        print(f"{T:>7.2f}{rec:>9.2f}{hit:>9}/{len(ev_scores):<3}{fa:>13.2f}{'':>4}")
    print("=" * 74)
    print(f"null score: mean {null_scores.mean():.3f}  median {np.median(null_scores):.3f}  "
          f"p90 {np.percentile(null_scores,90):.3f}  max {null_scores.max():.3f}")


if __name__ == '__main__':
    main()
