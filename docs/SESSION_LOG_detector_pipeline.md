# RASR Detector Session Log — Autoencoder → Signature/Classifier Pipeline → Labeling Reset

_Session spanning ~2026-06-09 → 2026-06-23. Written for later analysis. Records the
arc, the experiments, the honest results (including negative ones), and the current
state of the RASR (Re-entry Analysis of Serendipitous Radar) detection effort._

---

## 0. TL;DR

- **Killed the spatio-temporal autoencoder.** Reconstruction error is *anti-correlated*
  with falls (ROC ≈ 0.33–0.52): an AE reconstructs compact/simple point targets easily
  and flags busy weather instead. Wrong objective for this problem.
- **Built a physics-based pipeline** instead: `ρhv + isolation` signature filter →
  cross-sweep clustering → supervised classifier. Best validated result:
  **ROC-AUC ≈ 0.90 on held-out events** (grouped CV) using cross-sweep clustering +
  per-gate physical features, after removing leaky absolute-geometry features.
- **CNN on patches failed (chance, ~0.50)** — not a bug, a data-efficiency problem:
  ~140–180 positive labels is far too few to learn features from scratch; the
  hand-crafted physical features are a prior that makes scarce labels usable.
- **Unsupervised anomaly detection works *on filtered candidates*** (IsolationForest
  ROC ≈ 0.85, PCA-AE ≈ 0.78) with **zero fall labels** — the filter is what makes the
  AE idea viable. Deployable label-free baseline.
- **The real bottleneck is label quality.** Distance-based labels (any track near the
  recovery site) are contaminated by coincidental clutter; the apparent gains partly
  came from geometry leakage. → Pivoted to **human bounding-box labeling**.
- **Built a manual-boxing image set** and **expanded the event database to 48 events**
  (was ~19). Awaiting user-supplied Pascal VOC XML boxes to build clean track-level
  labels and retrain.

---

## 1. Starting point

- Repo: `signature-cv-pipeline` branch. NEXRAD Level II via AWS S3, PyART processing.
- Prior state: a spatio-temporal autoencoder (reconstruction-error anomaly detector)
  trained on "null" data; ~48 confirmed fall events in `falls_events.yaml`.
- Data: `data/positive/` (event files), `data/null/` (stratified sample, 159 stations ×
  12 months, ~6k files).

## 2. Autoencoder investigation and removal

- Ran the trained AE on positive (fall) data. **Null and positive score distributions
  were nearly identical; ROC-AUC ≈ 0.52.**
- Cropped-evaluation (score a window at the *known* fall location vs a random real echo):
  **ROC ≈ 0.33–0.38 — below chance.** At the fall location, reconstruction error was
  *lower* than at random weather.
- **Root cause (mechanistic):** an AE reconstructs compact, smooth, low-texture point
  targets trivially (low error) and complex storm texture poorly (high error). So
  reconstruction error rewards the opposite of the target. Adding ρhv as a channel
  would not fix it — low ρhv is common in null (clutter/bio), so it is "normal" to the
  AE; the fall is rare only in the *joint* feature combination, which reconstruction
  error cannot capture but a classifier can.
- **Decision:** remove the autoencoder (modules, training/eval scripts, configs,
  checkpoints, cache). Commit `f008a07e`.

## 3. Signature filter (physics, per gate) — `signature_detector.py`

Ported from the RASR "Replit" project's method (which itself hardcoded its Artemis
result — see §9), but run on **real** PyART-decoded moments:

1. **ρhv weather rejection** (primary): discard gates with ρhv ≥ 0.85. Weather > 0.97;
   metal/parachute/debris ≈ 0.2–0.7. Removes ~99% of weather.
2. **Spatial isolation**: reflectivity must exceed all 4 neighbours by > 8 dBZ
   (point-source); relaxed when ρhv < 0.7 strongly confirms non-met.
3. **Split-cut pairing + 4/3-earth geometry**: ρhv from surveillance sweep, velocity
   from Doppler sweep; convert (az, slant range, elevation) → lat/lon/altitude.

**Validation on the real Artemis II KNKX file:** recovered the capsule at 2.9 km from
splashdown, ρhv 0.38, −22 m/s inbound, 7.6 km altitude. But the filter is permissive —
**~12k–30k candidate gates per scan** (sea/ground clutter and biota are also low-ρhv).

## 4. Descent-coherence stage — `descent_coherence.py`

Cross-sweep grid-hash clustering of candidate gates into tracks, scored on multi-beam
presence, altitude span, elevation↔altitude monotonicity, compactness (gates/beam,
per-beam extent), non-met ρhv. **~30k gates → ~60 tracks/scan (~4,600× reduction).**

