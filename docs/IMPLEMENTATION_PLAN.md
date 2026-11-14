# VibeGuard — Implementation Plan (V1 → V4)

Master plan for the VibeGuard edge vibration monitor. Canonical version specs live in
`plans/PLAN_V2.md`, `plans/PLAN_V3.md`, `plans/PLAN_V4.md`; this document adds the
generic Docker test strategy and tracks delivery.

## 1. Architecture

```
Device Sources (pluggable)
  real ESP32 (HTTP/MQTT) | python-node | SIL binary | dataset replay
            |
            v  feature frames (flat JSON + optional extras)
   Mosquitto (optional) <-> Gateway (FastAPI + SQLite + detector + dashboard)
            ^
            | REST assertions
   Test Runner (pytest + harness scenarios) -> JUnit/JSON reports
```

Generic abstractions (add hardware without touching tests):
- **Hardware profiles** `config/hardware.yaml` (sensor ODR/range/noise/transport).
- **Machine profiles** `config/machines.yaml` (RPM, bearing defect frequencies).
- **Scenarios** `harness/scenarios/*.yaml` (baseline, fault injection, expectations).
- **Sources** `harness/sources/*` (python_node, sil, replay).
- **Metrics** `harness/metrics.py` (recall, false alarms, detection delay, latency).

## 2. Docker environment

| Image | Dockerfile | Purpose |
|---|---|---|
| gateway | `docker/gateway.Dockerfile` | FastAPI runtime |
| test | `docker/test.Dockerfile` | pytest + harness + g++ SIL build |
| firmware | `docker/firmware.Dockerfile` | PlatformIO compile gate (`pio run`) |
| ota-mock | `docker/ota_mock.Dockerfile` | signed-OTA fixture server (V3) |
| obs (optional) | `prom/prometheus`, `grafana/grafana` | fleet metrics + dashboards (V4) |
| ml (optional) | `docker/ml.Dockerfile` | TensorFlow/TFLite heavy profile |

Compose: `docker/docker-compose.yml` with profiles `v1`, `v2`, `v3`, `v4`, `ml`,
`firmware`, `ci`, `obs`. Gateway dashboard is published on
`${VG_GATEWAY_PORT:-18000}` and the OTA mock on `${VG_OTA_PORT:-18080}`.

Make targets: `make test-v1` … `make test-v4`, `make test-all`, `make obs`,
`make build-firmware`, `make up`, `make down`.

## 3. Version roadmap

### V1 — baseline + Docker E2E (done)
Firmware (ESP32-S3 + MPU-6050, 1 kHz), FastAPI gateway, Welford z-score detector,
dashboard, python node + SIL node, scenario E2E. Acceptance: recall ≥ 90%,
0 false alarms, latency < 1 s, baseline ≤ 60 windows.

### V2 — TinyML + better sensing (done)
ADXL345/ADXL355 SPI profiles, upgraded spectral features (15 log bands, centroid,
envelope), dataset tooling, **NAS-selected dense autoencoder**, int8 quantization +
header-only C runtime (`firmware/src/vg_core`), SIL v2, gateway model-score detector.
Acceptance: recall ≥ 90%, ≤ 1 false alarm/day, int8 AUC within 2% of float,
inference < 20 ms, arena < 60 KB.

NAS pipeline (`tools/`):
1. `dataset.py` builds labelled feature windows from machine/sensor profiles.
2. `nas.py` searches {latent, hidden, activation} configs, ranks by anomaly AUC
   (tie-break fewer params).
3. `train_autoencoder.py` trains the winner, calibrates a 99.5th-percentile
   threshold, quantizes to int8 (`tinyml.py`) and emits `model_data.h`.
4. `sil/v2_main.cpp` runs the int8 model in the SIL node; `sil/bench_main.cpp`
   measures device-side latency.

