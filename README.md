# RASR
Re-entry Analysis of Serendipitous Radar data

**Yash Sarda** <ysarda9@gmail.com>

Computational Astronautical Sciences and Technologies (CAST), The University of Texas at Austin

---

## Overview

RASR is an automated detection and warning system for atmospheric re-entry events using the NOAA NEXRAD Doppler radar network. The system uses anomaly detection approaches to identify rare re-entry signatures in radar data, providing automated detection for both meteorites and anthropogenic space objects entering Earth's atmosphere.

### Key Features
- Direct AWS S3 access to NOAA NEXRAD Level II radar data from 159+ stations
- Curated dataset of confirmed meteorite falls from NASA ARES database
- Multi-field radar analysis (velocity, reflectivity, spectrum width)
- Anomaly detection framework for rare event identification
- Kinematic back-propagation for trajectory estimation

### Motivation

As satellite launches into Low Earth Orbit increase, so does the frequency of re-entry events. Objects that don't completely incinerate during atmospheric entry pose risks to aircraft, spacecraft, and ground locations. Current meteorite detection relies on eyewitness reports, covering only ~0.3% of total re-entries. RASR automates this detection process using existing radar infrastructure.

## Architecture

RASR consists of data collection and analysis components:

### Data Collection
- **Positive Examples**: Confirmed meteorite fall events from NASA ARES database (stored in `data/positive/`)
- **Null Examples**: General radar scans with no known events (stored in `data/null/`)
- **Direct S3 Access**: Uses boto3 to download NEXRAD Level II data from AWS `unidata-nexrad-level2` bucket
- **Event Database**: YAML-based catalog of confirmed falls with radar station metadata

### Analysis Pipeline (In Development)
1. Retrieve and process radar data from NOAA NEXRAD archive via AWS S3
2. Convert radar sweeps to normalized images (PyART)
3. Anomaly detection using semi-supervised learning
4. Kinematic back-propagation for trajectory estimation
5. Output detection confidence, location, and state vectors


## Installation

### Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Setup

```bash
# Clone the repo
git clone https://github.com/ysarda/rasr.git
cd rasr

# Create venv and install all dependencies
uv sync

# Activate the virtual environment
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate
```