**Key finding — the high-scoring null tracks are NOT aircraft** (a prior assumption).
Inspecting them: near-zero velocities, low altitude → **ground/sea clutter, biology,
far-range speckle, and clustering artifacts** (a high-beam return + a surface return at
the same range linked into a fake "descent"). This reframed the problem: the filter is a
**candidate generator**, and a classifier should make the final call.

## 5. Supervised classifiers

Feature extraction per candidate + grouped cross-validation (held-out **events**, never
sibling tracks — avoids leakage). Positives = tracks/regions within `dist_km` of the
known event location; negatives = null tracks.

### 5a. Tabular GBT on cross-sweep tracks — `extract_tracks.py` + `train_classifier.py`

| positive radius | positives | ROC-AUC | PR-AUC | baseline | PR lift |
|---|---|---|---|---|---|
| 25 km | 471 | 0.651 | 0.164 | 0.032 | 5× |
| 10 km | 205 | 0.709 | 0.157 | 0.014 | 11× |
| 5 km  | 139 | 0.789 | 0.145 | 0.010 | 14.5× |

Signal is real and sharpens as labels get cleaner (→ label noise confirmed as limiter).

### 5b. Per-sweep "simplification" — `region_detector.py` (UNDERPERFORMED)

Motivated by an ablation suggesting cross-sweep *features* add nothing. But per-sweep
clustering **fragments each object across beams**, degrading candidates:
GBT ROC 0.54–0.64; and dropping the geometry features collapsed it to **below chance
(0.34–0.42)** — i.e. the only "signal" was `range_km`/`alt` **geometry leakage**
(each event sits at a characteristic range from its radar; grouped CV correctly punishes it).

### 5c. Clean 2×2 ablation (on the cross-sweep tracks, mpd=5)

| feature set | ROC |
|---|---|
| all features | 0.789 |
| **drop absolute-altitude** | **0.904** |
| drop cross-sweep structure | 0.798 |
| **drop both → per-gate physical only** | **0.900** |

**Conclusions:** absolute altitude/range **leak** (drop them). Cross-sweep *structural
features* add ~nothing, **but cross-sweep *clustering* is essential** (it builds one rich
candidate per object; per-sweep fragmentation is what killed 5b). The 0.90 is driven by
genuine signature features: `n_gates`/size, `non_met` (ρhv), reflectivity, velocity
spread, inbound fraction, compactness — **no position leak**.

**→ Validated detector: physics filter → cross-sweep clustering → per-gate physical
features (drop absolute geometry) → GBT. ROC ≈ 0.90 on held-out events.**

### 5d. Beam-stack CNN — `extract_stacks.py` + `train_cnn.py` (CHANCE)

To test "let the model learn the features": cross-sweep candidate → (3×K, px, px) stack
of the lowest K beams (reflectivity/velocity/ρhv), CNN with rotation/flip augmentation.
**ROC ≈ 0.498–0.506 (chance)**, even with all 182 positives.

| approach | features | labels needed | result |
|---|---|---|---|
| GBT + physical features | hand-crafted (prior) | works at ~140 | **ROC 0.90** |
| beam-stack CNN | learned from patches | needs thousands | chance (0.50) |

**Interpretation:** with ~150 labels, a CNN cannot learn shape/texture from scratch; the
hand-crafted physical features encode radar-physics prior knowledge that compensates for
label scarcity. **Keep the GBT + features.** CNN becomes viable only with many more clean
labels. (Single-sweep patches were even worse — fragmentation again.)

### 5e. Unsupervised AD on filtered candidates (WORKS, label-free)

Trained on NULL candidates only, scored positives (mpd=5 physical features):

| method | ROC |
|---|---|
| original AE on **raw scenes** | ~0.50 |
| PCA autoencoder on **filtered candidates** | 0.779 |
| **IsolationForest on filtered candidates** | **0.847** |
| supervised GBT (uses labels) | 0.90 |

**The filter resurrects the AE idea.** Falls sit in a low-density region of the
non-meteorological candidate distribution. IsolationForest at **0.847 with zero fall
labels** is a deployable baseline that sidesteps the labeling bottleneck. Supervised wins
by only ~0.05 (the value of labels = sharpening the fall-vs-aircraft boundary).

## 6. The label-quality bottleneck (the pivot)

Everything above is capped at ~0.90 by **label noise**: "positive = any track within
N km of the recovery site" mislabels (a) coincidental clutter near the site, and (b)
clutter in files that don't even contain the object (the object is overhead ~1–2 volumes).
The apparent tabular gains leaned partly on geometry leakage. **Clean, track-level truth
is required** — and only a human (or a validated physics forward-model) can provide the
fall-vs-aircraft discrimination that synthetic data cannot fake.

