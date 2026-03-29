# RASR Anomaly Detection Models

Multi-field Spatio-Temporal Autoencoder for meteorite fall detection in NEXRAD radar data.

## Architecture Overview

The system uses a semi-supervised anomaly detection approach designed for extremely rare events (meteorite falls ~0.0006% of radar scans).

### Components

1. **Spatial Encoder**: Multi-branch 2D-CNN
   - Separate branches for velocity, reflectivity, spectrum width
   - Late fusion in latent space
   - Output: 512-dimensional spatial features per sweep

2. **Temporal Encoder**: Bidirectional LSTM
   - Captures meteorite descent through atmosphere
   - Processes sequences of 8-12 sweeps
   - Output: Temporal latent representation

3. **Temporal Decoder**: LSTM decoder
   - Reconstructs temporal sequence

4. **Spatial Decoder**: Multi-branch 2D-CNN decoder
   - Separate decoder per field
   - Output: Reconstructed multi-field sweeps

5. **Anomaly Scoring**: Reconstruction error
   - MSE between original and reconstructed data
   - Higher error = anomaly (potential meteorite fall)

## Usage

### 1. Prepare Data

Collect radar data using data collection scripts:
```bash
# Collect null (negative) examples
python scripts/collect_null_data.py

# Collect positive examples (confirmed falls)
python scripts/collect_positive_data.py
```

Data structure:
```
data/
  ├── null/          # Normal radar patterns (21k+ files)
  │   ├── KGWX/
  │   ├── KDTX/
  │   └── ...
  └── positive/      # Confirmed falls (232 files)
      ├── KGWX/
      ├── KDTX/
      └── ...
```

### 2. Train the Model

Train Phase 1 (unsupervised on null data):
```bash
python scripts/train_autoencoder.py \
    --data_dir data/null \
    --checkpoint_dir checkpoints/phase1 \
    --batch_size 4 \
    --num_epochs 50 \
    --learning_rate 1e-4
```

**Training Parameters:**
- `--data_dir`: Path to null data directory
- `--batch_size`: Batch size (default: 4, reduce if GPU memory limited)
- `--num_epochs`: Number of training epochs (default: 50)
- `--learning_rate`: Learning rate (default: 1e-4)
- `--val_split`: Validation split ratio (default: 0.15)
- `--device`: Device to use (cuda/cpu, auto-detected)

**Output:**
- Checkpoints saved to `checkpoints/phase1/`
- Best model: `checkpoints/phase1/best_model.pt`
- Training curves: `checkpoints/phase1/visualizations/training_curves.png`
- Reconstruction visualizations: `checkpoints/phase1/visualizations/`

### 3. Evaluate the Model

Test on null and positive data to determine optimal threshold:
```bash
python scripts/evaluate_autoencoder.py \
    --model_path checkpoints/phase1/best_model.pt \
    --null_data_dir data/null \
    --positive_data_dir data/positive \
    --output_dir evaluation_results \
    --target_fpr 0.01
```

**Evaluation Parameters:**
- `--model_path`: Path to trained model checkpoint
- `--null_data_dir`: Path to null data for computing FPR
- `--positive_data_dir`: Path to positive data for computing TPR
- `--target_fpr`: Target false positive rate (default: 0.01 = 1%)

**Output:**
- Performance metrics: `evaluation_results/evaluation_results.json`
- ROC curve: `evaluation_results/roc_curve.png`
- Precision-Recall curve: `evaluation_results/precision_recall_curve.png`
- Score distributions: `evaluation_results/score_distributions.png`

**Expected Results:**
- Null data scores: Low (mean ~0.01-0.05)
- Positive data scores: High (mean ~0.1-0.5)
- ROC AUC: >0.95 (excellent separation)
- At 1% FPR, expect >90% TPR (detection rate)

## Model Details

### Input Format
- **Shape**: (batch_size, max_sweeps, num_fields, height, width)
  - `max_sweeps`: 12 (padded if fewer sweeps available)
  - `num_fields`: 3 (velocity, reflectivity, spectrum_width)
  - `height, width`: 512×512 pixels (~0.8 km/pixel resolution)
- **Mask**: Boolean tensor (batch_size, max_sweeps) indicating valid sweeps
- **Data range**: [-1, 1] (normalized)

### Architecture Parameters
- **Spatial latent dimension**: 512
- **Temporal hidden dimension**: 256 (bidirectional, so 512 total)
- **Total parameters**: ~15M
- **Memory footprint**: ~2GB GPU memory for batch_size=4

