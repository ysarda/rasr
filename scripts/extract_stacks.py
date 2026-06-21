"""
Extract multi-sweep "beam-stack" patches for the CNN.

Candidate = a cross-sweep cluster of signature-filter gates (one per object, NOT
fragmented per sweep). For each candidate we crop a patch at its ground centroid
from the lowest K elevation beams, 3 channels each (reflectivity, velocity,
rho_hv), and stack them -> (3*K, px, px). This lets the CNN learn the vertical
beam structure + local texture that we previously hand-crafted as features, with
no descent-tracking or hand-engineered statistics.

Output: data/stacks.npz  (X (N,3K,px,px) float16, y, groups, dist)
Labels: 1 = candidate within dist_km of event truth in a positive file; 0 = null.
"""

import argparse
import glob
import math
import os
import random
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pyart

import sys
sys.path.append(str(Path(__file__).parent))
from signature_detector import detect_file, haversine_km
from region_detector import _cluster, _grid_global, _crop, _elev_group_sweeps

import yaml
import warnings
warnings.filterwarnings('ignore')

FN_RE = re.compile(r"(\w{4})(\d{8})_(\d{6})")
K = 6                      # number of lowest beams in the stack
PATCH_PX = 32
PATCH_KM = 16.0
EXT_KM = 250.0


def parse_station_date(fn):
    m = FN_RE.search(fn)
    return (m.group(1), m.group(2)) if m else (None, None)


def _lowest_elevations(radar, k):
    angles = sorted(set(round(float(a), 1) for a in radar.fixed_angle['data']))
    return angles[:k]


def extract_stacks(path, radius_km=10.0, min_alt_m=300.0):
    radar = pyart.io.read(str(path))
    rlat = float(radar.latitude['data'][0])
    rlon = float(radar.longitude['data'][0])
    dets = [d for d in detect_file(path, max_targets=100000) if d['alt_m'] >= min_alt_m]
    if not dets:
        return [], []
    clusters = _cluster(dets, radius_km)            # cross-sweep candidates

    # grid the lowest K beams once (refl, vel, rho per beam)
    res = PATCH_KM / PATCH_PX
    elevs = _lowest_elevations(radar, K)
    grids = []
    for elev in elevs:
        surv, dop = _elev_group_sweeps(radar, elev)
        grids.append((
            _grid_global(radar, surv, 'reflectivity', res, EXT_KM, 60.0),
            _grid_global(radar, dop, 'velocity', res, EXT_KM, 30.0),
            _grid_global(radar, surv, 'cross_correlation_ratio', res, EXT_KM, 1.0),
        ))
    zero = np.zeros((int(2 * EXT_KM / res),) * 2, dtype=np.float32)
    while len(grids) < K:                            # pad VCPs with few tilts
        grids.append((zero, zero, zero))

    stacks, centroids = [], []
    for cl in clusters:
        clat = float(np.mean([d['lat'] for d in cl]))
        clon = float(np.mean([d['lon'] for d in cl]))
        cx = (clon - rlon) * 111.32 * math.cos(rlat * math.pi / 180.0)
        cy = (clat - rlat) * 111.32
        chans = []
        for (g_refl, g_vel, g_rho) in grids:
            chans.append(_crop(g_refl, cx, cy, res, EXT_KM, PATCH_PX))
            chans.append(_crop(g_vel, cx, cy, res, EXT_KM, PATCH_PX))
            chans.append(_crop(g_rho, cx, cy, res, EXT_KM, PATCH_PX))
        stacks.append(np.stack(chans, axis=0))      # (3K, px, px)
        centroids.append((clat, clon))
    return stacks, centroids


def _worker(args):
    path, truth, dist_km, group, neg_per_file, seed = args
    try:
        stacks, cents = extract_stacks(path)
    except Exception:
        return [], [], [], []
    pos, negpool = [], []
    for s, (clat, clon) in zip(stacks, cents):
        if truth is not None:
            d = haversine_km(truth[0], truth[1], clat, clon)
            if d > dist_km:
                continue
            pos.append((s, 1, group, d))
        else:
            negpool.append((s, 0, group, -1.0))
    if negpool:
        rng = random.Random(hash((path, seed)) & 0xffffffff)
        rng.shuffle(negpool)
        negpool = negpool[:neg_per_file]
    rows = pos + negpool
    if not rows:
        return [], [], [], []
    X, y, g, dist = zip(*rows)
    return list(X), list(y), list(g), list(dist)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--events', default='falls_events.yaml')
    ap.add_argument('--positive_dir', default='data/positive')
    ap.add_argument('--null_dir', default='data/null')
    ap.add_argument('--out', default='data/stacks.npz')
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
    print(f"Beam-stacks from {n_pos_files} positive + {len(jobs)-n_pos_files} null files (K={K} beams)...")

    X, Y, G, D = [], [], [], []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_worker, j) for j in jobs]
        for i, fut in enumerate(as_completed(futs), 1):
            xs, ys, gs, ds = fut.result()
            X.extend(xs); Y.extend(ys); G.extend(gs); D.extend(ds)
            if i % 50 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} files, {len(Y)} candidates")

    Xa = np.stack(X).astype(np.float16)
    y = np.array(Y, dtype=np.int8)
    groups = np.array(G)
    dist = np.array(D, dtype=np.float32)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.out, X=Xa, y=y, groups=groups, dist=dist)
    n_pos = int((y == 1).sum())
    print(f"\nWrote {len(y)} candidates to {args.out}")
    print(f"  X {Xa.shape}   positives {n_pos} ({len(set(groups[y==1]))} events)   negatives {len(y)-n_pos}")


if __name__ == '__main__':
    main()