- **Synthetic data assessment:** hand-templated positives = circular (teaches our own
  assumptions); GAN/VAE infeasible at ~150 examples; **copy-paste augmentation** (real
  fall signatures → varied real backgrounds) is the one legitimate technique, mainly to
  rescue the data-starved CNN. Physics forward-model = valid but high-effort. Always
  evaluate on **real held-out events**.

## 7. Manual-boxing image pipeline — `visualize_fall_sweeps.py`

Detector-free, human-in-the-loop labeling set:
- **Full-sweep** PPI rasters (radar-centered, ±250 km, 1600 px), **one image per field ×
  elevation**, black = no-data. Fields: reflectivity, velocity, spectrum width, ρhv, Zdr.
- **Dated, flattened folders**: `fall_sweeps/<YYYY-MM-DD>_<event>/<station>_<HHMMSS>Z__<field>__el<elev>.png`.
- **`manifest.json`** records per-image radar lat/lon, elevation, field, extent, px — the
  exact pixel→geo mapping for ingesting Pascal VOC XML boxes later.
- **Pruned** to detection-window / closest station (`prune_fall_sweeps.py`) to keep it
  light (~5.4k → then re-expanded with new events).
- Recommended tool: **makesense.ai** (browser-local, no install, exports VOC XML) or
  LabelImg standalone `.exe`.

**Planned ingestion (not yet built):** box pixels → radar gates → clean track-level
positive labels → re-extract features/patches → retrain from a trustworthy foundation.

## 8. Event database expansion — `add_events.py`

Reconciled `falls_events.yaml` against the full ARES database (49 listed). Added all
radar-detected missing events via nearest-NEXRAD lookup (station coords parsed from the
Replit `stations.ts`) + tight-window download + yaml append.

- **`falls_events.yaml`: ~19 → 48 events** (2003 Park Forest through 2026), incl. 5
  anthropogenic re-entry/debris cases (CZ-4C, Colorado/Crew-5 trunk, Yakima F9, Hanford,
  Gaojing).
- Dropped 4 with no boxable data (Muses Mills = no station; Coalmont/Addison = download
  gap; Caribbean Sea = out of NEXRAD range).
- **Boxing set: 48 event folders, ~10,956 images, ~1.6 GB.**
- Caveats: pre-2013 events (Park Forest 2003, etc.) are single-pol (no ρhv/Zdr); debris
  events show linear streaks, not compact falls.

## 9. Side investigation — the "Replit" RASR project

A parallel demo app claimed to have detected Artemis II. Verified from source: the app's
Artemis/Starship results are **hardcoded constants** (`artemis2.ts`, special-cased on the
scan key), served from a TS array — **not** computed live and **not** from the DB it
claimed. The only real parsing was an offline Python pipeline (`nexrad_retrieve.py`, AR2V
decode) whose Crew-7 run produced a **null** (non-converged) result. Its detection
*method* (ρhv + isolation + kinematics) is sound and is what we adopted; its live "REAL
DATA" claims are not backed by the code. Lesson reinforced: **only evaluate on real data,
never synthetic/hardcoded.**

## 10. Commits (branch `signature-cv-pipeline`)

- `f008a07e` — Replace autoencoder with signature + classifier detection pipeline.
- `b5844a62` — Expand to 48 confirmed events + manual-boxing image tooling.
- `0d88166c` — Remove Artemis report figures and devcontainer; move report PDF to docs/.

## 11. Key files

| file | role |
|---|---|
| `scripts/signature_detector.py` | ρhv + isolation filter, 4/3-earth geometry, kinematic class |
| `scripts/descent_coherence.py` | cross-sweep clustering + coherence scoring + track features |
| `scripts/extract_tracks.py` / `train_classifier.py` | tabular GBT pipeline (the 0.90 result) |
| `scripts/region_detector.py` / `extract_regions.py` | per-sweep pipeline (underperformed) |
| `scripts/extract_stacks.py` / `train_cnn.py` | beam-stack CNN (chance) |
| `scripts/eval_signature_detector.py` | per-event recall + false-alarm evaluation |
| `scripts/visualize_fall_sweeps.py` | full-sweep boxing image generator + manifest |
| `scripts/add_events.py` / `prune_fall_sweeps.py` | event ingestion / image pruning |
| `falls_events.yaml` | 48 confirmed events |

## 12. Open items / next steps

1. **Ingest human XML boxes** → clean track-level labels → re-extract → retrain
   (expected to beat 0.90). **This is the critical path.**
2. **Aircraft discrimination** (the remaining single-scan confuser): horizontal-speed
   gate (cross-beam displacement/time) or multi-scan temporal persistence, or
   location/time-cued operation.
3. **Stand up the IsolationForest baseline** (0.85, label-free) as a deployable detector
   now, in parallel with the labeling effort.