### Training Strategy

**Phase 1 - Unsupervised Pretraining:**
- Train on 18k null examples (85% of null data)
- Objective: Learn to reconstruct "normal" radar patterns
- Loss: MSE reconstruction error
- Duration: ~2-3 days on V100 GPU

**Phase 2 - Threshold Tuning (Evaluation):**
- Validate on 3k null + 232 positive examples
- Find threshold that achieves target FPR (e.g., 1%)
- Measure TPR (detection rate) at this threshold

**Phase 3 - Semi-Supervised Fine-Tuning (Optional):**
- Add contrastive loss to separate fall/null distributions
- Use positive examples for guidance
- Further improve separation

## Dataset Information

### Null Data
- **Size**: ~21,034 files from 94 radar stations
- **Coverage**: Random dates with no known meteorite falls
- **Contents**: Weather patterns, ground clutter, biological signatures, noise
- **Purpose**: Learn "normal" patterns for anomaly detection

### Positive Data
- **Size**: 232 files from 15 confirmed meteorite fall events
- **Events**:
  - Pebble AL (2025-11-06)
  - Hamburg MI (2018-01-17)
  - McDonough GA (2025-06-26)
  - Clanton Well AZ (2024-04-17) - First US Martian meteorite!
  - And 11 more...
- **Coverage**: ±30-90 minute windows around confirmed events
- **Purpose**: Validation and anomaly score threshold tuning

### Class Imbalance
- **Ratio**: ~1:90 (positive:null)
- **Real-world ratio**: ~1:millions (meteorite falls are extremely rare)
- **Approach**: Anomaly detection leverages this imbalance as a feature

## Performance Metrics

### Primary Metrics
1. **Detection Rate (TPR)**: Percentage of confirmed falls detected
   - Target: >90% at 1% FPR
   - Measured on 232 positive examples

2. **False Alarm Rate (FPR)**: Percentage of null scans flagged as anomalies
   - Target: <1% (1 false positive per 100 scans)
   - Measured on 21k null examples

3. **ROC AUC**: Area under ROC curve
   - Target: >0.95 (excellent separation)

### Secondary Metrics
- Precision: True positives / (true positives + false positives)
- Recall (=TPR): True positives / (true positives + false negatives)
- F1 Score: Harmonic mean of precision and recall

## Computational Requirements

### Training
- **GPU**: NVIDIA V100 or A100 recommended
- **GPU Memory**: ~8GB for batch_size=4
- **Training Time**: ~2-3 days for 50 epochs
- **CPU**: 8+ cores recommended for data loading

### Inference
- **Speed**: ~100ms per radar file on V100
- **Memory**: ~2GB GPU memory
- **Real-time capable**: Yes, can process continental-scale data

## Troubleshooting

### Out of Memory (OOM)
- Reduce `--batch_size` to 2 or 1
- Reduce `image_size` in dataset (e.g., 256×256 instead of 512×512)
- Use gradient checkpointing (add to model)

### Poor Separation (Null and Positive Scores Overlap)
- Train longer (increase `--num_epochs`)
- Check data quality (visualize reconstructions)
- Try different learning rate
- Add data augmentation
- Implement Phase 3 fine-tuning

### Slow Training
- Increase `--num_workers` for data loading
- Use mixed precision training (add to training script)
- Profile to find bottlenecks

## Next Steps

1. **Temporal Analysis Enhancement**:
   - Add attention mechanisms to LSTM
   - Implement physics-constrained motion model
   - Track detections across sequential scans

2. **Multi-Scale Detection**:
   - Process multiple image resolutions
   - Combine global (full sweep) and local (bounding box) features

3. **Real-Time Deployment**:
   - Integrate with AWS S3 event triggers
   - Stream processing for continental monitoring
   - Alert system for confirmed detections

4. **Physics Validation**:
   - Kinematic back-propagation for trajectory estimation
   - Velocity discrimination (meteors vs debris)
   - Strewn field prediction for recovery

## References

1. Fries, M. & Fries, J. (2010). Doppler Weather Radar as a Meteorite Recovery Tool. *Meteoritics & Planetary Sciences*, 45(9), 1476-1487.

2. Chandola, V., Banerjee, A., & Kumar, V. (2009). Anomaly Detection: A Survey. *ACM Computing Surveys*, 41(3), 1-58.

3. NASA ARES Meteorite Falls Database: https://ares.jsc.nasa.gov/meteorite-falls/
