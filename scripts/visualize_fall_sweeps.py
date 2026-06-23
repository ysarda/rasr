"""
Render FULL radar sweeps (one image per field x elevation) for manual boxing.

No detector, no markers, no cropping to fall coordinates. Each image is the whole
PPI for one field at one elevation, centred on the radar, as a fixed-extent
fixed-pixel raster so bounding boxes drawn in a labelling tool map deterministically
back to radar/geographic coordinates.

Layout:
  fall_sweeps/<event>/<station>_<HHMMSS>Z/<field>__el<elev>.png
  fall_sweeps/manifest.json   - per-image {station, radar_lat, radar_lon, elev,
                                field, ext_km, px} for converting box pixels -> geo

Pixel -> geo (for ingesting your XML later), per image of size px*px, extent ext km:
  x_east_km  = -ext + (col + 0.5)/px * 2*ext            (col 0 = west)
  y_north_km = +ext - (row + 0.5)/px * 2*ext            (row 0 = top = north)
  lat = radar_lat + y_north/111.32
  lon = radar_lon + x_east/(111.32*cos(radar_lat))
"""

import argparse
import glob
import json
import math
import os
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pyart
import yaml

import sys
sys.path.append(str(Path(__file__).parent))
from region_detector import _elev_group_sweeps

import warnings
warnings.filterwarnings('ignore')

FN_RE = re.compile(r"(\w{4})(\d{8})_(\d{6})")
DEG = math.pi / 180.0

# (field, which sweep, cmap, vmin, vmax)
FIELDS = [
    ('reflectivity', 'surv', 'turbo', -10, 60),
    ('velocity', 'dop', 'RdBu_r', -30, 30),
    ('spectrum_width', 'dop', 'viridis', 0, 12),
    ('cross_correlation_ratio', 'surv', 'plasma', 0.2, 1.05),
    ('differential_reflectivity', 'surv', 'RdBu_r', -2, 6),
]


def parse_station_date(fn):
    m = FN_RE.search(fn)
    return (m.group(1), m.group(2)) if m else (None, None)


def file_hhmmss(fn):
    m = FN_RE.search(fn)
    return m.group(3) if m else '??????'


def _grid_full(radar, sweep, field, ext, px):
    """Grid a whole sweep into a px*px image over [-ext,ext]^2 centred on radar."""
    img = np.full((px, px), np.nan, dtype=np.float32)
    if field not in radar.fields:
        return img
    sl = radar.get_slice(sweep)
    az = np.deg2rad(radar.azimuth['data'][sl])
    rng = radar.range['data'] / 1000.0
    elev = float(radar.fixed_angle['data'][sweep])
    gr = rng * math.cos(elev * DEG)
    x = gr[None, :] * np.sin(az)[:, None]
    y = gr[None, :] * np.cos(az)[:, None]
    d = radar.fields[field]['data'][sl]
    m = ~np.ma.getmaskarray(d) if hasattr(d, 'mask') else np.ones(d.shape, bool)
    win = m & (x > -ext) & (x < ext) & (y > -ext) & (y < ext)
    xi = ((x[win] + ext) / (2 * ext) * (px - 1)).astype(int)
    yi = ((y[win] + ext) / (2 * ext) * (px - 1)).astype(int)
    img[yi, xi] = np.asarray(d)[win]
    return img


def _save_sweep(img, cmap, vmin, vmax, out):
    norm = mcolors.Normalize(vmin, vmax)
    rgba = plt.get_cmap(cmap)(norm(img))
    rgba[np.isnan(img)] = (0, 0, 0, 1)          # no-data -> black
    plt.imsave(out, rgba, origin='lower')        # north up