To install with GPU support for PyTorch, see the [PyTorch install guide](https://pytorch.org/get-started/locally/) and configure the appropriate index in `pyproject.toml` if needed.

## Scripts

All scripts are in the `scripts/` directory. Run them from the project root with the virtual environment activated.

### Data Collection

#### `collect_null_data.py` — Download null (negative) radar data

Downloads random NEXRAD scans with no known events for training the anomaly detector.

```bash
python scripts/collect_null_data.py [NUM_WORKERS]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `NUM_WORKERS` | int (positional, optional) | `config.max_workers` | Number of parallel download workers |

Uses `config.yaml` for paths, date ranges, and site list.

#### `collect_positive_data.py` — Download confirmed fall radar data

Downloads NEXRAD data for confirmed meteorite fall events defined in `falls_events.yaml`.

```bash
python scripts/collect_positive_data.py [EVENT_NAME]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `EVENT_NAME` | str (positional, optional) | all events | Name of a specific fall event to download (must match a key in `falls_events.yaml`) |

#### `sample_null_data.py` — Stratified null-data sampler

Builds a varied "normal" training set by sampling NEXRAD scans uniformly across **date** (stratified by month for seasonal coverage), **station** (uniform-random over the full site list, covering coastal/mountain/inland types), and **time of day**. This is the preferred way to build `data/null` — single-day sets cause the model to flag any unseen day/scene as anomalous.

```bash
python scripts/sample_null_data.py [OPTIONS]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--num-samples` | int | `20000` | Target number of scans to download |
| `--start-date` | str | `2025-06-01` | Start of date range (YYYY-MM-DD) |
| `--end-date` | str | `2026-05-31` | End of date range (YYYY-MM-DD) |
| `--out-dir` | str | `data/null` | Output directory |
| `--workers` | int | `12` | Concurrent download workers |
| `--per-draw` | int | `1` | Scans per (station, day) draw |
| `--seed` | int | `None` | Random seed |

Known fall-event dates (from `falls_events.yaml`) are automatically excluded to avoid contaminating the null set.

#### `convert_radar_to_images.py` — Convert radar files to images

Converts raw NEXRAD Level II files into images for training.

```bash
python scripts/convert_radar_to_images.py [RAW_DIR] [BASE_DIR] [OUTPUT_DIR]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `RAW_DIR` | str (positional) | interactive prompt | Directory containing raw radar files |
| `BASE_DIR` | str (positional) | interactive prompt | Base comparison directory |
| `OUTPUT_DIR` | str (positional) | interactive prompt | Output directory for images |

If fewer than 3 arguments are provided, the script prompts for input interactively.

### Detection

The detector is a classical, **training-free** pipeline run on real pyART-decoded
NEXRAD moments: a per-gate signature filter, then a descent-coherence stage that
links gate candidates into 3D tracks. See [Detection Approach](#detection-approach).

#### `signature_detector.py` — per-gate signature filter

Stage 1 rejects weather by correlation coefficient (ρhv ≥ `rho-max` → discard);
stage 2 keeps spatially isolated point returns. Pairs split-cut sweeps so each
candidate carries ρhv (surveillance sweep) and velocity (Doppler sweep), converts
to lat/lon/altitude with 4/3-earth geometry, and classifies kinematically.

```bash
python scripts/signature_detector.py FILE [OPTIONS]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `FILE` | str (positional, required) | — | Path to a NEXRAD Level II file |
| `--rho-max` | float | `0.85` | ρhv weather-rejection threshold (gates ≥ this are discarded) |
| `--iso-db` | float | `8.0` | Reflectivity an isolated gate must exceed its neighbours by |

#### `descent_coherence.py` — link candidates into descent tracks

Clusters the filter's candidate gates (grid-hash, near-linear) and scores each
cluster for physical coherence: multiple elevation beams, altitude span,
elevation↔altitude monotonicity, compactness, and non-met ρhv. Returns ranked
tracks with a descent profile.

```bash
python scripts/descent_coherence.py FILE [OPTIONS]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `FILE` | str (positional, required) | — | Path to a NEXRAD Level II file |
| `--corridor-km` | float | `10.0` | Horizontal link radius for clustering candidates into a track |
| `--min-alt-m` | float | `300.0` | Surface floor; candidates below this are dropped (no altitude *seed*) |
| `--top` | int | `5` | Number of top tracks to print |

#### `eval_signature_detector.py` — evaluate against known events

Runs the detector over `data/positive` (events keyed by station+date from
`falls_events.yaml`) and a sample of `data/null`, then reports per-event recall
and the recall-vs-false-alarm tradeoff over a score-threshold sweep.

```bash
python scripts/eval_signature_detector.py [OPTIONS]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--events` | str | `falls_events.yaml` | Event truth file |
| `--positive_dir` | str | `data/positive` | Positive (event) data |
| `--null_dir` | str | `data/null` | Null data for false-alarm rate |
| `--dist_km` | float | `25.0` | Hit radius around the known event location |
| `--null_sample` | int | `120` | Number of null scans to score |
| `--corridor_km` | float | `10.0` | Coherence link radius |
| `--min_alt_m` | float | `300.0` | Surface floor |
| `--workers` | int | `10` | Parallel worker processes |

#### `download_events.py` — fetch event data

Downloads NEXRAD Level II files for the re-entry events (KBRO/KGSP/KMRX/KAMX)
into `data/positive/`. No arguments.

```bash
python scripts/download_events.py
```

#### `visualize_sweeps_3d.py` — 3D sweep visualization

Plots all sweeps of a single radar file in 3D Cartesian space (east, north, altitude), colored by a radar field, with a marker at the radar origin.

```bash
python scripts/visualize_sweeps_3d.py FILE [OPTIONS]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `FILE` | str (positional, required) | — | Path to a NEXRAD Level II radar file |
| `--field` | str | `reflectivity` | Radar field to color by |
| `--max-range-km` | float | `150` | Maximum range in km to plot |
| `--downsample` | int | `2` | Plot every Nth gate (reduces point count) |
| `--output` | str | `None` | Save as HTML to path instead of opening in browser |

### Utilities

#### `archive_results.py` — Archive detection results

Archives processed radar data and detection results. No arguments.

```bash
python scripts/archive_results.py
```

#### `check_radar_fields.py` — Inspect radar file fields

Prints available fields in radar files from `data/null`. No arguments.

```bash
python scripts/check_radar_fields.py
```

#### `test_boto3_download.py` — Test S3 download connectivity

Downloads a single NEXRAD file to verify AWS S3 access. No arguments.

```bash
python scripts/test_boto3_download.py
```


## Detection Approach

### The Challenge

Re-entry / fall signatures are **extremely rare and compact**:
- Millions of radar scans per day across 159 stations; a fall touches a handful of gates in 1–2 volumes
- The target is a small, hard, non-meteorological point return embedded in ordinary weather and clutter

An earlier **reconstruction-error autoencoder** was tried and removed: at the known
fall locations its reconstruction error was *lower* than at random weather echoes
(ROC AUC ≈ 0.33–0.52). An autoencoder reconstructs smooth, compact point targets
trivially and instead flags busy weather — anti-correlated with the goal. The
current approach is a physics-based signature detector instead of a learned one.

### Signature Filter (stage 1)

Per-gate, per-sweep, on real pyART-decoded moments (`signature_detector.py`):

- **ρhv (correlation coefficient) weather rejection** — the primary discriminant.
  Rain/snow/hail are clouds of similar hydrometeors (ρhv > 0.97); metal, parachute
  fabric, ablating rock and debris are irregular (ρhv ≈ 0.2–0.7). Gates with
  ρhv ≥ 0.85 are discarded, removing ~99% of weather.
- **Spatial isolation (feature, not a gate)** — a single intact body is a
  sub-resolution point source (reflectivity > 8 dBZ above neighbours), but real
  fall signatures are usually fragment clouds spanning many gates. Isolation is
  recorded per gate and passed downstream as classifier evidence rather than
  used as a veto.
- **Split-cut pairing & geometry** — ρhv lives in the surveillance sweep, velocity in
  the Doppler sweep; they are paired by elevation. Gates are converted to
  lat/lon/**altitude** with the 4/3-earth beam model, then classified kinematically
  (meteor / intact_aso / debris).

The filter recovers real signatures (e.g. the Artemis II capsule at 2.9 km from
splashdown, ρhv 0.38, −22 m/s at 7.6 km altitude) but is permissive on its own —
sea/ground clutter and biota are all low-ρhv too.

### Descent-Coherence Stage (stage 2)

`descent_coherence.py` links the filter's candidate gates into 3D tracks (grid-hash
clustering, near-linear) and scores each for physical coherence:

- **multi-beam presence** — a descending object is caught by several elevation beams
  across the ~5-minute volume; a clutter gate sits in one beam.
- **altitude span & elevation↔altitude monotonicity** — one body seen by several beams.
- **compactness** — a real object is a thin structure (few gates per beam, small
  per-beam extent); extended clutter blobs are penalised to ~0.
- **non-met ρhv** — lower ρhv scores higher.

There is **no altitude seed**: low-altitude meteorite falls are kept; the coherence
score itself rejects surface clutter. Output is a ranked, soft-thresholded score so
few-beam events still surface (at lower score).

**Known limitation:** within a single volume, **aircraft** produce nearly identical
compact, low-ρhv, multi-beam coherent tracks and are the dominant false-alarm
source. Separating them needs either a horizontal-speed gate (aircraft traverse far
between beams) or multi-scan temporal persistence, or operating in a
location/time-cued mode against externally predicted re-entries.

#### Multi-Field Integration
- **Correlation coefficient (ρhv)**: separates non-meteorological targets from weather (primary)
- **Velocity**: approach/recession speed; kinematic class and aircraft discrimination
- **Reflectivity**: RCS proxy / isolation test
- **Spectrum width**: fragmentation and tumbling

### Kinematic Validation

For confirmed detections, physics-based trajectory back-propagation validates results:

```
State equation with atmospheric drag:
ẍ = (-Gm_e/|x|³)|x| + k ρ ẋ²

Where:
- G: Gravitational constant
- m_e: Earth mass
- ρ: Atmospheric density (altitude-dependent)
- k ≈ 5 (drag coefficient × area/mass ratio)
```

This allows:
- Trajectory reconstruction to determine origin
- Strewn field prediction for meteorite recovery
- Discrimination between meteors (~10 km/s) and orbital debris (~1 km/s)

### Implementation Status

**Current State**:
- Data collection infrastructure (AWS S3 integration)
- Confirmed event database (meteorite falls + anthropogenic re-entries: Artemis II, Starship F5, Crew-7, ISS EP9)
- Stratified null-data sampler (seasonal × station coverage)
- Radar data processing (PyART integration), real AR2V moment decoding
- Signature filter: ρhv weather rejection + spatial isolation + 4/3-earth geometry
- Descent-coherence stage: grid-hash track linking + physical coherence scoring
- Event evaluation: per-event recall and recall-vs-false-alarm sweep against known locations

**Open problem:** single-scan aircraft rejection (horizontal-speed gate / multi-scan tracking / cued operation).

## Data Sources

1. **NASA ARES Meteorite Falls Database**: https://ares.jsc.nasa.gov/meteorite-falls/
   - Confirmed meteorite fall events with radar signatures
   - Event metadata, strewn field predictions, recovery reports

2. **NOAA NEXRAD Level II Data**: AWS S3 bucket `unidata-nexrad-level2`
   - 159 WSR-88D radar stations across US
   - Real-time and archived Level II base data
   - Public access via boto3

## References

1. Fries, M. & Fries, J. (2010). Doppler Weather Radar as a Meteorite Recovery Tool. *Meteoritics & Planetary Sciences*, 45(9), 1476-1487. DOI: 10.1111/j.1945-5100.2010.01115.x

2. Helmus, J.J. & Collis, S.M. (2016). The Python ARM Radar Toolkit (Py-ART), a Library for Working with Weather Radar Data in the Python Programming Language. *Journal of Open Research Software*, 4(1), p.e25. DOI: 10.5334/jors.119

3. Chandola, V., Banerjee, A., & Kumar, V. (2009). Anomaly Detection: A Survey. *ACM Computing Surveys*, 41(3), 1-58.
