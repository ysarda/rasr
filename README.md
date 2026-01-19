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


## Requirements & Setup

### Dependencies
- Python 3.8+
- arm_pyart - Weather radar data processing
- boto3 - AWS S3 access for NEXRAD data
- pyyaml - Configuration and event database management
- matplotlib - Visualization
- netCDF4 - Radar file format support
- numpy - Numerical processing
- pymap3d - Coordinate transformations
- scipy - Trajectory integration

### Installation

From the main rasr directory:
```bash
cd envs
conda env create --file rasrenv.yml
conda activate rasr
pip install -e .
```

**Note:** Ensure that the arm_pyart library has installed correctly. It may need to be installed manually from their GitHub: https://arm-doe.github.io/pyart/userguide/INSTALL.html


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
- ✅ Data collection infrastructure (AWS S3 integration)
- ✅ Confirmed falls database (15 events with metadata)
- ✅ Null data collection pipeline
- ✅ Radar data processing (PyART integration)
- 🔄 Anomaly detection models (in development)
- 🔄 Temporal analysis framework (planned)

**Next Steps**:
1. Build training dataset from confirmed falls
2. Implement autoencoder baseline for anomaly scoring
3. Add temporal analysis across radar sweeps
4. Validate on historical events
5. Deploy for real-time continental monitoring

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
