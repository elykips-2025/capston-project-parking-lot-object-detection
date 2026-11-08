# ParkSight AI — Model Evaluation Report

## 1. Objective

Evaluate the ability of ParkSight AI to classify parking bays as
occupied, empty, or unknown using recorded CCTV footage.

The evaluation compares raw image classification with temporal
occupancy smoothing.

## 2. Evaluation Methodology

The evaluation used:

- One CCTV recording, approximately 28.83 seconds long.
- Video resolution: 1280 × 720 pixels.
- 27 manually mapped parking bays.
- Five evaluation timestamps: 0.000, 7.007, 14.014,
  21.021 and 28.028 seconds.
- 135 manually reviewed bay observations.
- Ground truth: 85 occupied and 50 empty observations.

The processing pipeline uses frame alignment, parking-bay
polygons, a MobileNetV3-Small classifier and temporal smoothing.

Raw classification uses conservative probability thresholds:
0.10 for empty and 0.90 for occupied. Intermediate predictions
are classified as unknown.

Temporal smoothing uses a five-observation rolling window
with a minimum of three supporting votes.

## 3. Raw Classification Results

| Metric | Result |
|---|---:|
| Total observations | 135 |
| Correct classifications | 102 |
| Incorrect classifications | 0 |
| Unknown classifications | 33 |
| Classification coverage | 75.56% |
| Selective accuracy | 100.00% |
| Overall correct classification rate | 75.56% |
| False vacancies | 0 |

### Raw confusion matrix

| Actual | Predicted empty | Predicted occupied | Unknown |
|---|---:|---:|---:|
| Empty | 35 | 0 | 15 |
| Occupied | 0 | 67 | 18 |

## 4. Temporal Classification Results

| Metric | Result |
|---|---:|
| Total observations | 135 |
| Correct classifications | 80 |
| Incorrect classifications | 0 |
| Unknown classifications | 55 |
| Classification coverage | 59.26% |
| Selective accuracy | 100.00% |
| Overall correct classification rate | 59.26% |
| False vacancies | 0 |

### Temporal confusion matrix

| Actual | Predicted empty | Predicted occupied | Unknown |
|---|---:|---:|---:|
| Empty | 28 | 0 | 22 |
| Occupied | 0 | 52 | 33 |

## 5. Temporal Warm-up Analysis

| Timestamp (s) | Raw classified | Temporal classified |
|---|---:|---:|
| 0.000 | 19/27 | 0/27 |
| 7.007 | 21/27 | 19/27 |
| 14.014 | 21/27 | 20/27 |
| 21.021 | 19/27 | 20/27 |
| 28.028 | 22/27 | 21/27 |

Excluding the initial timestamp:

- Raw classification coverage: 76.85%.
- Temporal classification coverage: 74.07%.
- Coverage difference: 2.78 percentage points.

The initial temporal warm-up accounts for much of the
difference between overall raw and temporal coverage.

## 6. Automated Testing

The backend test suite completed successfully:

- 15 tests passed.
- 17 subtests passed.
- No failures.

Tests cover occupancy probability thresholds, invalid inputs,
temporal voting, state isolation, conservative availability
decisions and departure confirmation.

## 7. Interpretation

All definitive classifications matched the manually reviewed
labels in this evaluation sample.

The system returned unknown when classification confidence
was insufficient.

No occupied parking bay was incorrectly reported as available
among the evaluated observations.

Temporal smoothing reduced classification coverage, particularly
during initial warm-up. Its contribution to prediction stability
and vehicle-transition detection was not established by this
evaluation.

## 8. Limitations

1. Evaluation used one short CCTV recording.
2. The five sampled frames represent repeated observations
   of the same 27 parking bays.
3. Ground-truth labels were manually reviewed but not
   independently audited.
4. Different lighting, weather, camera angles and car parks
   were not evaluated.
5. No independently labelled arrival/departure transitions
   were included.
6. Selective accuracy excludes unknown predictions.
7. The results do not establish production-grade reliability.

## 9. Conclusion

ParkSight AI demonstrated the ability to classify mapped
parking bays from recorded CCTV footage while explicitly
representing uncertain predictions.

The raw classifier achieved 75.56% coverage and 100% selective
accuracy on 135 labelled observations, with no observed
false-vacancy errors.

These findings support the feasibility of the Capstone
proof of concept, but further evaluation is required before
making claims about generalisation or deployment reliability.

## 10. Reproducibility

Supporting datasets:

- reports/evaluation/ground-truth-video.csv
- reports/evaluation/video-occupancy-results.csv

The evaluation uses the saved model predictions and
timestamp-matched ground-truth labels.
