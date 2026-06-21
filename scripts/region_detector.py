"""
Per-sweep region detector (simplified pipeline).

The ablation showed cross-sweep descent tracking adds no signal, so the detection
unit here is a single-sweep REGION: a compact spatial cluster of signature-filter
candidate gates within one elevation. Each region yields:
  - a tabular feature vector (rho_hv / velocity / reflectivity / size / altitude)
  - optionally a multi-channel patch (reflectivity, velocity, rho_hv) for a CNN

This replaces descent_coherence's cross-sweep tracking for detection. Candidate
generation (signature filter) and intra-sweep spatial clustering are kept because
they are what makes the problem tractable (~30k gates -> a few hundred regions).
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pyart

import sys
sys.path.append(str(Path(__file__).parent))
from signature_detector import detect_file, haversine_km

import warnings
warnings.filterwarnings('ignore')

DEG = math.pi / 180.0


# ----------------------------- clustering -----------------------------

class _UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, a):
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def _cluster(dets, radius_km):
    """Grid-hash spatial clustering of a list of gate dicts. Near-linear."""
    n = len(dets)
    if n == 0:
        return []
    lat = np.array([d['lat'] for d in dets])
    lon = np.array([d['lon'] for d in dets])
    latr, lonr = np.radians(lat), np.radians(lon)
    cell = max(radius_km / 111.0, 1e-4)
    ci = np.floor(lat / cell).astype(np.int64)
    cj = np.floor(lon / cell).astype(np.int64)
    grid = {}
    for i in range(n):
        grid.setdefault((ci[i], cj[i]), []).append(i)
    uf = _UF(n)
    R = 6371.0
    for (a, b), members in grid.items():
        neigh = []
        for da in (-1, 0, 1):
            for db in (-1, 0, 1):
                neigh.extend(grid.get((a + da, b + db), ()))
        mi = np.array(members)
        ni = np.array(neigh)
        dlat = latr[mi][:, None] - latr[ni][None, :]
        dlon = lonr[mi][:, None] - lonr[ni][None, :]
        hav = (np.sin(dlat / 2) ** 2 +
               np.cos(latr[mi])[:, None] * np.cos(latr[ni])[None, :] * np.sin(dlon / 2) ** 2)
        dist = 2 * R * np.arcsin(np.sqrt(np.clip(hav, 0, 1)))
        within = dist <= radius_km
        for r in range(mi.size):
            row = within[r]
            row[ni == mi[r]] = False
            hit = np.argmax(row)
            if row[hit]:
                uf.union(int(mi[r]), int(ni[hit]))
    clusters = {}
    for i in range(n):
        clusters.setdefault(uf.find(i), []).append(dets[i])
    return list(clusters.values())


# ----------------------------- features -----------------------------

def region_features(region):
    """Per-region tabular features (single sweep, no cross-sweep terms)."""
    lat = np.array([d['lat'] for d in region])
    lon = np.array([d['lon'] for d in region])
    rho = np.clip(np.array([d['rhohv'] for d in region]), 0, 1)
    refl = np.array([d['reflectivity'] for d in region])
    alt = np.array([d['alt_m'] for d in region])
    rng = np.array([d['range_km'] for d in region])
    vel = np.array([d['velocity'] for d in region if d['velocity'] is not None], dtype=float)

    clat, clon = float(lat.mean()), float(lon.mean())
    extent = max((haversine_km(clat, clon, a, b) for a, b in zip(lat, lon)), default=0.0)
    if vel.size:
        vmean_abs, vmax_abs = float(np.abs(vel).mean()), float(np.abs(vel).max())
        frac_inbound, vel_std = float(np.mean(vel < 0)), float(np.std(vel))
    else:
        vmean_abs = vmax_abs = frac_inbound = vel_std = 0.0

    return {
        'lat': clat, 'lon': clon,
        'elev': float(region[0]['elev']),
        'alt_m': float(alt.mean()),
        'range_km': float(rng.mean()),
        'n_gates': len(region),
        'extent_km': float(extent),
        'rho_min': float(rho.min()), 'rho_mean': float(rho.mean()),
        'refl_mean': float(refl.mean()), 'refl_max': float(refl.max()),
        'vmean_abs': vmean_abs, 'vmax_abs': vmax_abs,
        'frac_inbound': frac_inbound, 'vel_std': vel_std, 'n_with_vel': int(vel.size),
    }


FEATURE_COLS = [
    'elev', 'alt_m', 'range_km', 'n_gates', 'extent_km',
    'rho_min', 'rho_mean', 'refl_mean', 'refl_max',
    'vmean_abs', 'vmax_abs', 'frac_inbound', 'vel_std', 'n_with_vel',
]


# ----------------------------- patch extraction -----------------------------

def _ground_xy(az_deg, range_km, elev_deg):
    gr = range_km * math.cos(elev_deg * DEG)
    return gr * math.sin(az_deg * DEG), gr * math.cos(az_deg * DEG)


def _grid_global(radar, sweep, field, res_km, ext_km, norm):
    """Grid a whole sweep ONCE into a global Cartesian image (origin at -ext_km).

    Done once per sweep, then cropped per region -- far cheaper than re-gridding
    the sweep for every region.
    """
    n = int(2 * ext_km / res_km)
    img = np.zeros((n, n), dtype=np.float32)
    if field not in radar.fields:
        return img
    sl = radar.get_slice(sweep)
    az = radar.azimuth['data'][sl]
    rng = radar.range['data'] / 1000.0
    elev = float(radar.fixed_angle['data'][sweep])
    gr = rng * math.cos(elev * DEG)
    x = gr[None, :] * np.sin(np.deg2rad(az))[:, None]
    y = gr[None, :] * np.cos(np.deg2rad(az))[:, None]
    d = radar.fields[field]['data'][sl]
    m = ~np.ma.getmaskarray(d) if hasattr(d, 'mask') else np.ones(d.shape, bool)
    xi = ((x + ext_km) / res_km).astype(np.int32)
    yi = ((y + ext_km) / res_km).astype(np.int32)
    valid = m & (xi >= 0) & (xi < n) & (yi >= 0) & (yi < n)
    img[yi[valid], xi[valid]] = (np.asarray(d)[valid] / norm).astype(np.float32)
    return img


def _crop(img, cx, cy, res_km, ext_km, px):
    """Crop a px*px window from a global grid centred at ground (cx,cy)."""
    h = px // 2
    pcx = int((cx + ext_km) / res_km)
    pcy = int((cy + ext_km) / res_km)
    out = np.zeros((px, px), dtype=np.float32)
    y0, x0 = pcy - h, pcx - h
    sy0, sy1 = max(0, y0), min(img.shape[0], y0 + px)
    sx0, sx1 = max(0, x0), min(img.shape[1], x0 + px)
    if sy1 > sy0 and sx1 > sx0:
        out[sy0 - y0:sy0 - y0 + (sy1 - sy0), sx0 - x0:sx0 - x0 + (sx1 - sx0)] = img[sy0:sy1, sx0:sx1]
    return out


def _elev_group_sweeps(radar, elev):
    angles = np.asarray(radar.fixed_angle['data'])
    grp = [s for s in range(radar.nsweeps) if abs(angles[s] - elev) < 0.1]
    surv = next((s for s in grp if 'cross_correlation_ratio' in radar.fields and
                 (~radar.fields['cross_correlation_ratio']['data'][radar.get_slice(s)].mask).any()),
                grp[0] if grp else 0)
    dop = next((s for s in grp if 'velocity' in radar.fields and
                (~radar.fields['velocity']['data'][radar.get_slice(s)].mask).any()), surv)
    return surv, dop


def extract_regions(path, radius_km=4.0, min_alt_m=300.0,
                    want_patch=False, patch_px=32, patch_km=16.0, radar=None,
                    ext_km=250.0):
    """Return list of region dicts (features + members). If want_patch, each has
    a (3, px, px) 'patch' of [reflectivity, velocity, rho_hv]."""
    if radar is None:
        radar = pyart.io.read(str(path))
    dets = detect_file(path, max_targets=100000)
    dets = [d for d in dets if d['alt_m'] >= min_alt_m]
    # group by elevation, cluster within each elevation (per-sweep regions)
    by_elev = {}
    for d in dets:
        by_elev.setdefault(round(d['elev'], 1), []).append(d)

    res = patch_km / patch_px        # km per pixel
    regions = []
    for elev, gates in by_elev.items():
        clusters = _cluster(gates, radius_km)
        if want_patch and clusters:
            # grid the elevation's sweeps ONCE, then crop per region
            surv, dop = _elev_group_sweeps(radar, elev)
            g_refl = _grid_global(radar, surv, 'reflectivity', res, ext_km, 60.0)
            g_rho = _grid_global(radar, surv, 'cross_correlation_ratio', res, ext_km, 1.0)
            g_vel = _grid_global(radar, dop, 'velocity', res, ext_km, 30.0)
        for region in clusters:
            feats = region_features(region)
            rec = {'features': feats, 'members': region}
            if want_patch:
                cx, cy = _ground_xy(float(np.mean([g['az'] for g in region])),
                                    feats['range_km'], feats['elev'])
                rec['patch'] = np.stack([
                    _crop(g_refl, cx, cy, res, ext_km, patch_px),
                    _crop(g_vel, cx, cy, res, ext_km, patch_px),
                    _crop(g_rho, cx, cy, res, ext_km, patch_px),
                ], axis=0)
            regions.append(rec)
    return regions


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--patch', action='store_true')
    args = ap.parse_args()
    regs = extract_regions(args.path, want_patch=args.patch)
    print(f"{len(regs)} regions")
    for r in sorted(regs, key=lambda r: r['features']['rho_min'])[:8]:
        f = r['features']
        print(f"  el{f['elev']:.2f} alt{f['alt_m']:.0f} rng{f['range_km']:.0f} "
              f"n{f['n_gates']} ext{f['extent_km']:.1f}km rho{f['rho_min']:.2f} "
              f"refl{f['refl_max']:.0f} vmax{f['vmax_abs']:.0f}"
              + (f" patch{r['patch'].shape}" if 'patch' in r else ''))
