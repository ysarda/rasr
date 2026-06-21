"""
Render a validation image per confirmed event for human review against ARES.

For each event we locate the best near-truth candidate track (the signature +
coherence detector run over the event's files), then render its detection sweep
as reflectivity / velocity / rho_hv, zoomed to the candidate, with the candidate
gates (white rings) and the known truth location (red star) marked. The title
carries the metadata needed to cross-check the ARES page.

A human compares each panel to the ARES event page and confirms whether it is a
clear fall signature; confirmed events become clean track-level positives.
"""

import argparse
import glob
import math
import os
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pyart
import yaml

import sys
sys.path.append(str(Path(__file__).parent))
from signature_detector import haversine_km
from descent_coherence import detect_tracks

import warnings
warnings.filterwarnings('ignore')

FN_RE = re.compile(r"(\w{4})(\d{8})_(\d{6})")
DEG = math.pi / 180.0


def parse_station_date(fn):
    m = FN_RE.search(fn)
    return (m.group(1), m.group(2)) if m else (None, None)


def file_hhmmss(fn):
    m = FN_RE.search(fn)
    return m.group(3) if m else None


def truth_xy(radar_lat, radar_lon, tlat, tlon):
    north = (tlat - radar_lat) * 111.32
    east = (tlon - radar_lon) * 111.32 * math.cos(radar_lat * DEG)
    return east, north


def _best_track_for_file(args):
    """Return (path, dist, profile) for the closest-to-truth track, or None."""
    path, tlat, tlon, corridor, min_alt = args
    try:
        tracks = detect_tracks(path, corridor_km=corridor, min_alt_m=min_alt)
    except Exception:
        return path, None, None
    best = None
    for t in tracks:
        d = min(haversine_km(tlat, tlon, a, b) for a, b in t['members_latlon'])
        if best is None or d < best[0]:
            best = (d, t)
    if best is None:
        return path, None, None
    return path, best[0], best[1]['profile']


def _ground_xy(radar, sweep, field):
    """Return (x_east_km, y_north_km, values, masked) for a sweep field."""
    sl = radar.get_slice(sweep)
    az = np.deg2rad(radar.azimuth['data'][sl])
    rng = radar.range['data'] / 1000.0
    elev = radar.fixed_angle['data'][sweep] * DEG
    gr = rng * math.cos(elev)
    x = gr[None, :] * np.sin(az)[:, None]
    y = gr[None, :] * np.cos(az)[:, None]
    d = radar.fields[field]['data'][sl]
    return x, y, d


