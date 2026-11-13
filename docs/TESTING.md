# Testing VibeGuard in Docker

Everything runs without hardware.

## V1 (baseline)
```bash
make test-v1
```
Spins up gateway + Mosquitto + the test image, then runs:
- unit tests: features, detector, API (FastAPI TestClient);
- SIL parity: host-compiled `firmware/src/vg_features_v1.h` vs Python features;
- E2E scenarios: `v1_healthy`, `v1_bearing`, `v1_imbalance`, `v1_looseness` (python node)
  and `v1_bearing_sil` (compiled C++ node);
- MQTT ingestion smoke test.

Reports are written to `reports/*.json`.

## V2 (TinyML)
```bash
make test-v2
```
Builds the NAS autoencoder + int8 TinyML artifact, then runs feature/model/SIL/E2E
tests and the gateway model-score detector.

Optional heavy TensorFlow/TFLite comparison:
```bash
docker-compose -f docker/docker-compose.yml --profile ml run --rm train-ml
```

## Adding hardware or a machine
1. Add a sensor entry to `config/hardware.yaml` (fs, window, noise, transport).
2. Add a machine entry to `config/machines.yaml` (rpm, bearing frequencies).
3. Add a scenario to `harness/scenarios/` referencing them.
No test code changes are required.

## Running the gateway manually
```bash
make up          # dashboard at http://localhost:18000
make down
```

## Firmware compile gate
```bash
make build-firmware   # PlatformIO, downloads the ESP32-S3 toolchain on first run
```
