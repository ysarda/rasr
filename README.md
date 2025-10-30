# RASR
Re-entry Analysis of Serendipitous Radar data

**Yash Sarda** <ysarda@utexas.edu>

Computational Astronautical Sciences and Technologies (CAST), The University of Texas at Austin

### Previous Contributors
Benjamin Miller <benjamin.g.miller@utexas.edu>
Carson Lansdowne <carson.l@utexas.edu>
Robby Keh <robbykeh@utexas.edu>

---

## Overview

RASR is an automated detection and warning system for atmospheric re-entry events using the NOAA NEXRAD Doppler radar network. The system leverages machine learning to identify re-entry signatures in real-time radar data, providing a proof-of-concept for detecting both meteorites and anthropogenic space objects entering Earth's atmosphere.

### Key Features
- Automated scraping of NOAA NEXRAD Level II radar data from 159 stations across the continental US
- PyTorch-based Faster R-CNN ResNet-50 FPN for object detection
- Multi-field analysis (velocity, reflectivity, spectrum width)
- Kinematic back-propagation for trajectory estimation
- Real-time detection capability with latitude/longitude/altitude output

### Motivation

As satellite launches into Low Earth Orbit increase, so does the frequency of re-entry events. Objects that don't completely incinerate during atmospheric entry pose risks to aircraft, spacecraft, and ground locations. Current meteorite detection relies on eyewitness reports, covering only ~0.3% of total re-entries. RASR automates this detection process using existing radar infrastructure.

## Architecture

RASR consists of two main components:

1. **RASR-Get**: Data scraping tool that autonomously downloads Level-II base data from 159 Weather Surveillance Radars (WSR-88D) across the continental United States
2. **RASR-Detect**: Analysis engine that unpacks radar data and identifies re-entry signatures using neural networks

### Detection Pipeline

1. Retrieve radar data from NOAA NEXRAD archive
2. Normalize velocity arrays
3. Pass through Faster R-CNN for initial detection
4. For multiple detections, calculate kinematic back-propagation
5. Output latitude, longitude, altitude, time, and state vector


## Requirements & Setup

### Dependencies
- Python (3.8)
- arm_pyart (1.11)
- beautifulsoup4 (4.9.3)
- detecto (1.2.0)
- geojson (2.5.0)
- matplotlib (3.2.3)
- netCDF4 (1.5.3)
- numpy (1.19.2)
- pymap3d (2.4.3)
- requests (2.24.0)
- torch (1.7.1)
- tqdm (4.54.1)

### Installation

From the main rasr directory:
```bash
cd envs
conda env create --file rasrenv.yml
conda activate rasr
pip install -e .
```

**Note:** Ensure that the arm_pyart library has installed correctly. It may need to be installed manually from their GitHub: https://arm-doe.github.io/pyart/userguide/INSTALL.html


## Proof of Concept Results

### Methodology

The proof of concept explored using machine learning for automated re-entry detection, transitioning from rigid empirical methods (OpenCV-based filtering) to adaptive neural network approaches.

#### Initial Approach: Computer Vision
Early attempts used Python OpenCV for detection:
- Filtered radial velocity based on minimum speed
- Calculated radial acceleration gradients as spatial derivatives
- Applied area, eccentricity, and spatial density filters
- Defined contour features for velocity and spectrum width

**Limitation:** This empirical method proved too rigid for general use, being over-fitted to specific test cases.

#### Neural Network Approach
Transitioned to a machine learning approach using:
- **Framework:** PyTorch with Detecto package interface
- **Architecture:** Faster R-CNN ResNet-50 FPN (pre-trained on COCO 2017)
- **Training Data:** Manually labeled ARES library of radar-captured meteorite falls
- **Detection Process:**
  1. Data unpacking and velocity array normalization
  2. Pass through R-CNN for object detection
  3. Altitude-specific processing with iterative pixel dilation (2×iteration filter)
  4. Coordinate conversion (Cartesian → latitude/longitude/altitude)
  5. ECI frame conversion for kinematic back-propagation

#### Kinematic Back-Propagation Model
State equation assuming Keplerian orbit decay with basic drag:

```
Σ F = m₀ẍ = (-Gm_e m₀/|x|³)|x| + C_D l^(1/2) ρ ẋ²

ẍ = (-Gm_e/|x|³)|x| + (C_D l/2m₀) ρ ẋ²

Assuming C_D ≈ 0.9, l/m₀ ≈ 10, thus k ≡ C_D l/2m₀ ≈ 5

ẍ = (-Gm_e/|x|³)|x| + k ρ ẋ²
```

### Test Results

#### Lake Michigan, WI Case Study
- **Performance:** ~30 seconds per iteration (non-optimized, single process, 8 CPUs)
- **Detection Rate:** Successfully detected all 3 case study events
- **False Positives:** 1 false positive detected

#### Model Performance Analysis

**Object Detection CNN (Velocity-only):**
- Precision: 2%
- Recall: 69%
- Issue: High propensity for false positives due to imbalanced dataset (~90% null data, ~10% actual detections)

**Null Classifier (with null data training):**
- Precision: 71%
- Recall: 99%
- Limitation: No object detection or localization capability

**Multi-Field Bagged Model (Reflectivity + Velocity + Spectrum Width + CC):**
- Precision: 12% (6× improvement over velocity-only)
- Key Finding: Reflectivity data significantly reduced bias/error

#### Continental-Scale Testing
When processing 24 hours of continental-scale radar data, no detections were made, which aligns with the average frequency of manual radar meteor detections (~0.3% of total re-entries).

### Key Findings

1. **Two-Pronged Approach Necessary:** A classifier to filter null data, followed by an object detector for localization
2. **Multi-Field Integration Critical:** Incorporating reflectivity, spectrum width, and correlation coefficient data significantly improves precision
3. **Data Diversity Limitation:** The model showed success in test cases but requires more diverse training data to handle weather and noise effects at continental scale
4. **Velocity Discrimination Potential:** Meteors (~10 km/s) vs. orbital debris (~1 km/s) velocity signatures can potentially distinguish re-entry types

### Future Architecture Proposal

The proof of concept identified a path forward using ensemble models:
- Multiple weak learners (CNNs) for different data fields (velocity, reflectivity, spectrum width)
- 3D ensemble model for classification
- Physics-constrained LSTM for temporal analysis across radar sweeps
- Ensemble model for final detection with confidence scores

**Note:** The original trained models are no longer available. The detection pipeline is being rebuilt with an ensemble ML approach.

## References

1. Fries, M. & Fries, J. (2010). Doppler Weather Radar as a Meteorite Recovery Tool. *Meteoritics & Planetary Sciences*, 45(9), 1476-1487. DOI: 10.1111/j.1945-5100.2010.01115.x

2. Helmus, J.J. & Collis, S.M. (2016). The Python ARM Radar Toolkit (Py-ART), a Library for Working with Weather Radar Data in the Python Programming Language. *Journal of Open Research Software*, 4(1), p.e25. DOI: 10.5334/jors.119

3. Ren, S., He, K., Girshick, R.B. & Sun, J. (2015). Faster R-CNN: Towards Real-Time Object Detection with Region Proposal Networks.

4. NASA ARES Meteorite Falls Database: https://ares.jsc.nasa.gov/meteorite-falls/

## Technical Report

For detailed information about the proof of concept methodology and results, see [RASRreport.pdf](RASRreport.pdf).
