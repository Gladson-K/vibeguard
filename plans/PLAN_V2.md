# VibeGuard V2: TinyML on-device learning and better sensing (4-6 weeks)

**Goal:** replace hand-tuned z-scores with a quantized int8 autoencoder running on the ESP32-S3, and upgrade the sensor so real bearing faults are visible.

## Skills you build
Data collection discipline, spectral feature engineering, model quantization (int8 PTQ), TFLite Micro, SPI sensors, honest evaluation.

## Deliverables
1. Better sensor: ADXL355 or ADXL345 (SPI, 3.2 kHz+ ODR). Driver in `firmware/src/adxl.cpp`, DMA/timer-driven sampling at 3.2 kHz.
2. Feature upgrade: log-spaced band energies (8-16 bands), spectral centroid, envelope spectrum of high-passed signal (bearing demodulation).
3. Dataset tooling: `tools/record.py` saves labelled raw windows (healthy, imbalance, looseness, bearing-like, belt) to `data/<machine>/<label>/*.npy`. Also try public data (CWRU bearing set, Paderborn) for pretraining.
4. Model: small dense autoencoder (e.g. 24 -> 12 -> 4 -> 12 -> 24), trained on healthy only; reconstruction error as anomaly score.
5. Quantization pipeline: Keras -> TFLite int8 with representative dataset -> C array -> TFLite Micro on device. Compare float vs int8 reconstruction error and AUC; accept if AUC drop < 2%.
6. Runtime: model inference < 20 ms, arena < 60 KB. Threshold calibrated from healthy-set 99.5th percentile, stored in NVS flash.
7. Evaluation notebook: ROC/PR curves, detection delay, false alarms/day on a 24 h healthy run.

## Milestones
| Week | Output |
|---|---|
| 1 | SPI sensor driver, 3.2 kHz stable sampling, jitter measured with logic analyser |
| 2 | Recorder + bench rig (fan/drill/small motor with seeded faults), 500+ windows per class |
| 3 | Feature upgrade + offline model in Python beating V1 baseline |
| 4 | Int8 quantization + TFLM integration |
| 5 | On-device inference + threshold in NVS, gateway shows model score |
| 6 | 24 h soak test + write-up |

## Exit criteria
Recall >= 90% on seeded faults, <= 1 false alarm/day, inference < 20 ms, int8 AUC within 2% of float.

## Stretch
On-device baseline adaptation (small running mean of the latent code), compare with isolation forest on gateway.
