"""
Add the missing ARES events: append to falls_events.yaml + download radar.

For each event we pick the nearest NEXRAD station (coords from the Replit
stations table), download a tight window around the detection time, and append a
yaml entry. Render afterwards with: visualize_fall_sweeps.py --new_only
"""

import math
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append('.')
from rasr.get.get import get_s3_client, get_station_files, download_s3_file

BASE = "https://ares.jsc.nasa.gov/meteorite-falls/events/"

# name, date, HHMM(UTC detection), lat, lon, alt_m|None, kind, slug, note
EVENTS = [
    ("Cockburn Island ON", "2026-06-20", "0008", 45.939476, -83.324361, None, "fall", "cockburn-island-ontario", "18 sweeps, 4 NEXRAD"),
    ("Cape Cod Bay MA", "2026-05-30", "1806", 41.87754, -70.35239, None, "fall", "cape-cod-bay-ma", "iron, fell in Cape Cod Bay (water)"),
    ("Houston TX", "2026-03-21", "2140", 30.048492, -95.47391, None, "fall", "houston-tx", "~1 ton meteoroid, ~8 min radar; KHGX"),
    ("Windfall OH", "2026-03-17", "1256", 41.057158, -81.800047, None, "fall", "windfall-oh", "achondrites recovered"),
    ("CZ-4C Rocket Body MN", "2026-01-24", "0620", 46.62914, -93.23138, None, "debris", "cz-4c-rocket-body-re-entry-minnesota", "Chinese rocket body re-entry, linear track"),
    ("Gunsight Butte AZ", "2023-11-23", "0255", 33.991066, -110.896376, None, "fall", "gunsight-butte-az", "possible fall, no GLM, rough time"),
    ("Kingsport TN 02", "2023-08-02", "0613", 36.587573, -82.614954, 2400, "fall", "kingsport-tn-02", "single signature 2.4 km, ~36 g"),
    ("Hopewell NJ", "2023-05-08", "1623", 40.3069, -74.84, None, "fall", "hopewell-nj", "small, TDWR-heavy detection"),
    ("Colorado Debris", "2023-04-27", "0852", 39.053202, -103.479592, None, "debris", "colorado-debris-de-orbit", "SpaceX Crew-5 trunk re-entry SE of Limon CO"),
    ("Waite ME", "2023-04-08", "1557", 45.369249, -67.516169, 7440, "fall", "waite-me", "KCBW 7440->2376 m over 4m40s"),
    ("El Sauz TX", "2023-02-15", "2322", 26.592252, -98.629942, None, "fall", "el-sauz-tx", "~1000 lb meteoroid"),
    ("Muskogee OK", "2023-01-20", "0938", 35.668006, -95.358036, None, "fall", "muskogee-ok", "5 NEXRAD, slow fireball to low altitude"),
    ("Lake Ontario WJ1", "2022-11-19", "0827", 43.182036, -79.557401, 15000, "fall", "lake-ontario-meteoroid-2022-wj1", "KBUF 15 km->850 m, fell in Lake Ontario"),
    ("Junction City GA", "2022-09-26", "0405", 32.629034, -84.396568, 16027, "fall", "junction-city-ga", "KMXX 16027 m, 5m31s"),
    ("Coalmont CO", "2022-08-24", "0235", 40.546356, -106.586326, 10173, "fall", "coalmont-co", "KFTG 10173 m 1.8 deg, possible"),
    ("Great Salt Lake UT", "2022-08-13", "1432", 40.733638, -112.419765, 6360, "fall", "great-salt-lake-ut", "6360 m, fell in/near Great Salt Lake"),
    ("Cranfield MS", "2022-04-27", "1304", 31.553773, -91.181204, 11257, "fall", "cranfield-ms", "KDGX 11257 m, H3-5 chondrite"),
    ("Patch Grove WI", "2022-01-20", "1248", 42.939029, -90.972408, None, "fall", "patch-grove-wi", "KARX/KGRB"),
    ("Yakima WA Debris", "2021-03-26", "0354", 46.83516, -120.031275, 8000, "debris", "yakima-wa-debris-de-orbit", "SpaceX F9 upper stage re-entry"),
    ("Prescott AZ", "2020-02-16", "1418", 34.717562, -112.747969, 16400, "fall", "prescott-az", "KFSX 16400 m, probable"),
    ("St Louis MO", "2019-11-12", "0256", 38.769045, -91.310246, 1729, "fall", "st-louis-missouri", "KLSX 1729 m, low altitude"),
    ("Caribbean Sea PR", "2019-06-22", "2124", 14.998267, -66.336777, 10600, "fall", "caribbean-sea-near-puerto-rico", "TJUA at ~348 km, fell in sea (deep)"),
    ("White Springs FL", "2019-04-04", "0405", 30.40967, -82.568493, 4029, "fall", "white-springs-florida", "KVAX/KJAX 4029 m, probable"),
    ("Vinales Cuba", "2019-02-01", "1818", 22.613415, -83.7129, 10600, "fall", "vinales-cuba", "KBYX at ~300 km, Cuba"),
    ("Hanford CA Debris", "2018-10-11", "0815", 36.324251, -119.619102, None, "debris", "hanford-ca-satellite-de-orbit", "satellite re-entry, ~200 km debris path"),
    ("Glendale AZ", "2018-07-27", "0327", 33.683881, -112.222128, 3710, "fall", "glendale-arizona", "KIWA 3710 m"),
    ("Dishchiibikoh AZ", "2016-06-02", "1057", 33.855281, -110.654072, 9740, "fall", "dishchiibikoh-arizona", "KFSX 9740 m, LL7 chondrite"),
    ("Mount Blanco TX", "2016-02-18", "0346", 33.754207, -101.248789, 7265, "fall", "mount-blanco-texas", "7265 m, L5 chondrite"),
    ("Osceola FL", "2016-01-24", "1527", 30.463389, -82.485716, 4380, "fall", "osceola-florida", "4380 m, L6, 11 sweeps"),
    ("Creston CA", "2015-10-24", "0549", 35.572766, -120.473317, 16460, "fall", "creston-california", "16460 m, L6, ~1.7x Park Forest mass"),
    ("Addison AL", "2012-10-30", "2236", 34.33625, -87.189535, 16190, "fall", "addison-alabama", "16190 m, extensive fragmentation"),
    ("Gaojing De-Orbit", "2024-12-22", "0408", 33.820552, -90.310355, None, "debris", "gaojing-1-02-de-orbit", "satellite re-entry, LA->MO linear track"),
]

