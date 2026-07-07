"""
Assemble the pruned manual-boxing set with detector-pre-drawn VOC XML boxes.

Selects from fall_sweeps/ (rendered by visualize_fall_sweeps.py):
  - scans nearest the documented detection time (radar_details.sweep_time when
    present, else the event window centre), up to --max_scans per event
  - the --n_elev lowest elevation beams per scan
  - the rho_hv image per (scan, elevation); reflectivity fallback for
    single-pol events

Copies the images to --out_dir/<date>_<event>/ and, for each, runs the
signature + coherence detector on the source radar file and writes a Pascal
VOC .xml next to the image containing the near-truth candidate tracks as
pre-drawn boxes (class "fall") for a human to correct — correcting a box is
much faster than drawing one. Oversized boxes (mega-clusters) are skipped.

A boxing manifest (subset of the fall_sweeps manifest, same pixel->geo
contract) is written to --out_dir/manifest.json for XML ingestion later.
"""

import argparse
import glob
import json
import math
import os
import re
import shutil
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

import sys
sys.path.append(str(Path(__file__).parent))
from signature_detector import haversine_km
from descent_coherence import detect_tracks

import warnings
warnings.filterwarnings('ignore')

FN_RE = re.compile(r"(\w{4})(\d{8})_(\d{6})")
PRIMARY_FIELD = 'cross_correlation_ratio'
FALLBACK_FIELD = 'reflectivity'


def hhmmss_to_sec(t):
    t = t.replace(':', '')
    return int(t[:2]) * 3600 + int(t[2:4]) * 60 + int(t[4:6])


def geo_to_pixel(lat, lon, radar_lat, radar_lon, ext, px):
    """Inverse of the manifest's pixel->geo contract (row 0 = north)."""
    n = (lat - radar_lat) * 111.32
    e = (lon - radar_lon) * 111.32 * math.cos(radar_lat * math.pi / 180.0)
    col = (e + ext) / (2 * ext) * px
    row = (ext - n) / (2 * ext) * px
    return col, row


def voc_xml(folder, filename, px, objects):
    parts = [f"<annotation>\n  <folder>{escape(folder)}</folder>\n"
             f"  <filename>{escape(filename)}</filename>\n"
             f"  <size><width>{px}</width><height>{px}</height><depth>3</depth></size>\n"
             f"  <segmented>0</segmented>\n"]
    for (name, xmin, ymin, xmax, ymax) in objects:
        parts.append(
            f"  <object>\n    <name>{name}</name>\n    <pose>Unspecified</pose>\n"
            f"    <truncated>0</truncated>\n    <difficult>0</difficult>\n"
            f"    <bndbox><xmin>{xmin}</xmin><ymin>{ymin}</ymin>"
            f"<xmax>{xmax}</xmax><ymax>{ymax}</ymax></bndbox>\n  </object>\n")
    parts.append("</annotation>\n")
    return ''.join(parts)


