# VibeGuard V4: Fleet, long range, continual learning, productization (8-12 weeks)

**Goal:** run 20-50 nodes across a site, adapt to changing machines safely, and make it a product someone could actually deploy.

## Skills you build
Distributed systems, wireless (LoRa), MLOps at the edge, security, observability, documentation, user research, compliance basics.

## Deliverables
1. Connectivity: add LoRa (SX1262 module) or ESP-NOW mesh for sheds without WiFi; nodes send compact 32-byte feature frames, not raw data. Gateway = Raspberry Pi with LoRa HAT + MQTT broker (Mosquitto) + TimescaleDB or SQLite WAL.
2. Gateway v2: device registry, per-machine metadata (RPM, motor kW, bearing model), alert rules, hysteresis and maintenance-window suppression, Telegram/WhatsApp/email alerts, REST + WebSocket API, Grafana dashboards.
3. Continual learning: operating-condition clustering (load/speed states) so a baseline per state is kept; drift detector (PSI/KS test) proposing baseline refresh that an operator approves; model versioning and staged rollout (10% -> 100%) over OTA with automatic rollback if alarm rate spikes.
4. Fault diagnosis beyond "anomaly": order tracking, envelope spectrum with bearing defect frequencies (BPFO/BPFI/BSF/FTF from bearing geometry), classify imbalance / misalignment / looseness / bearing via rules first, small classifier second. Remaining-useful-life trend from RMS/kurtosis slope.
5. Security: per-device keys, mTLS or signed payloads, secure boot + flash encryption on ESP32-S3, update signing, threat-model doc.
6. Quality and operations: CI (unit tests, firmware build, hardware-in-loop smoke test), field logging, Prometheus metrics (packet loss, battery, rssi), 30-day pilot at a real site (pump house, workshop, farm) with weekly review.
7. Productization: install guide (10-minute install), quick-start video, pricing model (hardware + optional hosting), basic regulatory plan (CE/FCC for the radio module, battery transport rules), FMEA of top 10 failure modes.

## Milestones
| Weeks | Output |
|---|---|
| 1-2 | LoRa link budget test, frame format, gateway ingestion |
| 3-4 | Fleet dashboard, alerting, device registry |
| 5-6 | Multi-state baselines + drift detection offline on collected data |
| 7-8 | Signed OTA with staged rollout, security hardening |
| 9-10 | Bearing-frequency diagnosis, RUL trend |
| 11-12 | 30-day pilot, post-mortem, v1.0 release docs |

## Exit criteria
20+ nodes stable for 30 days, packet delivery > 98%, at least one true early-warning catch (or documented seeded-fault catch), false alarms < 1 per 10 machine-days, one external person installs a node from docs alone.

## Learning backlog (pick as you go)
Rust on ESP32 (esp-hal), Zephyr RTOS, Edge Impulse comparison, ONNX Runtime on Pi, vibration standards (ISO 10816/20816), Kalman filtering, federated updates across sites.