def render_file(path, ext, n_elev, px, out_dir, event, date):
    radar = pyart.io.read(str(path))
    rlat = float(radar.latitude['data'][0])
    rlon = float(radar.longitude['data'][0])
    st = parse_station_date(os.path.basename(path))[0]
    t = file_hhmmss(os.path.basename(path))
    safe = f"{date}_{event.replace(' ', '_').replace('/', '-')}"   # date-prefixed, sorts by date
    edir = Path(out_dir) / safe
    edir.mkdir(parents=True, exist_ok=True)

    elevs = sorted(set(round(float(a), 1) for a in radar.fixed_angle['data']))[:n_elev]
    entries = []
    for elev in elevs:
        surv, dop = _elev_group_sweeps(radar, elev)
        for field, which, cmap, vmin, vmax in FIELDS:
            if field not in radar.fields:
                continue
            sweep = surv if which == 'surv' else dop
            img = _grid_full(radar, sweep, field, ext, px)
            fname = f"{st}_{t}Z__{field}__el{elev:.1f}.png"    # flat, self-describing
            _save_sweep(img, cmap, vmin, vmax, edir / fname)
            entries.append({
                'image': f"{safe}/{fname}",
                'event': event, 'station': st, 'file': os.path.basename(path),
                'radar_lat': rlat, 'radar_lon': rlon,
                'elev': elev, 'field': field, 'ext_km': ext, 'px': px,
            })
    return entries


def _worker(args):
    try:
        return render_file(*args)
    except Exception as e:
        return [{'error': f"{args[0]}: {e}"}]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--events', default='falls_events.yaml')
    ap.add_argument('--positive_dir', default='data/positive')
    ap.add_argument('--out_dir', default='fall_sweeps')
    ap.add_argument('--ext_km', type=float, default=250.0)
    ap.add_argument('--n_elev', type=int, default=9)
    ap.add_argument('--px', type=int, default=1000)
    ap.add_argument('--only_event', default=None, help='render just one event (substring match)')
    ap.add_argument('--new_only', action='store_true',
                    help='skip events whose dated folder already exists; merge into manifest')
    ap.add_argument('--workers', type=int, default=10)
    args = ap.parse_args()

    ev = yaml.safe_load(open(args.events))
    key2ev = {}
    for e in ev['events']:
        loc = e.get('location', {})
        if loc.get('latitude') is None:
            continue
        date = e['date'].replace('-', '')
        for s in e.get('radar_stations', []):
            key2ev[(s, date)] = (e['name'], e['date'])

    def safe_dir(name, date):
        return f"{date}_{name.replace(' ', '_').replace('/', '-')}"

    jobs = []
    for path in glob.glob(os.path.join(args.positive_dir, '*', '*')):
        fn = os.path.basename(path)
        if fn.endswith('_MDM'):
            continue
        st, date = parse_station_date(fn)
        hit = key2ev.get((st, date))
        if not hit:
            continue
        name, date_str = hit
        if args.only_event and args.only_event.lower() not in name.lower():
            continue
        if args.new_only and (Path(args.out_dir) / safe_dir(name, date_str)).is_dir():
            continue
        jobs.append((path, args.ext_km, args.n_elev, args.px, args.out_dir, name, date_str))

    print(f"Rendering {len(jobs)} files -> {args.out_dir}/ "
          f"(ext ±{args.ext_km:.0f} km, {args.px}px, {args.n_elev} beams x {len(FIELDS)} fields)")
    new_entries = []
    done = 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_worker, j) for j in jobs]
        for fut in as_completed(futs):
            for r in fut.result():
                if 'error' in r:
                    print('  FAIL', r['error'])
                else:
                    new_entries.append(r)
            done += 1
            if done % 40 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)} files, {len(new_entries)} images")

    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    man_path = Path(args.out_dir) / 'manifest.json'
    manifest = json.load(open(man_path)) if man_path.exists() else []
    have = {m['image'] for m in manifest}
    manifest += [e for e in new_entries if e['image'] not in have]
    with open(man_path, 'w') as f:
        json.dump(manifest, f, indent=0)
    print(f"Done. +{len(new_entries)} new images; manifest now {len(manifest)} entries")


if __name__ == '__main__':
    main()