def _boxes_for_scan(args):
    """Run the detector on one radar file; return per-elevation pixel boxes of
    near-truth tracks. Returns (radar_file, {elev_round: [box, ...]}) with box =
    (xmin, ymin, xmax, ymax)."""
    radar_path, tlat, tlon, radar_lat, radar_lon, ext, px, near_km, max_frac = args
    try:
        tracks = detect_tracks(radar_path)
    except Exception:
        return os.path.basename(radar_path), {}
    out = defaultdict(list)
    pad = max(3, int(0.004 * px))
    for t in tracks:
        d = min(haversine_km(tlat, tlon, a, b) for a, b in t['members_latlon'])
        if d > near_km:
            continue
        by_el = defaultdict(list)
        for p in t['profile']:
            by_el[round(p['elev'], 1)].append(p)
        for el, pts in by_el.items():
            cols, rows = [], []
            for p in pts:
                c, r = geo_to_pixel(p['lat'], p['lon'], radar_lat, radar_lon, ext, px)
                cols.append(c)
                rows.append(r)
            xmin = max(0, int(min(cols)) - pad)
            xmax = min(px - 1, int(max(cols)) + pad)
            ymin = max(0, int(min(rows)) - pad)
            ymax = min(px - 1, int(max(rows)) + pad)
            if xmax <= xmin or ymax <= ymin:
                continue
            if (xmax - xmin) > max_frac * px or (ymax - ymin) > max_frac * px:
                continue        # mega-cluster: useless as a pre-drawn box
            out[el].append((xmin, ymin, xmax, ymax))
    return os.path.basename(radar_path), dict(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--events', default='falls_events.yaml')
    ap.add_argument('--sweeps_dir', default='fall_sweeps')
    ap.add_argument('--positive_dir', default='data/positive')
    ap.add_argument('--out_dir', default='boxing_set')
    ap.add_argument('--max_scans', type=int, default=6, help='scans per event')
    ap.add_argument('--n_elev', type=int, default=4, help='lowest beams per scan')
    ap.add_argument('--near_km', type=float, default=15.0,
                    help='pre-draw tracks within this distance of truth')
    ap.add_argument('--max_box_frac', type=float, default=0.35,
                    help='skip pre-drawn boxes larger than this fraction of the image')
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--only_event', default=None, help='process just one event (substring match)')
    args = ap.parse_args()

    manifest = json.load(open(Path(args.sweeps_dir) / 'manifest.json'))
    ev = yaml.safe_load(open(args.events))

    # index manifest by (event, radar file)
    by_event_file = defaultdict(lambda: defaultdict(list))
    for m in manifest:
        by_event_file[m['event']][m['file']].append(m)

    selected = []          # manifest entries to copy
    detector_jobs = {}     # radar file basename -> job args
    summary = {}
    for e in ev['events']:
        name = e['name']
        loc = e.get('location', {})
        if loc.get('latitude') is None or name not in by_event_file:
            continue
        if args.only_event and args.only_event.lower() not in name.lower():
            continue
        # only images from the event's CURRENT stations (manifest may retain
        # renders from stations that were later reassigned, e.g. Gateway KEAX)
        stations = set(e.get('radar_stations', []))
        for f in list(by_event_file[name]):
            if by_event_file[name][f][0]['station'] not in stations:
                del by_event_file[name][f]
        if not by_event_file[name]:
            continue
        # target time: documented sweep_time if present, else window centre
        tgt = None
        for rd in e.get('radar_details', []) or []:
            if isinstance(rd, dict) and rd.get('sweep_time'):
                tgt = hhmmss_to_sec(rd['sweep_time'])
                break
        if tgt is None:
            t0 = hhmmss_to_sec(e.get('time_start_utc', '00:00:00'))
            t1 = hhmmss_to_sec(e.get('time_end_utc', '23:59:59'))
            tgt = (t0 + t1) // 2

        files = sorted(by_event_file[name],
                       key=lambda f: abs(hhmmss_to_sec(FN_RE.search(f).group(3)) - tgt))
        files = files[:args.max_scans]

        n_img = 0
        for f in files:
            entries = by_event_file[name][f]
            elevs = sorted(set(m['elev'] for m in entries))[:args.n_elev]
            fields = set(m['field'] for m in entries)
            field = PRIMARY_FIELD if PRIMARY_FIELD in fields else FALLBACK_FIELD
            for m in entries:
                if m['elev'] in elevs and m['field'] == field:
                    selected.append(m)
                    n_img += 1
            st = m['station']
            radar_path = os.path.join(args.positive_dir, st, f)
            if os.path.exists(radar_path) and field == PRIMARY_FIELD:
                m0 = entries[0]
                detector_jobs[f] = (radar_path, loc['latitude'], loc['longitude'],
                                    m0['radar_lat'], m0['radar_lon'],
                                    m0['ext_km'], m0['px'],
                                    args.near_km, args.max_box_frac)
        summary[name] = n_img

    print(f"Selected {len(selected)} images across {len(summary)} events; "
          f"running detector on {len(detector_jobs)} scans for pre-drawn boxes...")

    boxes_by_file = {}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_boxes_for_scan, j) for j in detector_jobs.values()]
        for i, fut in enumerate(as_completed(futs), 1):
            fname, boxes = fut.result()
            boxes_by_file[fname] = boxes
            if i % 20 == 0 or i == len(detector_jobs):
                print(f"  {i}/{len(detector_jobs)} scans")

    # copy images + write xmls
    out = Path(args.out_dir)
    n_boxes = 0
    boxed_events = set()
    for m in selected:
        src = Path(args.sweeps_dir) / m['image']
        dst = out / m['image']
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(src, dst)
        boxes = boxes_by_file.get(m['file'], {}).get(m['elev'], [])
        if boxes:
            objs = [('fall', *b) for b in boxes]
            xml = voc_xml(dst.parent.name, dst.name, m['px'], objs)
            dst.with_suffix('.xml').write_text(xml)
            n_boxes += len(boxes)
            boxed_events.add(m['event'])

    # merge into any existing boxing manifest (replacing entries for the events
    # processed this run, so a re-run with --only_event refreshes them cleanly)
    man_path = out / 'manifest.json'
    old = json.load(open(man_path)) if man_path.exists() else []
    done_events = set(summary)
    merged = [m for m in old if m['event'] not in done_events] + selected
    with open(man_path, 'w') as f:
        json.dump(merged, f, indent=0)

    print(f"\n{args.out_dir}/: {len(selected)} images, {n_boxes} pre-drawn boxes "
          f"({len(boxed_events)}/{len(summary)} events have at least one)")
    print("\nPer-event image counts (* = no pre-drawn boxes -> draw or skip manually):")
    for name in sorted(summary):
        mark = '' if name in boxed_events else '  *'
        print(f"  {name:<28}{summary[name]:>4}{mark}")


if __name__ == '__main__':
    main()