WINDOW_MIN = 12      # +/- minutes around detection time to download
MAX_RANGE_KM = 420   # skip download if nearest station is farther


def parse_stations():
    txt = open('rasr-project/artifacts/api-server/src/lib/stations.ts').read()
    st = {}
    for m in re.finditer(r'id:\s*"(\w+)".*?lat:\s*([-\d.]+),\s*lon:\s*([-\d.]+)', txt):
        st[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    return st


def hav(a, b, c, d):
    R = 6371.0
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = math.radians(c - a), math.radians(d - b)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def in_window(fn, lo, hi):
    m = re.search(r'_(\d{6})', fn)
    if not m:
        return False
    h = m.group(1)
    if lo <= hi:
        return lo <= h <= hi
    return h >= lo or h <= hi          # midnight wrap


def yaml_entry(name, date, hhmm, lat, lon, alt, kind, slug, note, station, dist):
    hh, mm = hhmm[:2], hhmm[2:]
    t = int(hh) * 60 + int(mm)
    ws = f"{((t-20)//60)%24:02d}:{(t-20)%60:02d}:00"
    we = f"{((t+20)//60)%24:02d}:{(t+20)%60:02d}:00"
    alt_line = f"\n        altitude_m: {alt}" if alt else ""
    return (
        f'\n  - name: "{name}"'
        f'\n    date: "{date}"'
        f'\n    time_start_utc: "{ws}"'
        f'\n    time_end_utc: "{we}"'
        f'\n    location:'
        f'\n      latitude: {lat}'
        f'\n      longitude: {lon}'
        f'\n    radar_stations:'
        f'\n      - {station}  # nearest NEXRAD, {dist} km'
        f'\n    radar_details:'
        f'\n      - station: {station}'
        f'\n        sweep_time: "{hh}:{mm}:00"{alt_line}'
        f'\n    notes: "{note}. Kind: {kind}."'
        f'\n    source_url: "{BASE}{slug}"\n'
    )


def main():
    stations = parse_stations()
    s3 = get_s3_client()
    entries = []
    download_jobs = []

    for (name, date, hhmm, lat, lon, alt, kind, slug, note) in EVENTS:
        near = min(stations.items(), key=lambda kv: hav(lat, lon, kv[1][0], kv[1][1]))
        st_id, (slat, slon) = near
        dist = round(hav(lat, lon, slat, slon))
        entries.append(yaml_entry(name, date, hhmm, lat, lon, alt, kind, slug, note, st_id, dist))
        if dist > MAX_RANGE_KM:
            print(f"  {name:<22} {st_id} {dist} km  -> OUT OF RANGE, yaml only")
            continue
        y, mo, d = date.split('-')
        t = int(hhmm[:2]) * 60 + int(hhmm[2:])
        lo = f"{((t-WINDOW_MIN)//60)%24:02d}{(t-WINDOW_MIN)%60:02d}00"
        hi = f"{((t+WINDOW_MIN)//60)%24:02d}{(t+WINDOW_MIN)%60:02d}00"
        keys = get_station_files(s3, st_id, y, mo, d)
        sel = [k for k in keys if in_window(k.split('/')[-1], lo, hi)
               and (k.endswith('.gz') or k.endswith('_V06'))]
        print(f"  {name:<22} {st_id} {dist} km  {len(sel)} files")
        for k in sel:
            fn = k.split('/')[-1]
            download_jobs.append((k, f"data/positive/{st_id}/{fn}"))
        os.makedirs(f"data/positive/{st_id}", exist_ok=True)

    # threaded download
    def dl(k, lp):
        if os.path.exists(lp):
            return True
        return download_s3_file(get_s3_client(), k, lp, max_retries=3)
    ok = 0
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = [ex.submit(dl, k, lp) for k, lp in download_jobs]
        for f in as_completed(futs):
            ok += 1 if f.result() else 0
    print(f"\nDownloaded {ok}/{len(download_jobs)} files")

    # append yaml entries before the trailing "# Notes:" block
    txt = open('falls_events.yaml').read()
    marker = "\n# Notes:"
    assert marker in txt
    txt = txt.replace(marker, ''.join(entries) + marker, 1)
    open('falls_events.yaml', 'w').write(txt)
    print(f"Appended {len(entries)} events to falls_events.yaml")


if __name__ == '__main__':
    main()
