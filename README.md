# VibeGuard

Edge vibration anomaly monitor for small workshops, pump houses and farms.
See `PROBLEM_STATEMENT.md` for goals and success metrics.

## Docker quick start (no hardware needed)
```bash
make test-v1     # V1 end-to-end suite: gateway + mosquitto + python & SIL nodes
make test-v2     # V2 suite: NAS TinyML autoencoder + int8 model + E2E
make up          # start gateway + broker, dashboard on http://localhost:18000
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
1. Wire per `hardware/WIRING_AND_BOM.md`.
2. Edit `firmware/src/config.h` (WiFi, gateway IP).
3. `cd firmware && pio run -t upload && pio device monitor`.

## Layout
- `firmware/` PlatformIO ESP32-S3 code; `vg_core/` portable DSP + int8 model (V2)
- `gateway/` FastAPI, SQLite, detectors, dashboard, simulator, tests
- `harness/` generic test harness: sources, scenarios, profiles, metrics
- `config/` hardware + machine profiles
- `sil/` software-in-the-loop firmware nodes (host-compiled)
- `docker/` images, compose, mosquitto config
- `tools/` dataset recording, NAS training, TinyML export (V2)
- `hardware/` BOM, wiring, bench-test procedure
- `docs/` implementation plan and testing guide
- `plans/` V2, V3, V4 specs
