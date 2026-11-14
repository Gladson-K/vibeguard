# VibeGuard

Edge vibration anomaly monitor for small workshops, pump houses and farms.
See `PROBLEM_STATEMENT.md` for goals and success metrics.

## Docker quick start (no hardware needed)
```bash
make test-v1     # V1 end-to-end suite: gateway + mosquitto + python & SIL nodes
make test-v2     # V2 suite: NAS TinyML autoencoder + int8 model + E2E
make test-v3     # V3 suite: power budget, signed OTA + rollback, prodtest
make test-v4     # V4 suite: LoRa codec, drift, diagnosis, RUL, fleet gateway
make up          # start gateway + broker, dashboard on http://localhost:18000
make obs         # optional Prometheus + Grafana
make down
```
Reports land in `reports/`. See `docs/TESTING.md`.

## Local quick start
```bash
cd gateway
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q
uvicorn app:app --port 8000
python simulator.py --fault-after 120    # in another terminal
```

## With hardware
1. V1/V2 wiring: `hardware/WIRING_AND_BOM.md`.
2. V3 board: `hardware/V3_DESIGN.md` + `hardware/v3/` (BOM, design rules, enclosure).
3. V4 LoRa fleet node: `hardware/V4_DESIGN.md` + `hardware/v4/bom.csv`; edit
   `firmware/src/v4/v4_config.h` (band, pins, key) and `firmware/src/config.h`.
4. `cd firmware && pio run -e esp32s3_v3 -t upload` (V3) or
   `pio run -e esp32s3_v4 -t upload` (V4).
5. Production test image: `pio run -e esp32s3_v3_prodtest -t upload`.
6. Site install: `docs/INSTALL_V4.md`; operations: `docs/OPERATIONS_V4.md`.

## Layout
- `firmware/` PlatformIO ESP32-S3 code; `vg_core/` portable DSP + int8 model +
  V3 OTA/power/prodtest/state and V4 codec/rollout/drift/diagnosis/RUL
- `gateway/` FastAPI, SQLite, detectors, dashboard, simulator, tests
- `harness/` generic test harness: sources, scenarios, profiles, metrics
- `config/` hardware + machine profiles
- `sil/` software-in-the-loop firmware nodes (host-compiled, incl. V3)
- `docker/` images, compose, mosquitto config, OTA mock, Prometheus/Grafana
- `tools/` dataset recording, NAS training, TinyML export (V2), OTA signing (V3)
- `hardware/` BOM, wiring, V3 design package + enclosure
- `docs/` implementation plan, testing, V4 security/install/operations/productization
- `plans/` V2, V3, V4 specs