4. **Copy-paste augmentation** to revisit the CNN once more labels exist.
5. Optional gap-fills: Coalmont/Addison (wider download window), Muses Mills (assign
   station), Caribbean (add TJUA to station table).

## 13. Addendum (2026-07-05/06): isolation demoted, thresholds widened, blind events explained

**Labeling decision.** Exhaustive boxing of the ~11k `fall_sweeps` images is NOT the
plan anymore. Since the GBT only judges tracks the filter+clustering produce, boxes
only matter where the detector generates candidates → replace boxing with
**detector-assisted accept/reject** of near-truth tracks (extend
`visualize_event_detection.py`, record verdicts to YAML = clean track labels).
Manual boxing is reserved for events where the detector finds nothing.

**Isolation test measured and demoted.** Diagnostic over all events, candidate gates
within 10 km of truth (204,442 gates): 38.7% were dropped *solely* because the
isolation test failed (ρhv 0.7–0.85, not isolated); gates uniquely kept by isolation:
<0.1%. Six events lost 100% of their near-truth candidates to it. Real fall
signatures are extended fragment clouds, not point targets. → keep rule is now just
ρhv < rho_max; isolation is computed per gate (`isolated` flag) and aggregated into a
`frac_isolated` track feature for the classifier.

**Zero-candidate events explained** (second diagnostic, rejection-reason bucketing):
- `refl_min=5 dBZ` hid Hamburg MI (8,218 near-truth gates, ρhv→0.21, all <5 dBZ!),
  Patch Grove, Dishchiibikoh, Waite, Prescott, CZ-4C. Falls are weak echoes.
  → `refl_min` now **−10 dBZ**.
- `rng_max=200 km` excluded La Petite Belgique (KCXX at 216 km) → now **300 km**.
- **Gateway AR was mis-assigned KEAX (262 km)**; fixed to KSGF (~95 km), 11 files
  downloaded; detector now finds a 7-beam track **1.1 km** from truth.
- Vinales Cuba (301 km) stays out of reach; Park Forest 2003 is single-pol AND its
  legacy files decode with radar coords (0,0) in pyART — the `surv is None → continue`
  path makes all single-pol files yield zero candidates (open gap).

**Retrain result (same validated config: grouped CV, mpd=5, drop absolute-altitude):**
**ROC 0.908, PR-AUC 0.214 (prevalence 0.014, ~15× lift), 302 positives from 40 events**
— metrics held while positive coverage more than doubled (was ~139 positives from far
fewer events). `frac_isolated` ranks in the top-10 features (evidence, not veto —
vindicated).

**New dominant problem: biota mega-clusters.** The −10 dBZ floor admits nocturnal
biology; 10 km horizontal-only clustering merges the fall into 4k–17k-gate blobs whose
coherence score → 0 (Gateway, Muskogee: tracks 0.5–1.5 km from truth, score 0.0). The
GBT still discriminates, but candidate granularity is degraded. **Next fix: altitude-
aware or tighter clustering** to keep the descent column separate from the biota layer.

**Tooling fixes:** `eval_signature_detector.py` no longer swallows worker exceptions
(they were silently recorded as score-0.0 "clean" results — invalidated an entire eval
run) and now reports nearest-any-track distance separately from best near-truth score
(score-0 tracks near truth used to print as "no track"). `train_classifier.py` can now
load `tracks.csv` directly and has `--drop` for feature ablations. Note: the
coherence-score-alone threshold sweep is a weak instrument; judge changes by the
grouped-CV GBT metrics.

**Locked holdout (2026-07-06).** Grouped CV tests each model on held-out events, but
the *design process* has seen all 40 events (features, thresholds, and structure were
tuned while looking at their scores), so CV numbers are an optimistic upper bound.
→ `holdout_events.yaml`: 10 events (2 ASO / 3 compact / 5 dense-scene, ≥4 from 2025+),
seeded stratified draw over strata measured from data (median near-truth track size).
`train_classifier.py` excludes them by default (`--holdout`). Dev-only result (30
events, 229 positives): **ROC 0.913, PR-AUC 0.146** — consistent with the full-set
number. The holdout is to be scored only against a frozen pipeline, and every such
evaluation logged in the yaml. Null side: use fresh, never-extracted null scans.

## 14. Honest assessment

The detection *method* is sound and validated (physics filter + clustering + physical
features → ROC ~0.90; label-free IsolationForest → 0.85). Neither is deployable-grade yet
because **positive-label quality/quantity is the binding constraint** — ~140 clean
positives from a handful of events, labeled by recovery location rather than the true
radar track. The manual-boxing + 48-event expansion directly attacks that constraint. The
CNN/deep-learning path is premature until labels are ~10× more plentiful and clean.
