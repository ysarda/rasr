"""
Prune the fall_sweeps/ set down to only the files worth boxing, keeping it light.

Rules:
  - Events with a known detection time: keep files within +/- pad_min of that
    window; delete the rest (padding).
  - Null events (e.g. ISS EP9): delete entirely.
  - Multi-station events with no known time: keep only the radar closest to the
    event location (one view is enough to box); delete the others.
  - Single-station events with no known time: keep all.
Updates manifest.json to drop pruned images. Use --dry-run to preview.
"""

import argparse
import json
import math
import os
import re
import shutil
import yaml
from pathlib import Path

OUT = 'fall_sweeps'

# known detection windows (UTC minutes); falls back to radar_details times
EXTRA_WINDOWS = {
    'Artemis II Splashdown': ('00:04:00', '00:08:00'),
    'Crew-7 Trunk': ('00:00:00', '00:13:00'),
    'Starship F5 Booster': ('12:26:00', '12:33:00'),
}
NULL_EVENTS = {'ISS EP9 Pallet'}


def mins(t):
    p = [int(x) for x in t.split(':')]
    return p[0] * 60 + p[1] + (p[2] / 60 if len(p) > 2 else 0)


def fmins(h):
    return int(h[:2]) * 60 + int(h[2:4]) + int(h[4:]) / 60


def haversine(a, b, c, d):
    R = 6371.0
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = math.radians(c - a), math.radians(d - b)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def detection_window(e):
    if e['name'] in EXTRA_WINDOWS:
        s, t = EXTRA_WINDOWS[e['name']]
        return mins(s), mins(t)
    times = []
    for d in (e.get('radar_details') or []):
        for k, v in d.items():
            if isinstance(v, str) and re.match(r'^\d{2}:\d{2}', v):
                times.append(mins(v))
    return (min(times), max(times)) if times else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pad_min', type=float, default=10.0)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    ev = yaml.safe_load(open('falls_events.yaml'))
    manifest = json.load(open(f'{OUT}/manifest.json'))
    # station -> (lat,lon) from manifest
    st_coord = {m['station']: (m['radar_lat'], m['radar_lon']) for m in manifest}

    to_delete = []   # subdir paths
    for e in ev['events']:
        name = e['name']
        safe = name.replace(' ', '_').replace('/', '-')
        edir = Path(OUT) / safe
        if not edir.is_dir():
            continue
        subs = sorted(s.name for s in edir.iterdir() if s.is_dir())

        if name in NULL_EVENTS:
            to_delete += [edir / s for s in subs]
            continue

        win = detection_window(e)
        if win is not None:
            for s in subs:
                m = re.search(r'_(\d{6})Z', s)
                ft = fmins(m.group(1)) if m else None
                keep = ft is not None and any(win[0] - args.pad_min <= ft + o <= win[1] + args.pad_min
                                              for o in (0, 1440, -1440))
                if not keep:
                    to_delete.append(edir / s)
            continue

        # no time: if multi-station, keep only the closest radar
        stations = sorted(set(s.split('_')[0] for s in subs))
        if len(stations) > 1:
            loc = e['location']
            best = min(stations, key=lambda st: haversine(loc['latitude'], loc['longitude'],
                                                          *st_coord.get(st, (0, 0))))
            for s in subs:
                if s.split('_')[0] != best:
                    to_delete.append(edir / s)

    del_set = {str(p).replace('\\', '/') for p in to_delete}
    n_img = sum(len(list(p.glob('*.png'))) for p in to_delete if p.exists())
    print(f"Pruning {len(to_delete)} subdirs (~{n_img} images){' [DRY RUN]' if args.dry_run else ''}")
    by_event = {}
    for p in to_delete:
        by_event[p.parent.name] = by_event.get(p.parent.name, 0) + 1
    for ev_name, n in sorted(by_event.items()):
        print(f"  {ev_name}: -{n} subdirs")

    if args.dry_run:
        return
    for p in to_delete:
        if p.exists():
            shutil.rmtree(p)
    # drop now-empty event dirs
    for d in Path(OUT).iterdir():
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    # rewrite manifest
    new_manifest = [m for m in manifest
                    if not any(m['image'].startswith(d.replace(OUT + '/', '') + '/') for d in del_set)]
    json.dump(new_manifest, open(f'{OUT}/manifest.json', 'w'), indent=0)
    remaining = len(list(Path(OUT).glob('*/*/*.png')))
    print(f"\nDone. Remaining: {remaining} images, manifest {len(new_manifest)} entries")


if __name__ == '__main__':
    main()
