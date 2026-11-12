# VibeGuard: Problem Statement

## The problem
Small workshops, pump houses and farms run dozens of motors, pumps and compressors with no condition monitoring.
Bearings and belts fail without warning, causing unplanned downtime and burnt motors.
Commercial vibration monitors cost USD 300-1,500 per machine and need cloud subscriptions, so they are out of reach for small operators.
Manual "listen with a screwdriver" inspection is subjective and infrequent.

## Specific goal
Build a sub-USD 25 battery or mains powered vibration node (ESP32-S3 + accelerometer) that:
1. samples a motor housing at 1 kHz and extracts features on-device (RMS, peak, crest factor, kurtosis, dominant frequency),
2. learns the machine's own healthy baseline during the first hours (no labelled fault data needed),
3. flags drift and fault signatures locally and reports to a gateway over MQTT/HTTP,
4. works offline, with a dashboard served from a local gateway (Raspberry Pi or laptop).

## Success metrics
| Metric | Target |
|---|---|
| Node BOM cost | < USD 25 |
| Detection of seeded bearing-like fault (bench test) | >= 90% recall, <= 1 false alarm/day |
| Feature window latency | < 1 s |
| Node power (WiFi duty-cycled) | < 120 mA average (V1), < 15 mA (V3) |
| Time to learn baseline | <= 60 windows |

## Why it grows your skills
Embedded C++ and DSP, sensor physics, Python backend, anomaly detection, then TinyML quantization (V2), PCB/enclosure/power design (V3), fleet/LoRa/continual learning and productization (V4).

## Versions
- V1 (this zip): working firmware + gateway + simulator + tests, hardware BOM and wiring.
- V2 `plans/PLAN_V2.md`: TinyML autoencoder on device.
- V3 `plans/PLAN_V3.md`: custom PCB, enclosure, power, OTA.
- V4 `plans/PLAN_V4.md`: fleet scale, LoRa, continual learning, productization.
