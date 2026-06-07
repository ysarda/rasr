# Artemis II Splashdown: NEXRAD Radar Analysis

**Author:** Yash Sarda, Computational Astronautical Sciences and Technologies (CAST), UT Austin  
**Date:** June 2026  
**Radar Station:** KNKX (San Diego, CA) — 32.9190°N, 117.0418°W, 320m ASL  
**Data Source:** NOAA NEXRAD Level II via AWS S3 (`noaa-nexrad-level2`)

---

## 1. Summary

Analysis of KNKX NEXRAD radar data surrounding the Artemis II capsule "Integrity" splashdown reveals two discrepancies in public records:

1. **Date error:** The NASA ARES Meteorite Falls Database lists the event as **April 10, 2026 at 0007 UTC**. The radar data containing the capsule signature is from **April 11, 2026**. ARES appears to have used the local PDT date (April 10) with the UTC time (0007), producing an incorrect UTC date.

2. **Splashdown time discrepancy:** The widely reported splashdown time of **00:07:27 UTC** (5:07 PM PDT) cannot represent water contact. KNKX radar shows the capsule at **9+ km altitude** at that time, with a continuous descent tracked over **~29 minutes** until signal disappearance at approximately **00:33 UTC**. At a descent rate consistent with Orion under main parachutes (~5-7.5 m/s), actual water contact occurred closer to **00:30-00:33 UTC** (5:30 PM PDT).

---

## 2. Background

### 2.1 Event Overview

The Artemis II mission returned four astronauts from a lunar flyby aboard the Orion spacecraft "Integrity." The capsule splashed down in the Pacific Ocean southwest of San Diego, California, within range of the KNKX NEXRAD radar.

- **ARES Event Page:** https://ares.jsc.nasa.gov/meteorite-falls/events/artemis-ii-splashdown
- **ARES Cited Parameters:**
  - Date/Time: 4/10/2026 @ 0007 UTC
  - Coordinates: 32.4175°N, 117.707°W
  - Altitude: 9.071 km (velocity image)

### 2.2 Radar Geometry

The splashdown coordinates map to the following position relative to KNKX:

| Parameter | Value |
|-----------|-------|
| Distance from radar | 83.7 km |
| Azimuth from radar | 228° (southwest) |
| East offset | -62.5 km |
| North offset | -55.7 km |

This places the capsule well within KNKX's operational range (460 km max) and at a distance where multiple elevation angles intersect the descent corridor between 0-12 km altitude.

---

## 3. Data Analyzed

### 3.1 Radar Files

Ten KNKX Volume Coverage Pattern (VCP) scans were downloaded spanning the event window. Each scan contains 14 sweeps from 0.48° to 6.42° elevation across 7 radar fields.

| File | Scan Start (UTC) | Offset from Reported Splashdown |
|------|------------------|---------------------------------|
| KNKX20260410_232152_V06 | 23:21:52 | -46 min |
| KNKX20260410_233027_V06 | 23:30:27 | -37 min |
| KNKX20260410_233903_V06 | 23:39:03 | -28 min |
| KNKX20260410_234737_V06 | 23:47:37 | -20 min |
| KNKX20260410_235612_V06 | 23:56:12 | -11 min |
| **KNKX20260411_000447_V06** | **00:04:47** | **-3 min** |
| **KNKX20260411_001321_V06** | **00:13:21** | **+6 min** |
| **KNKX20260411_002156_V06** | **00:21:56** | **+14 min** |
| **KNKX20260411_003030_V06** | **00:30:30** | **+23 min** |
| KNKX20260411_003905_V06 | 00:39:05 | +32 min |

Each VCP scan takes approximately 8.5 minutes to complete all 14 elevation sweeps. Low-elevation sweeps (0.5°) execute first, with high-elevation sweeps (5.1°, 6.42°) completing last. This offset between scan start time and individual sweep observation time is critical for interpreting the data.

### 3.2 Fields Available

All files contain: velocity, spectrum_width, differential_reflectivity, cross_correlation_ratio, reflectivity, differential_phase, clutter_filter_power_removed.

### 3.3 Extraction Region

A 30-km box centered on E=-60 km, N=-53 km (radar-relative coordinates) was used to extract all returns above 1.5 km altitude, excluding ocean surface clutter.

---

## 4. Findings

### 4.1 Discrepancy #1: ARES Date Error

The ARES page lists the event date as **April 10, 2026 at 0007 UTC**. However:

- All radar files containing the capsule signature have filenames dated **April 11, 2026** (e.g., `KNKX20260411_000447_V06`).
- The reference time embedded in the radar data is `2026-04-11T00:04:47Z`.
- The widely reported splashdown occurred at **5:07 PM PDT on April 10**, which converts to **00:07 UTC on April 11**.

**Conclusion:** ARES recorded the local calendar date (April 10 PDT) but paired it with the UTC time (0007), producing an incorrect combined timestamp. The correct UTC date is **April 11, 2026**.

### 4.2 Discrepancy #2: Splashdown Time

The reported splashdown time of 00:07:27 UTC is inconsistent with the radar data. The capsule is observed at altitude well past this time.

#### Descent Timeline

| Sweep Time (UTC) | Offset | Elevation | Altitude | Peak Ref | Velocity | Notes |
|-------------------|--------|-----------|----------|----------|----------|-------|
| ~00:04:34 | -3 min | 6.42° | 10.5 km | 4.5 dBZ | +25.5 m/s | First detection |
| 00:08:14 | +1 min | 1.32° | 1.8-2.1 km | 14.5 dBZ | -13.0 m/s | Low-altitude component |
| 00:12:10 | +5 min | 3.12° | 4.5 km | 5.0 dBZ | -19.5 to -21.0 m/s | Coherent cluster |
| 00:12:29 | +5 min | 4.00° | 5.9 km | 4.5 dBZ | -17.5 to -18.5 m/s | Coherent cluster |
| 00:12:48 | +5 min | 5.10° | 6.5-7.4 km | **12.5 dBZ** | -20.0 to -24.5 m/s | Strong returns |
| **00:13:07** | **+6 min** | **6.42°** | **7.1-9.9 km** | **8.0 dBZ** | **±26-28 m/s** | **Opposing velocities** |
| 00:20:43 | +13 min | 3.12° | 4.0 km | -0.5 dBZ | -18.5 m/s | Descending |
| 00:21:03 | +14 min | 4.00° | 5.1-5.3 km | **20.0 dBZ** | -18.5 to -20.5 m/s | **Peak reflectivity** |
| 00:21:22 | +14 min | 5.10° | 6.1-6.6 km | 8.5 dBZ | -18.0 to -19.5 m/s | Extended return |
| 00:21:41 | +14 min | 6.42° | 7.2-7.9 km | 4.5 dBZ | -19.5 to -24.5 m/s | Still descending |
| 00:25:15 | +18 min | 1.32° | 1.5-1.7 km | 9.0 dBZ | -8.0 to -11.0 m/s | Near surface |
| 00:28:36 | +21 min | 1.80° | 2.1-2.4 km | 4.0 dBZ | ±8.5 to -18.0 m/s | **Opposing velocities** |
| 00:29:36 | +22 min | 4.00° | 4.3-4.5 km | 4.0 dBZ | -19.0 to -21.5 m/s | Weakening |
| 00:29:54 | +22 min | 5.10° | 5.4-7.1 km | 11.5 dBZ | -19.0 to -21.5 m/s | Last strong return |
| 00:33:47 | +26 min | 1.32° | 1.6-1.8 km | 1.0 dBZ | — | Signal gone |

#### Key Observations

**The object is at ~9 km altitude at the reported splashdown time.** ARES itself cites the velocity image at 9.071 km altitude at 0007 UTC, which is internally consistent with the radar data but contradicts a 00:07 water contact time.

**The descent rate matches Orion under parachutes.** The object descends from ~10.5 km to signal disappearance at ~1.5 km over approximately 29 minutes, yielding a mean descent rate of ~5.2 m/s. The Orion capsule under three main parachutes descends at approximately 7.5 m/s. Accounting for beam geometry and wind-driven lateral drift, these rates are consistent.

**The object drifts northeast during descent.** The centroid position shifts from E=-62, N=-56 to E=-49, N=-45 over the observation window — approximately 18 km NE over 25 minutes (~43 km/h). This is consistent with prevailing Pacific winds carrying the parachutes inland during descent.

**Peak reflectivity occurs at +14 minutes (20 dBZ).** This is the strongest radar return of the entire event, observed at 5.1 km altitude — 14 minutes after the reported splashdown. An object on the water surface would not produce a 20 dBZ return at 5 km altitude.

### 4.3 Opposing Velocity Signature

Grouped opposing radial velocities (red and blue Doppler returns in close spatial proximity) were detected in two separate scans:

1. **00:13:07 UTC at 6.42° elevation:** Velocities of -26 to -28 m/s and +26 to +28 m/s observed within the same cluster at 7-10 km altitude.

