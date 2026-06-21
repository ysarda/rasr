"""
Descent-coherence stage.

The first-stage signature filter (signature_detector.detect_file) emits thousands
of low-rho_hv candidate gates per scan -- sea/ground clutter and biota are all
non-meteorological too. This stage links those candidates into 3D tracks and
keeps only the ones that look like a descending object: present across multiple
elevation beams, spanning altitude, with altitude rising consistently with beam
elevation (one body seen by several beams during the ~5 min volume).

Key idea: a clutter gate sits at one low altitude in one beam and connects to
nothing above it. A real entering object forms a coherent column/slant across
beams. We *seed* tracks from elevated candidates (clutter never seeds), extend
them downward, and score by physical coherence. The result is a soft score with a
tunable threshold -- not a hard multi-beam gate -- so few-beam meteorite events
still surface (at lower score).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

import sys
sys.path.append(str(Path(__file__).parent))
from signature_detector import detect_file, haversine_km

import warnings
warnings.filterwarnings('ignore')


# ----------------------------- union-find -----------------------------

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


# ----------------------------- linking -----------------------------

def _beam_extent_km(track):
    """Mean over beams of the max horizontal distance from each beam's centroid.

    A point object is compact at every beam (~1-2 km); an extended clutter patch
    spreads many km across a beam.
    """
    groups = {}
    for d in track:
        groups.setdefault(round(d['elev'] / 0.1), []).append(d)
    exts = []
    for g in groups.values():
        if len(g) == 1:
            exts.append(0.0)
            continue
        clat = np.mean([d['lat'] for d in g])
        clon = np.mean([d['lon'] for d in g])
        exts.append(max(haversine_km(clat, clon, d['lat'], d['lon']) for d in g))
    return float(np.mean(exts)) if exts else 0.0


def link_tracks(dets, corridor_km=10.0, min_alt_m=300.0):
    """Group candidate detections into spatial clusters (candidate tracks).

    All candidates above a small surface floor are clustered by horizontal
    proximity (<= corridor_km) using a grid hash so cost is ~linear in the number
    of candidates (no altitude seed: low-altitude meteorite falls are kept). The
    coherence score (compactness + multi-beam + monotonic descent) does the
    clutter rejection, so an extended ground/sea blob is linked but scores ~0.

    Returns a list of tracks; each track is a list of detection dicts.
    """
    pts = [d for d in dets if d['alt_m'] >= min_alt_m]
    n = len(pts)
    if n == 0:
        return []

    lat = np.array([d['lat'] for d in pts])
    lon = np.array([d['lon'] for d in pts])
    latr, lonr = np.radians(lat), np.radians(lon)

    # spatial grid hash: bin into ~corridor-sized cells, compare only within the
    # 3x3 neighbourhood of each cell. Distances are computed vectorised per cell,
    # and each point is unioned to one near neighbour (enough to grow connected
    # components) so the cost stays ~linear even in dense clutter.
    cell = max(corridor_km / 111.0, 1e-4)            # degrees (lat) approx
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
        # vectorised haversine: members (rows) x neighbourhood (cols)
        dlat = latr[mi][:, None] - latr[ni][None, :]
        dlon = lonr[mi][:, None] - lonr[ni][None, :]
        hav = (np.sin(dlat / 2) ** 2 +
               np.cos(latr[mi])[:, None] * np.cos(latr[ni])[None, :] * np.sin(dlon / 2) ** 2)
        dist = 2 * R * np.arcsin(np.sqrt(np.clip(hav, 0, 1)))
        within = dist <= corridor_km
        for r in range(mi.size):
            row = within[r]
            row[ni == mi[r]] = False                 # exclude self
            hit = np.argmax(row)
            if row[hit]:
                uf.union(int(mi[r]), int(ni[hit]))

    clusters = {}
    for i in range(n):
        clusters.setdefault(uf.find(i), []).append(pts[i])
    return list(clusters.values())


# ----------------------------- scoring -----------------------------

def _distinct_elevations(track, tol=0.1):
    els = sorted(set(round(d['elev'] / tol) * tol for d in track))
    return els


def score_track(track):
    """Physical coherence score in [0,1] plus features and descent profile."""
    els = _distinct_elevations(track)
    n_elev = len(els)
    alts = np.array([d['alt_m'] for d in track])
    elevs = np.array([d['elev'] for d in track])
    rhos = np.clip(np.array([d['rhohv'] for d in track]), 0, 1)
    vels = [d['velocity'] for d in track if d['velocity'] is not None]

    alt_span = float(alts.max() - alts.min())

    # monotonicity: altitude should rise with beam elevation (one descending body)
    if n_elev >= 2 and np.ptp(elevs) > 0 and np.ptp(alts) > 0:
        mono = float(np.corrcoef(elevs, alts)[0, 1])
    else:
        mono = 0.0
    mono = max(0.0, mono)

    non_met = float(np.mean(1.0 - rhos))            # higher = more non-met

    # velocity coherence: some real radial motion, not a stationary smear
    if vels:
        vmag = float(np.mean(np.abs(vels)))
        v_score = min(vmag / 25.0, 1.0)
    else:
        v_score = 0.0

    # compactness: a real object is a thin structure (few gates per beam, small
    # horizontal extent per beam); extended clutter patches are not.
    gpb = len(track) / max(n_elev, 1)
    beam_extent = _beam_extent_km(track)
    f_compact = max(0.0, min(1.0, 1.0 - (gpb - 2.0) / 12.0))   # gpb<=2->1, >=14->0
    f_spread = max(0.0, min(1.0, 1.0 - beam_extent / 6.0))     # <6km across ->ok

    # feature -> [0,1] transforms
    f_nelev = min((n_elev - 1) / 3.0, 1.0)          # 1 beam=0, 4+ beams=1
    f_span = min(alt_span / 5000.0, 1.0)            # 5 km span = full

    # coherence base, modulated multiplicatively by compactness so a diffuse
    # clutter blob cannot score high no matter how many beams it spans.
    base = (0.40 * f_nelev + 0.30 * mono + 0.15 * f_span +
            0.10 * non_met + 0.05 * v_score)
    score = base * f_compact * f_spread

    profile = sorted(
        [{'elev': d['elev'], 'alt_m': d['alt_m'], 'rhohv': d['rhohv'],
          'velocity': d['velocity'], 'lat': d['lat'], 'lon': d['lon'],
          'range_km': d['range_km'], 'reflectivity': d['reflectivity']}
         for d in track],
        key=lambda p: -p['alt_m'])

    # --- extra descriptive features for the downstream classifier ---
    ranges = np.array([d['range_km'] for d in track])
    refls = np.array([d['reflectivity'] for d in track])
    allv = np.array([d['velocity'] for d in track if d['velocity'] is not None], dtype=float)

    # descent geometry: a real descent has range INCREASING as altitude drops
    # (object travels outward/down), so corr(alt, range) is strongly negative.
    # A spurious vertical stack (high-beam + surface return at the same range)
    # has ~no range variation -> corr ~0 and ~0 horizontal travel.
    if len(track) >= 2 and np.ptp(ranges) > 0 and np.ptp(alts) > 0:
        range_alt_corr = float(np.corrcoef(alts, ranges)[0, 1])
    else:
        range_alt_corr = 0.0
    range_span_km = float(ranges.max() - ranges.min())
    horiz_disp_km = haversine_km(profile[0]['lat'], profile[0]['lon'],
                                 profile[-1]['lat'], profile[-1]['lon'])

    if allv.size:
        vmean_abs = float(np.abs(allv).mean())
        vmax_abs = float(np.abs(allv).max())
        frac_inbound = float(np.mean(allv < 0))
        vel_std = float(np.std(allv))
    else:
        vmean_abs = vmax_abs = frac_inbound = vel_std = 0.0

    features = {
        'n_elev': n_elev,
        'n_gates': len(track),
        'gates_per_beam': gpb,
        'beam_extent_km': beam_extent,
        'alt_span_m': alt_span,
        'alt_max_m': float(alts.max()),
        'alt_min_m': float(alts.min()),
        'monotonicity': mono,
        'non_met': non_met,
        'rho_min': float(rhos.min()),
        'rho_mean': float(rhos.mean()),
        'range_alt_corr': range_alt_corr,
        'range_span_km': range_span_km,
        'horiz_disp_km': horiz_disp_km,
        'vmean_abs': vmean_abs,
        'vmax_abs': vmax_abs,
        'frac_inbound': frac_inbound,
        'vel_std': vel_std,
        'n_with_vel': int(allv.size),
        'refl_mean': float(refls.mean()),
        'refl_max': float(refls.max()),
        'coherence_score': float(score),
    }

    return {
        'score': float(score),
        'features': features,
        'n_elev': n_elev,
        'alt_span_m': alt_span,
        'monotonicity': mono,
        'non_met': non_met,
        'v_score': v_score,
        'gates_per_beam': gpb,
        'beam_extent_km': beam_extent,
        'f_compact': f_compact,
        'n_gates': len(track),
        'profile': profile,
        # representative positions
        'lat_top': profile[0]['lat'], 'lon_top': profile[0]['lon'],
        'lat_bot': profile[-1]['lat'], 'lon_bot': profile[-1]['lon'],
        'members_latlon': [(p['lat'], p['lon']) for p in profile],
    }


def detect_tracks(path, corridor_km=10.0, min_alt_m=300.0, **filter_kw):
    """Full pipeline: signature filter -> link -> score. Returns ranked tracks."""
    filter_kw.setdefault('max_targets', 100000)
    dets = detect_file(path, **filter_kw)
    tracks = [score_track(t) for t in link_tracks(dets, corridor_km, min_alt_m)]
    tracks.sort(key=lambda t: t['score'], reverse=True)
    return tracks


# ----------------------------- CLI -----------------------------

def main():
    ap = argparse.ArgumentParser(description='Descent-coherence detector (single file)')
    ap.add_argument('path')
    ap.add_argument('--corridor-km', type=float, default=10.0)
    ap.add_argument('--min-alt-m', type=float, default=300.0)
    ap.add_argument('--top', type=int, default=5)
    args = ap.parse_args()

    tracks = detect_tracks(args.path, corridor_km=args.corridor_km, min_alt_m=args.min_alt_m)
    print(f"{len(tracks)} coherent tracks in {Path(args.path).name}\n")
    for t in tracks[:args.top]:
        print(f"score={t['score']:.3f}  beams={t['n_elev']}  alt_span={t['alt_span_m']:.0f}m  "
              f"mono={t['monotonicity']:.2f}  non_met={t['non_met']:.2f}  "
              f"gpb={t['gates_per_beam']:.1f}  extent={t['beam_extent_km']:.1f}km  gates={t['n_gates']}")
        for p in t['profile']:
            v = f"{p['velocity']:.1f}" if p['velocity'] is not None else "  -"
            print(f"    el{p['elev']:>5.2f}  alt{p['alt_m']:>7.0f}m  rng{p['range_km']:>6.1f}km  "
                  f"refl{p['reflectivity']:>6.1f}  vel{v:>7}  rho{p['rhohv']:.2f}  "
                  f"[{p['lat']:.4f},{p['lon']:.4f}]")
        print()


if __name__ == '__main__':
    main()