def render_event(name, idx, path, dist, profile, truth, out_dir):
    radar = pyart.io.read(str(path))
    rlat = float(radar.latitude['data'][0])
    rlon = float(radar.longitude['data'][0])

    # candidate = clearest (lowest rho_hv) member; pick its elevation group
    cand = min(profile, key=lambda p: p['rhohv'])
    # candidate ground position from its lat/lon
    cex, cny = truth_xy(rlat, rlon, cand['lat'], cand['lon'])
    tex, tny = truth_xy(rlat, rlon, truth[0], truth[1])

    angles = np.asarray(radar.fixed_angle['data'])
    grp = [s for s in range(radar.nsweeps) if abs(angles[s] - cand['elev']) < 0.1]
    surv = next((s for s in grp if 'cross_correlation_ratio' in radar.fields and
                 (~radar.fields['cross_correlation_ratio']['data'][radar.get_slice(s)].mask).any()), grp[0])
    dop = next((s for s in grp if (~radar.fields['velocity']['data'][radar.get_slice(s)].mask).any()), surv)

    panels = [('reflectivity', surv, 'turbo', -10, 60),
              ('velocity', dop, 'RdBu_r', -30, 30),
              ('cross_correlation_ratio', surv, 'plasma', 0.2, 1.05)]

    W = 35.0
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    for ax, (field, sweep, cmap, vmin, vmax) in zip(axes, panels):
        if field not in radar.fields:
            ax.axis('off'); continue
        x, y, d = _ground_xy(radar, sweep, field)
        m = (x > cex - W) & (x < cex + W) & (y > cny - W) & (y < cny + W)
        if hasattr(d, 'mask'):
            m = m & ~d.mask
        sc = ax.scatter(x[m], y[m], c=np.asarray(d)[m], s=4, cmap=cmap, vmin=vmin, vmax=vmax)
        plt.colorbar(sc, ax=ax, shrink=0.8)
        # candidate gates in this elevation group
        for p in profile:
            if abs(p['elev'] - cand['elev']) < 0.6:
                pex, pny = truth_xy(rlat, rlon, p['lat'], p['lon'])
                ax.plot(pex, pny, 'o', mfc='none', mec='white', mew=1.6, ms=12)
        ax.plot(tex, tny, '*', color='red', ms=20, mec='black', label='ARES truth')
        ax.set_xlim(cex - W, cex + W); ax.set_ylim(cny - W, cny + W)
        ax.set_aspect('equal')
        ax.set_title(f"{field}  (el {radar.fixed_angle['data'][sweep]:.2f}°)")
        ax.set_xlabel('E (km)'); ax.set_ylabel('N (km)')

    vels = [p['velocity'] for p in profile if p['velocity'] is not None]
    vstr = f"{min(vels):.0f}..{max(vels):.0f}" if vels else "none"
    fig.suptitle(
        f"{name}  |  {parse_station_date(os.path.basename(path))[0]} "
        f"{file_hhmmss(os.path.basename(path))}Z  |  dist-to-truth {dist:.1f} km  |  "
        f"beams {len(set(round(p['elev'],1) for p in profile))}  alt "
        f"{min(p['alt_m'] for p in profile):.0f}-{max(p['alt_m'] for p in profile):.0f} m  "
        f"rho {min(p['rhohv'] for p in profile):.2f}  vel[{vstr}]",
        fontsize=12, fontweight='bold')
    plt.tight_layout()
    out = Path(out_dir) / f"{idx:02d}_{name.replace(' ', '_').replace('/', '-')}.png"
    plt.savefig(out, dpi=110, bbox_inches='tight')
    plt.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--events', default='falls_events.yaml')
    ap.add_argument('--positive_dir', default='data/positive')
    ap.add_argument('--out_dir', default='event_validation')
    ap.add_argument('--corridor_km', type=float, default=10.0)
    ap.add_argument('--min_alt_m', type=float, default=300.0)
    ap.add_argument('--workers', type=int, default=10)
    args = ap.parse_args()

    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    ev = yaml.safe_load(open(args.events))
    key2ev = {}
    for e in ev['events']:
        loc = e.get('location', {})
        if loc.get('latitude') is None:
            continue
        date = e['date'].replace('-', '')
        for s in e.get('radar_stations', []):
            key2ev.setdefault(e['name'], []).append((s, date, loc['latitude'], loc['longitude']))

    # gather one job per positive file, tagged by event
    jobs = {}   # event -> list of (path, tlat, tlon)
    for path in glob.glob(os.path.join(args.positive_dir, '*', '*')):
        fn = os.path.basename(path)
        if fn.endswith('_MDM'):
            continue
        st, date = parse_station_date(fn)
        for name, keys in key2ev.items():
            for (ks, kd, tlat, tlon) in keys:
                if ks == st and kd == date:
                    jobs.setdefault(name, []).append((path, tlat, tlon))

    # phase 1: find best near-truth track per event (parallel over files)
    flat = [(name, (p, tlat, tlon, args.corridor_km, args.min_alt_m))
            for name, lst in jobs.items() for (p, tlat, tlon) in lst]
    print(f"Scanning {len(flat)} files across {len(jobs)} events...")
    best = {}   # event -> (dist, path, profile, truth)
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_best_track_for_file, j[1]): j[0] for j in flat}
        # map path->truth for rendering
        truth_of = {j[1][0]: (j[1][1], j[1][2]) for j in flat}
        for fut in as_completed(futs):
            name = futs[fut]
            path, dist, profile = fut.result()
            if dist is None:
                continue
            if name not in best or dist < best[name][0]:
                best[name] = (dist, path, profile, truth_of[path])

    # phase 2: render
    print(f"Rendering {len(best)} event panels to {args.out_dir}/ ...")
    for idx, name in enumerate(sorted(best), 1):
        dist, path, profile, truth = best[name]
        try:
            out = render_event(name, idx, path, dist, profile, truth, args.out_dir)
            print(f"  {name:<24} dist {dist:5.1f}km -> {out.name}")
        except Exception as e:
            print(f"  {name:<24} render failed: {e}")


if __name__ == '__main__':
    main()
