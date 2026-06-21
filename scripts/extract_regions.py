"""
Extract labeled per-sweep regions into a single .npz artifact.

Runs the simplified region detector over positive (event) and null files and
writes ONE file holding everything both downstream models need:
  X_patch   (N, 3, px, px) float16  - [reflectivity, velocity, rho_hv] crops (CNN)
  X_feat    (N, F)         float32   - tabular per-region features (GBT)
  feat_names                         - column names for X_feat
  y, groups, dist                    - labels, CV groups, distance-to-truth

Labels: 1 = region within dist_km of the event truth in a positive file;
0 = region in a null file (subsampled per file). Ambiguous regions (positive
file, far from truth) are skipped. `group` (event / null scan) drives grouped CV.
A single artifact means the tabular and patch views can never drift out of sync.
"""

import argparse
import glob
import os
import random
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import yaml

import sys
sys.path.append(str(Path(__file__).parent))
from signature_detector import haversine_km
from region_detector import extract_regions, FEATURE_COLS

FN_RE = re.compile(r"(\w{4})(\d{8})_(\d{6})")


def parse_station_date(fn):
    m = FN_RE.search(fn)
    return (m.group(1), m.group(2)) if m else (None, None)


def _worker(args):
    """Return (feat_rows, patches, labels, groups, dists) for one file."""
    path, truth, dist_km, group, neg_per_file, seed = args
    try:
        regs = extract_regions(path, want_patch=True)
    except Exception:
        return [], [], [], [], []
    pos, negpool = [], []
    for r in regs:
        f = r['features']
        feat = [f[k] for k in FEATURE_COLS]
        if truth is not None:
            d = haversine_km(truth[0], truth[1], f['lat'], f['lon'])
            if d > dist_km:
                continue
            pos.append((feat, r['patch'], 1, group, d))
        else:
            negpool.append((feat, r['patch'], 0, group, -1.0))
    if negpool:
        rng = random.Random(hash((path, seed)) & 0xffffffff)
        rng.shuffle(negpool)
        negpool = negpool[:neg_per_file]
    rows = pos + negpool
    if not rows:
        return [], [], [], [], []
    feats, patches, labels, groups, dists = zip(*rows)
    return list(feats), list(patches), list(labels), list(groups), list(dists)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--events', default='falls_events.yaml')
    ap.add_argument('--positive_dir', default='data/positive')
    ap.add_argument('--null_dir', default='data/null')
    ap.add_argument('--out', default='data/regions.npz')
    ap.add_argument('--dist_km', type=float, default=25.0)
    ap.add_argument('--null_sample', type=int, default=150)
    ap.add_argument('--neg_per_file', type=int, default=40)
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
    for path in glob.glob(os.path.join(args.positive_dir, '*', '*')):
        fn = os.path.basename(path)
        if fn.endswith('_MDM'):
            continue
        st, date = parse_station_date(fn)
        if (st, date) in key2ev:
            lat, lon, name = key2ev[(st, date)]
            jobs.append((path, (lat, lon), args.dist_km, name, args.neg_per_file, args.seed))

    rng = random.Random(args.seed)
    null_files = [f for f in glob.glob(os.path.join(args.null_dir, '*', '*')) if not f.endswith('_MDM')]
    rng.shuffle(null_files)
    for path in null_files[:args.null_sample]:
        jobs.append((path, None, args.dist_km, 'null::' + os.path.basename(path),
                     args.neg_per_file, args.seed))

    n_pos_files = sum(1 for j in jobs if j[1] is not None)
    print(f"Extracting regions from {n_pos_files} positive + {len(jobs)-n_pos_files} null files...")

    F, P, Y, G, D = [], [], [], [], []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_worker, j) for j in jobs]
        for i, fut in enumerate(as_completed(futs), 1):
            feats, patches, labels, groups, dists = fut.result()
            F.extend(feats); P.extend(patches); Y.extend(labels); G.extend(groups); D.extend(dists)
            if i % 50 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} files, {len(Y)} regions")

    X_feat = np.array(F, dtype=np.float32)
    X_patch = np.stack(P).astype(np.float16)
    y = np.array(Y, dtype=np.int8)
    groups = np.array(G)
    dist = np.array(D, dtype=np.float32)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.out, X_patch=X_patch, X_feat=X_feat,
                        feat_names=np.array(FEATURE_COLS), y=y, groups=groups, dist=dist)
    n_pos = int((y == 1).sum())
    print(f"\nWrote {len(y)} regions to {args.out}")
    print(f"  X_patch {X_patch.shape}  X_feat {X_feat.shape}")
    print(f"  positives: {n_pos} ({len(set(groups[y==1]))} events)   negatives: {len(y)-n_pos}")


if __name__ == '__main__':
    main()
