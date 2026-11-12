# VibeGuard V1

Edge vibration anomaly monitor. See `PROBLEM_STATEMENT.md`.

## Quick start (no hardware needed)
```bash
cd gateway
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q                         # run tests
uvicorn app:app --port 8000       # terminal 1: gateway + dashboard
python simulator.py --fault-after 120   # terminal 2: fake machine, fault injected after 120 windows
```
Open http://localhost:8000. The first 60 windows are baseline learning, then faults turn the status red.

## With hardware
1. Wire per `hardware/WIRING_AND_BOM.md`.
2. Edit `firmware/src/config.h` (WiFi, gateway IP).
3. `cd firmware && pio run -t upload && pio device monitor`
4. Optional MQTT: `MQTT_HOST=<broker> uvicorn app:app` (topic `vibeguard/<id>/features`).

## Layout
- `firmware/` PlatformIO ESP32-S3 code (MPU6050, FFT, features, HTTP/MQTT)
- `gateway/` FastAPI, SQLite, anomaly detector, dashboard, simulator, tests
- `hardware/` BOM, wiring, bench-test procedure
- `plans/` V2, V3, V4 plans
