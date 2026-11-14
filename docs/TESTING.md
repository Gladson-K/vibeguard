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

## V3 (hardware, power, signed OTA)
```bash
make test-v3
```
Starts the signed-OTA mock server and runs:
- power-budget model (`vg-sil-v3_power`) — target and monotonicity checks;
- OTA policy (`vg-sil-v3_ota`) — canonical parity, valid, tampered, wrong key,
  downgrade, below-minimum, size mismatch, invalid signature;
- production test (`vg-sil-v3_prodtest`) — PASS label and every failure reason;
- deep-sleep state machine (`vg-sil-v3_state`);
- OTA E2E — fetch `manifest.json` + `firmware.bin` from `ota-mock` and verify,
  then reject a tampered download.

The mock key and version are set in `docker/docker-compose.yml`; tests read the
same `VG_OTA_KEY_HEX`. Physical power/thermal/ESD checks are hardware-in-the-loop
(see `hardware/V3_DESIGN.md`).

## V4 (LoRa fleet, drift, diagnosis, staged rollout)
```bash
make test-v4
```
Builds the V4 SIL binaries and runs:
- codec tests: 32-byte CRC frame, 40-byte HMAC frame, corruption/tamper,
  C++/Python byte-for-byte parity;
- rollout: FNV-1a buckets, 10/50/100 cohorts, SIL parity;
- diagnosis: BPFO/BPFI/BSF/FTF geometry and rule classes, SIL parity;
- RUL and PSI/KS drift, SIL parity;
- gateway v2: signed LoRa ingest, CRC/key rejection, device registry, machine
  metadata, alert hysteresis + recovery, maintenance suppression, ack,
  staged rollout selection/advance/auto-rollback, drift/diagnosis/RUL endpoints,
  Prometheus metrics and WebSocket events.

`make test-all` now runs V1 + V2 + V3 + V4. Current totals: 22 + 14 + 35 + 45.

Observability smoke test (optional):
```bash
make obs    # Prometheus http://localhost:19090, Grafana http://localhost:13000
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
