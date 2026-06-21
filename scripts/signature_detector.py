"""
Signature-based re-entry / fall detector (label-free).

Ported and adapted from the RASR Replit project's detection method, but run on
REAL decoded NEXRAD Level II moments via pyART (no synthetic data, no hardcoded
results). The detector is a classical two-stage filter + kinematic classifier:

  Stage 1 - rho_hv gate: weather (rain/snow) has correlation coefficient
            rho_hv > ~0.97; metal / parachute / debris is 0.2-0.6. Gates with
            rho_hv >= rho_max are rejected as meteorological.
  Stage 2 - spatial isolation: a re-entering object is a point source - its
            reflectivity must exceed neighbouring gates by > iso_db, with few
            valid neighbours. If rho_hv strongly confirms non-met (< rho_strict)
            the isolation requirement is relaxed (a large body fills gates).

NEXRAD low tilts are split cuts: rho_hv lives in the surveillance sweep, radial
velocity in the paired Doppler sweep. We detect on the surveillance sweep and
look up velocity from the Doppler sweep at the same elevation for classification.

Geometry uses the 4/3-earth beam model for altitude and a great-circle step for
the ground position.
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path

import numpy as np
import pyart
import warnings

warnings.filterwarnings('ignore')

DEG = math.pi / 180.0
EARTH_R = 6371000.0          # m
KE = 4.0 / 3.0               # effective earth radius factor (standard refraction)


# ----------------------------- geometry -----------------------------

def beam_to_latlonalt(lat0, lon0, az_deg, slant_m, elev_deg):
    """4/3-earth beam geometry -> (lat, lon, altitude_m)."""
    el = elev_deg * DEG
    ke_r = KE * EARTH_R
    # height above radar (4/3 earth)
    alt = math.sqrt(slant_m ** 2 + ke_r ** 2 + 2 * slant_m * ke_r * math.sin(el)) - ke_r
    # ground (great-circle) distance along the earth
    ground = ke_r * math.asin(slant_m * math.cos(el) / (ke_r + alt))
    ang = ground / EARTH_R
    az = az_deg * DEG
    lat0r, lon0r = lat0 * DEG, lon0 * DEG
    lat = math.asin(math.sin(lat0r) * math.cos(ang) +
                    math.cos(lat0r) * math.sin(ang) * math.cos(az))
    lon = lon0r + math.atan2(math.sin(az) * math.sin(ang) * math.cos(lat0r),
                             math.cos(ang) - math.sin(lat0r) * math.sin(lat))
    return lat / DEG, lon / DEG, alt


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = lat1 * DEG, lat2 * DEG
    dp = (lat2 - lat1) * DEG
    dl = (lon2 - lon1) * DEG
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R / 1000.0 * math.asin(math.sqrt(a))


# ----------------------------- classification -----------------------------

def classify(refl, vel, rhohv):
    """Kinematic + dual-pol classification (ported from the Replit method)."""
    av = abs(vel) if vel is not None else None
    rho_conf = rhohv is not None and rhohv < 0.7
    boost = 0.08 if rho_conf else 0.0
    if refl > 60:
        return 'unclassified', 0.35
    if av is not None and av > 45 and refl > 15:
        return 'meteor', min(0.95, 0.82 + boost)
    if av is not None and av > 38:
        return 'meteor', min(0.90, 0.67 + boost)
    if av is not None and av > 25 and refl > 20:
        return 'intact_aso', min(0.92, 0.78 + boost)
    if av is not None and av > 12 and refl > 8:
        return 'aso_debris', min(0.85, 0.61 + boost)
    if rho_conf and refl > 20:
        return 'intact_aso', 0.58
    if rho_conf and refl > 8:
        return 'aso_debris', 0.50
    return 'unclassified', 0.40


# ----------------------------- detection -----------------------------

def _elevation_groups(radar):
    ang = np.asarray(radar.fixed_angle['data'], dtype=np.float32)
    groups, used = [], set()
    for i in range(radar.nsweeps):
        if i in used:
            continue
        g = [i]
        used.add(i)
        for j in range(i + 1, radar.nsweeps):
            if j not in used and abs(ang[j] - ang[i]) < 0.05:
                g.append(j)
                used.add(j)
        groups.append(g)
    return groups


def _sweep_field(radar, sweep, name):
    if name not in radar.fields:
        return None
    d = radar.fields[name]['data'][radar.get_slice(sweep)]
    return d  # masked array (rays, gates)


def _velocity_lookup(radar, dop_sweep, az_deg, gate_idx):
    """Nearest-azimuth velocity at the given range gate in a Doppler sweep."""
    if dop_sweep is None:
        return None
    vel = _sweep_field(radar, dop_sweep, 'velocity')
    if vel is None:
        return None
    az = radar.azimuth['data'][radar.get_slice(dop_sweep)]
    d = np.abs((az - az_deg + 180) % 360 - 180)
    ri = int(np.argmin(d))
    if gate_idx >= vel.shape[1]:
        return None
    v = vel[ri, gate_idx]
    if np.ma.is_masked(v):
        return None
    return float(v)


def detect_file(path, rho_max=0.85, rho_strict=0.7, iso_db=8.0,
                refl_min=5.0, refl_max=65.0, rng_min_km=5.0, rng_max_km=200.0,
                max_targets=30):
    """Run the signature detector on one NEXRAD file. Returns list of detections."""
    radar = pyart.io.read(str(path))
    lat0 = float(radar.latitude['data'][0])
    lon0 = float(radar.longitude['data'][0])
    rng_m = np.asarray(radar.range['data'], dtype=np.float64)   # (gates,)
    rng_km = rng_m / 1000.0
    dets = []

    for group in _elevation_groups(radar):
        # surveillance sweep = the one carrying rho_hv; doppler = carries velocity
        surv = dop = None
        for s in group:
            rh = _sweep_field(radar, s, 'cross_correlation_ratio')
            if rh is not None and (~rh.mask).sum() > 0 and surv is None:
                surv = s
            vl = _sweep_field(radar, s, 'velocity')
            if vl is not None and (~vl.mask).sum() > 0 and dop is None:
                dop = s
        if surv is None:
            continue
        elev = float(radar.fixed_angle['data'][surv])
        az = radar.azimuth['data'][radar.get_slice(surv)]            # (rays,)

        refl = _sweep_field(radar, surv, 'reflectivity')
        rho = _sweep_field(radar, surv, 'cross_correlation_ratio')
        if refl is None or rho is None:
            continue
        nrays, ngates = refl.shape

        rf = np.ma.filled(refl, -999.0).astype(np.float64)
        rv = np.ma.getmaskarray(refl)                                # True = invalid
        valid = ~rv & (rf >= refl_min) & (rf <= refl_max)
        rho_f = np.ma.filled(rho, 9.9).astype(np.float64)

        # range gate window (broadcast over rays)
        rmask = (rng_km >= rng_min_km) & (rng_km <= rng_max_km)
        valid &= rmask[np.newaxis, :]
        # rho_hv weather rejection
        rho_ok = (rho_f < rho_max)
        cand = valid & rho_ok
        if not cand.any():
            continue

        # neighbour stats for isolation (az wraps on axis 0; range clamps on axis 1)
        big_neg = -999.0
        nb_refl = []
        nb_valid = []
        for shift, ax in [(+1, 0), (-1, 0)]:
            nb_refl.append(np.roll(rf, shift, axis=ax))
            nb_valid.append(np.roll(~rv, shift, axis=ax))
        # range neighbours (no wrap)
        left = np.full_like(rf, big_neg); left[:, 1:] = rf[:, :-1]
        left_v = np.zeros_like(rv); left_v[:, 1:] = (~rv)[:, :-1]
        right = np.full_like(rf, big_neg); right[:, :-1] = rf[:, 1:]
        right_v = np.zeros_like(rv); right_v[:, :-1] = (~rv)[:, 1:]
        nb_refl += [left, right]
        nb_valid += [left_v, right_v]

        nb_stack = np.stack(nb_refl, axis=0)              # (4, rays, gates)
        nb_vmask = np.stack(nb_valid, axis=0)
        nb_stack = np.where(nb_vmask, nb_stack, big_neg)
        max_nb = nb_stack.max(axis=0)
        n_valid_nb = nb_vmask.sum(axis=0)

        isolated = ((rf - max_nb) > iso_db) & (n_valid_nb < 3)
        rho_confirmed = rho_f < rho_strict
        keep = cand & (isolated | rho_confirmed)

        idx = np.argwhere(keep)
        for (ri, gi) in idx:
            a = float(az[ri])
            slant = float(rng_m[gi])
            lat, lon, alt = beam_to_latlonalt(lat0, lon0, a, slant, elev)
            vel = _velocity_lookup(radar, dop, a, gi)
            cls, conf = classify(float(rf[ri, gi]), vel, float(rho_f[ri, gi]))
            dets.append({
                'station': Path(path).parent.name,
                'file': Path(path).name,
                'elev': elev, 'az': a, 'range_km': slant / 1000.0,
                'lat': lat, 'lon': lon, 'alt_m': alt,
                'reflectivity': float(rf[ri, gi]),
                'velocity': vel,
                'rhohv': float(rho_f[ri, gi]),
                'objectClass': cls, 'confidence': conf,
            })

    # strongest first; cap
    dets.sort(key=lambda d: d['confidence'], reverse=True)
    return dets[:max_targets]


# ----------------------------- CLI: single file -----------------------------

def main():
    ap = argparse.ArgumentParser(description='Signature-based fall detector (single file)')
    ap.add_argument('path')
    ap.add_argument('--rho-max', type=float, default=0.85)
    ap.add_argument('--iso-db', type=float, default=8.0)
    args = ap.parse_args()

    dets = detect_file(args.path, rho_max=args.rho_max, iso_db=args.iso_db)
    print(f"{len(dets)} detections in {Path(args.path).name}")
    print(f"{'elev':>5}{'az':>8}{'rng_km':>8}{'alt_m':>8}{'refl':>7}{'vel':>8}"
          f"{'rhohv':>7}  class")
    for d in dets:
        v = f"{d['velocity']:.1f}" if d['velocity'] is not None else "  -"
        print(f"{d['elev']:>5.2f}{d['az']:>8.1f}{d['range_km']:>8.1f}{d['alt_m']:>8.0f}"
              f"{d['reflectivity']:>7.1f}{v:>8}{d['rhohv']:>7.2f}  {d['objectClass']}"
              f" ({d['confidence']:.2f})  [{d['lat']:.4f},{d['lon']:.4f}]")


if __name__ == '__main__':
    main()
