# ParkSight AI — Model Provenance and Evaluation

**Project:** Quantic MSSE Capstone — ParkSight AI  
**Evaluation source:** `model-evaluation.md` (project evaluation report)  
**Status:** Initial evaluation on one recorded CCTV video; not a production-grade generalisation study.

## 1. Model provenance and configuration

| Item | Recorded detail | Evidence status |
|---|---|---|
| Vehicle detection | Ultralytics YOLO11n | Model used in processing pipeline |
| Parking-bay classification | MobileNetV3-Small-based classifier | Architecture named in evaluation report |
| Original training dataset | Not established | **Unverified** |
| Checkpoint/weights origin and version | Not established | **Unverified** |
| Custom training or fine-tuning | Not established | **Unverified** |
| Training epochs, learning rate, split | Not documented | **Unverified** |
| Raw occupancy thresholds | Empty probability ≤ 0.10; occupied probability ≥ 0.90; otherwise unknown | Documented |
| Temporal smoothing | Five-observation rolling window; minimum three supporting votes | Documented |

**Important:** Integrating a pretrained model and running inference does not itself demonstrate custom model training. Do not claim fine-tuning until the model-loading/training code and checkpoint provenance are verified.

## 2. Evaluation dataset

| Characteristic | Value |
|---|---:|
| CCTV recordings | 1 |
| Recording duration | Approximately 28.83 seconds |
| Video resolution | 1280 × 720 |
| Manually mapped parking bays | 27 |
| Evaluated timestamps | 5 (0.000, 7.007, 14.014, 21.021, 28.028 seconds) |
| Human-reviewed bay observations | **135** (27 bays × 5 timestamps) |
| Ground-truth occupied | 85 |
| Ground-truth empty | 50 |

These are repeated observations of the same 27 bays, **not 135 independent parking scenarios**. Ground-truth labels were manually reviewed but not independently audited.

## 3. Evaluation summary

| Metric | Raw classifier | Temporal classifier |
|---|---:|---:|
| Total observations | 135 | 135 |
| Correct definitive predictions | 102 | 80 |
| Incorrect definitive predictions | 0 | 0 |
| Unknown / abstained | 33 | 55 |
| **Prediction coverage** | **75.56%** | **59.26%** |
| **Unknown-state rate** | **24.44%** | **40.74%** |
| **Selective accuracy** (definitive predictions only) | **100.00%** | **100.00%** |
| Correct out of all observations | 75.56% | 59.26% |
| Observed false vacancies | 0 | 0 |

### Raw classifier confusion matrix

| Ground truth | Predicted empty | Predicted occupied | Unknown |
|---|---:|---:|---:|
| Empty (50) | 35 | 0 | 15 |
| Occupied (85) | 0 | 67 | 18 |

### Temporal classifier confusion matrix

| Ground truth | Predicted empty | Predicted occupied | Unknown |
|---|---:|---:|---:|
| Empty (50) | 28 | 0 | 22 |
| Occupied (85) | 0 | 52 | 33 |

## 4. Precision, recall and F1-score

**Calculation convention:** Precision is calculated among definitive occupied/empty predictions. Unknown predictions count as missed detections of the actual class when computing recall. These are *abstention-aware* per-class metrics; they are not conventional binary-classification metrics computed after discarding unknowns.

| Metric | Raw classifier | Temporal classifier |
|---|---:|---:|
| Empty precision | 100.00% | 100.00% |
| Empty recall | 70.00% | 56.00% |
| Empty F1-score | 82.35% | 71.79% |
| Occupied precision | 100.00% | 100.00% |
| Occupied recall | 78.82% | 61.18% |
| Occupied F1-score | 88.16% | 75.91% |
| **Macro F1-score** | **85.26%** | **73.85%** |

**Formulae:** `precision = TP / (TP + FP)`; `recall = TP / (TP + FN + unknown actual-class cases)`; `F1 = 2 × precision × recall / (precision + recall)`. Macro F1 is the arithmetic mean of the occupied and empty F1 scores. Values are derived from the confusion matrices and rounded to two decimals.

## 5. Temporal warm-up

| Timestamp (seconds) | Raw definitive predictions | Temporal definitive predictions |
|---|---:|---:|
| 0.000 | 19 / 27 | 0 / 27 |
| 7.007 | 21 / 27 | 19 / 27 |
| 14.014 | 21 / 27 | 20 / 27 |
| 21.021 | 19 / 27 | 20 / 27 |
| 28.028 | 22 / 27 | 21 / 27 |

Excluding the first timestamp, raw coverage was **76.85%** and temporal coverage was **74.07%**. The initial warm-up explains much of the difference in overall coverage. This evaluation does **not** establish that smoothing improves stability or transition detection.

## 6. Related engineering evidence

- Full processing run: **29 sampled frames × 27 bays = 783 occupancy observations**.
- Observed processing-state distribution: **355 occupied, 185 empty, 243 unknown**.
- Regression parity: **783/783** state outputs matched reference processing, with zero reported probability difference.
- Automated backend checks: **15 tests passed; 17 subtests passed; no failures**, as recorded in the evaluation report.

**Do not confuse the datasets:** The 783 observations are pipeline outputs; the **135 manually reviewed observations** are the labelled subset used for accuracy-related metrics. Regression parity is not ground-truth accuracy.

## 7. Interpretation and limitations

All definitive predictions matched reviewed labels in this limited evaluation, but the classifier abstained on **24.44%** of raw observations and **40.74%** of temporally smoothed observations. No false vacancy was observed in the sample; this is **not** a guarantee of zero false vacancies in deployment.

Limitations include a single short recording, correlated observations of the same bays, manually reviewed but unaudited labels, and no testing across independent car parks, weather, lighting or camera angles. Arrival/departure transition accuracy was not independently evaluated.

## 8. Slide-ready takeaway

> On 135 manually reviewed parking-bay observations from one CCTV recording, the raw classifier achieved **75.56% coverage**, **100% selective accuracy** and **85.26% macro F1** using abstention-aware scoring. Temporal classification achieved **59.26% coverage**, **100% selective accuracy** and **73.85% macro F1**. These findings demonstrate feasibility on the test recording, not generalisation to new sites.

## 9. Reproducibility and outstanding evidence

**Evaluation inputs identified in the project report:**

- `reports/evaluation/ground-truth-video.csv`
- `reports/evaluation/video-occupancy-results.csv`
- `model-evaluation.md`

**Still to verify before final submission:** model checkpoint path and checksum, upstream training dataset and licence, whether any local fine-tuning occurred, and independent evaluation on additional recordings.
