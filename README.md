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

### Training

#### `train_autoencoder.py` — Train the spatio-temporal autoencoder

Trains the anomaly detection model on null radar data.

```bash
python scripts/train_autoencoder.py [CONFIG]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `CONFIG` | str (positional, optional) | `configs/train_poc.json` | Path to JSON training config file |

The JSON config file supports the following parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data_dir` | str | `data/null` | Training data directory |
| `checkpoint_dir` | str | `checkpoints` | Model checkpoint directory |
| `batch_size` | int | `4` | Training batch size |
| `num_epochs` | int | `200` | Number of training epochs |
| `learning_rate` | float | `1e-4` | Learning rate |
| `val_split` | float | `0.15` | Validation split ratio |
| `device` | str | `cuda` | Device (`cuda` or `cpu`) |
| `mixed_precision` | bool | `true` | Use mixed precision training |
| `image_size` | int | `128` | Radar image size (height=width) |
| `spatial_latent_dim` | int | `512` | Spatial encoder latent dimension |
| `temporal_hidden_dim` | int | `256` | Temporal LSTM hidden dimension |
| `max_sweeps` | int | `6` | Maximum sweeps per sample |
| `cache_dir` | str | `data/cache` | Preprocessed data cache directory |
| `max_samples` | int | `null` | Limit number of samples (null = all) |
| `preload_workers` | int | `16` | Number of data loading workers |
| `fields` | list | `["reflectivity"]` | Radar fields to use |
| `signal_weight` | float | `0.99` | Signal loss weight |
| `resume` | str | `null` | Checkpoint path to resume from |

### Evaluation

#### `evaluate_autoencoder.py` — Evaluate model on positive/negative data

Produces ROC curves, precision-recall curves, and threshold analysis.

```bash
python scripts/evaluate_autoencoder.py [CONFIG] [OPTIONS]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `CONFIG` | str (positional, optional) | `configs/train_poc.json` | Training config (for model architecture) |
| `--positive_data_dir` | str | `data/positive` | Directory containing positive (fall) radar data |
| `--output_dir` | str | `evaluation_results` | Directory to save evaluation results |
| `--target_fpr` | float | `0.01` | Target false positive rate for threshold selection |
| `--max_samples` | int | `None` | Limit samples per dataset (for quick testing) |

#### `inspect_positives.py` — Analyze positive samples in detail

Visualizes the top anomalous sweeps from positive (confirmed fall) data.

```bash
python scripts/inspect_positives.py [CONFIG] [OPTIONS]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `CONFIG` | str (positional, optional) | `configs/train_poc.json` | Training config |
| `--positive_data_dir` | str | `data/positive` | Positive samples directory |
| `--output_dir` | str | `evaluation_results/inspect_positives` | Output directory |
| `--top_n` | int | `20` | Number of top anomalies to visualize |

#### `visualize_model.py` — Visualize model reconstructions

Shows original vs. reconstructed radar images and error maps.

```bash
python scripts/visualize_model.py [OPTIONS]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--model_path` | str | `checkpoints/best_model.pt` | Path to trained model checkpoint |
| `--data_dir` | str | `data/null` | Directory containing radar data |
| `--output_dir` | str | `checkpoints/visualizations` | Output directory for visualizations |
| `--num_samples` | int | `5` | Number of samples to visualize |
| `--device` | str | `cuda`/`cpu` (auto) | Device to use |
| `--image_size` | int | `128` | Image size for radar grid |

### Utilities

#### `save_run.py` — Archive a training run

Copies model checkpoints, config, and training artifacts into a timestamped run directory.

```bash
python scripts/save_run.py [NAME] [OPTIONS]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `NAME` | str (positional, optional) | auto-generated | Run name |
| `--config` | str | `configs/train_poc.json` | Training config used for this run |
| `--runs_dir` | str | `runs` | Base directory for saved runs |

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

#### `debug_dataloader.py` — Debug the data loader

Loads a batch from the dataset and saves a debug visualization. No arguments.

```bash
python scripts/debug_dataloader.py
```

#### `test_boto3_download.py` — Test S3 download connectivity

Downloads a single NEXRAD file to verify AWS S3 access. No arguments.

```bash
python scripts/test_boto3_download.py
```


## Anomaly Detection Approach

### The Challenge

Meteorite falls are **extremely rare events** in radar data:
- Only ~0.3% of re-entries are detected through any means
- Millions of radar scans per day across 159 stations
- ~1 in millions of scans contain meteorite signatures
- Class imbalance makes this a textbook anomaly detection problem

### Current Development Focus

RASR is being rebuilt from the ground up with a focus on **semi-supervised anomaly detection**:

#### Data Collection Strategy
1. **Positive Examples (Confirmed Falls)**:
   - 15+ confirmed meteorite fall events from NASA ARES database
   - Events include: Pebble AL, Hamburg MI, McDonough GA, Clanton Well AZ (first US Martian meteorite!)
   - Each event has precise UTC time windows, radar stations, and geographic coordinates
   - Stored in `data/positive/` for training

2. **Null Examples (Normal Radar Patterns)**:
   - Random samples from dates with no known events
   - Weather phenomena (rain, snow, ground clutter)
   - Biological signatures (birds, insects)
   - Atmospheric noise patterns
   - Stored in `data/null/` for training

#### Anomaly Detection Framework

**One-Class Learning**:
- Train models to learn "what normal looks like" from abundant null data
- Falls are so rare that contamination in null data (~0.0006%) doesn't affect learned distribution
- Confirmed falls serve as validation set to measure detection capability

**Advantages**:
- No need to verify every scan is truly null
- Leverages extreme class imbalance as a feature, not a bug
- Scales to continental-wide monitoring
- Can detect novel fall signatures not in training set

**Potential Approaches**:
- Autoencoders: Learn to reconstruct normal patterns, falls have high reconstruction error
- Isolation Forest: Anomalies are easier to isolate in feature space
- One-Class SVM: Learn decision boundary around normal data
- Temporal analysis: Leverage multi-sweep patterns unique to falling objects

#### Multi-Field Integration
Incorporating multiple radar products improves discrimination:
- **Velocity**: Primary signature of high-speed re-entry
- **Reflectivity**: Distinguishes solid objects from weather
- **Spectrum Width**: Measures turbulence and fragmentation
- **Correlation Coefficient**: Separates meteorological from non-meteorological targets

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
- Confirmed falls database (15 events with metadata)
- Null data collection pipeline
- Radar data processing (PyART integration)
- Spatio-temporal autoencoder model
- Training and evaluation pipeline
- Per-sweep anomaly scoring

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