### V3 — custom hardware, power, OTA (done)
Design package: `hardware/V3_DESIGN.md`, `hardware/v3/bom.csv`,
`hardware/v3/design_rules.md`, `hardware/v3/enclosure.scad`. Firmware:
`firmware/src/main_v3.cpp` plus `firmware/src/v3/` (deep sleep, fast Wi-Fi,
SoftAP provisioning, signed OTA + rollback, production test); portable policy in
`firmware/src/vg_core/v3/`.

Signed OTA uses HMAC-SHA256 over a canonical manifest
(`vg-ota-v1\nversion\nmin_version\nsize\nsha256\n`) implemented in
`vg_core/v3/ota_verify.cpp` and mirrored by `tools/ota_sign.py`. The firmware
rejects bad signatures, hash/size mismatches, downgrades and too-old versions,
and only confirms a new image after the sensor self-test passes.

Docker additions: `ota-mock` service (`tools/ota_server.py`) plus host SIL nodes
`v3_power`, `v3_ota`, `v3_prodtest`, `v3_state`. `make test-v3` covers the power
budget, OTA policy and canonical parity, production-test labels, state-machine
transitions, and an end-to-end fetch-and-verify against the mock server.

Acceptance: default 45 s duty cycle ≈0.47 mA average (≈175 days on 2000 mAh,
target <15 mA / ≥30 days), OTA accepts only signed newer images and rolls back
on self-test failure, production jig reports a PASS/FAIL label, and no Docker
test regressions in V1/V2.

### V4 — fleet, LoRa, continual learning, productization (implemented)
See `plans/PLAN_V4.md`. Portable core in `firmware/src/vg_core/v4/`:
32-byte compact frame + CRC16 and 40-byte HMAC-signed frame, deterministic
staged rollout (FNV-1a bucket, 10/50/100), PSI + two-sample KS drift, bearing
frequencies plus rule-based diagnosis, and linear-trend RUL. Host SIL nodes
`v4_codec`, `v4_rollout`, `v4_diag`, `v4_rul`, `v4_drift` mirror the Python
modules in `gateway/`.

Gateway v2: device registry with per-device keys and machine metadata, signed
LoRa ingest with CRC/HMAC checks, maintenance suppression, warning/critical/
recovery alerts with hysteresis, Telegram/email hooks, REST + SSE/WebSocket,
Prometheus metrics, Grafana assets, drift/diagnosis/RUL endpoints and staged
model rollout with alarm-rate auto-rollback.

Firmware: `firmware/src/main_v4.cpp`, `firmware/src/v4/` (SX1262 driver, LoRa +
ESP-NOW fallback, NVS key/sequence security, on-device drift shadow), PlatformIO
env `esp32s3_v4`. Hardware package: `hardware/V4_DESIGN.md`, `hardware/v4/bom.csv`.
Security/ops/productization: `docs/V4_SECURITY.md`, `docs/INSTALL_V4.md`,
`docs/OPERATIONS_V4.md`, `docs/PRODUCTIZATION.md`.

Verification: `make test-v4` covers codec rotation/tamper, rollout cohorts,
diagnosis rules, RUL, drift, signed ingest, alert lifecycle, maintenance,
rollout advance/rollback, metrics and WebSocket. `make test-all` includes V1–V4.
The PlatformIO compile gate remains hardware-side.

## 4. Acceptance matrix

| Metric | V1 | V2 | V3 | V4 |
|---|---|---|---|---|
| Recall (seeded) | ≥90% | ≥90% | ≥90% | ≥90% |
| False alarms | 0 (bench) | ≤1/day | ≤1/day | <1/10 machine-days |
| Latency | <1 s | <1 s | <1 s | <1 s |
| Power | <120 mA | — | <15 mA | <15 mA |
| Model | z-score | int8 AE | AE + OTA | multi-state + staged |
| Packet delivery | — | — | — | >98% |

## 5. Out of scope for Docker
Real sensor noise, EMC, PPK2 power measurement and physical fault seeding are
hardware-in-the-loop tasks; container tests validate logic and plumbing only.