2. **00:28:36 UTC at 1.80° elevation:** Velocities of -18 m/s and +8.5 m/s at 2.1-2.4 km altitude.

Opposing velocities in a compact spatial cluster are a well-established radar signature of falling objects, including meteorite falls and re-entering debris. This signature arises from a descending object producing both approaching and receding radial velocity components relative to the radar beam. The presence of this signature at two different altitudes during the descent further supports identification as the capsule rather than aircraft or clutter.

This signature is **not consistent with aircraft**, which produce a single coherent velocity vector, or with sea clutter, which lacks the altitude and spatial coherence observed here.

### 4.4 Signal Disappearance

By the 00:30:30 scan, only 4 weak returns remain at 6.42° elevation. By 00:33:47 (the 1.32° sweep of the same scan), only 1.0 dBZ noise-level returns persist at 1.6-1.8 km. The 00:39:05 scan shows only scattered noise in the region.

**Estimated actual water contact: 00:30-00:33 UTC (5:30-5:33 PM PDT).**

---

## 5. Descent Profile

The descent profile (Figure 21) plots all radar returns above 1.5 km altitude in the splashdown region as a function of time. The top panel colors returns by reflectivity, the bottom by radial velocity.

A theoretical 7.5 m/s descent curve originating at 10.5 km altitude at t=-3 minutes fits the observed altitude envelope. The reported splashdown time (red dashed line) falls approximately 25 minutes before the actual signal disappearance.

The velocity panel shows the transition from mixed opposing velocities (re-entry signature) at high altitude to coherent negative velocities (approaching the radar) at lower altitude, consistent with wind-driven drift toward San Diego during the final descent phase.

---

## 6. Figures

| Figure | Description |
|--------|-------------|
| 01-04 | Vel/Ref at 3.1°-6.4° from 23:56 scan (pre-event baseline) |
| 05-08 | Vel/Ref at 3.1°-6.4° from 00:04 scan (capsule at ~9 km, opposing velocities in Fig 08) |
| 09-12 | Vel/Ref at 3.1°-6.4° from 00:13 scan (descending, peak 20 dBZ in Fig 10) |
| 13-16 | Vel/Ref at 3.1°-6.4° from 00:21 scan (continued descent, opposing vel in Fig 14) |
| 17-20 | Vel/Ref at 3.1°-6.4° from 00:30 scan (signal fading) |
| **21** | **Descent profile — altitude vs time colored by ref and velocity** |
| **22** | **Annotated timeline with labeled events** |

---

## 7. Conclusions

1. **The ARES date should be corrected** from April 10, 2026 to **April 11, 2026** (UTC). The event occurred at 0007 UTC on April 11, which corresponds to 5:07 PM PDT on April 10.

2. **The reported splashdown time of 00:07:27 UTC likely represents a mission milestone other than water contact** — possibly entry interface, communications acquisition, or drogue deployment. The radar data shows the capsule at ~9 km altitude at this time, consistent with ARES's own cited altitude of 9.071 km.

3. **Actual water contact occurred approximately 00:30-00:33 UTC** (5:30-5:33 PM PDT), based on radar signal disappearance and a descent rate consistent with Orion under main parachutes.

4. **The opposing velocity signature at two altitudes** confirms the radar target is a descending object, not aircraft or clutter, and is consistent with the established radar phenomenology of re-entering objects documented in meteorite fall literature.

---

## 8. Reproducibility

All analysis can be reproduced using the RASR toolkit:

```bash
# Download radar data
python scripts/collect_positive_data.py "Artemis II Splashdown"

# Generate figures
python scripts/artemis_figures.py

# Interactive 3D visualization
python scripts/visualize_sweeps_3d.py data/positive/KNKX/KNKX20260411_000447_V06 --field velocity
```

Raw NEXRAD Level II data is publicly available from `s3://noaa-nexrad-level2/2026/04/11/KNKX/`.

---

## References

1. ARES Meteorite Falls Database — Artemis II Splashdown. NASA Johnson Space Center. https://ares.jsc.nasa.gov/meteorite-falls/events/artemis-ii-splashdown

2. Fries, M. & Fries, J. (2010). Doppler Weather Radar as a Meteorite Recovery Tool. *Meteoritics & Planetary Sciences*, 45(9), 1476-1487.

3. Helmus, J.J. & Collis, S.M. (2016). The Python ARM Radar Toolkit (Py-ART). *Journal of Open Research Software*, 4(1), p.e25.
