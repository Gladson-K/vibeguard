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
| ml (optional) | `docker/ml.Dockerfile` | TensorFlow/TFLite heavy profile |

Compose: `docker/docker-compose.yml` with profiles `v1`, `v2`, `ml`, `firmware`, `ci`.
Gateway dashboard is published on `${VG_GATEWAY_PORT:-18000}`.

Make targets: `make test-v1`, `make test-v2`, `make test-all`, `make build-firmware`,
`make up`, `make down`.

## 3. Version roadmap

### V1 — baseline + Docker E2E (done)
Firmware (ESP32-S3 + MPU-6050, 1 kHz), FastAPI gateway, Welford z-score detector,
dashboard, python node + SIL node, scenario E2E. Acceptance: recall ≥ 90%,
0 false alarms, latency < 1 s, baseline ≤ 60 windows.

### V2 — TinyML + better sensing
ADXL345/ADXL355 SPI profiles, upgraded spectral features (15 log bands, centroid,
envelope), dataset tooling, **NAS-selected dense autoencoder**, int8 quantization +
header-only C runtime (`firmware/src/vg_core`), SIL v2, gateway model-score detector.
Acceptance: recall ≥ 90%, ≤ 1 false alarm/day, int8 AUC within 2% of float,
inference < 20 ms, arena < 60 KB.

### V3 — custom hardware, power, OTA (planned)
See `plans/PLAN_V3.md`. Docker additions: OTA mock server, power-model test,
production-test jig emulation, HIL profile.

### V4 — fleet, LoRa, continual learning, productization (planned)
See `plans/PLAN_V4.md`. Docker additions: LoRa/fleet simulator, gateway v2 + Grafana,
drift/staged-rollout tests, mTLS/security tests, soak/load tests.

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
