# VibeGuard V3: Custom hardware, power and OTA (6-8 weeks)

Status: **implemented** — design package in `hardware/V3_DESIGN.md` (BOM, design
rules, enclosure), firmware in `firmware/src/main_v3.cpp` + `firmware/src/v3/`,
portable policy in `firmware/src/vg_core/v3/`, verified by `make test-v3`
(power budget, signed OTA + rollback policy, prodtest, state machine, OTA E2E).
Physical PPK2/thermal/ESD/tap tests remain hardware-in-the-loop.

**Goal:** turn the breadboard prototype into a robust, manufacturable node.

## Skills you build
Schematic capture and PCB design (KiCad), power design, EMC basics, enclosure CAD/3D printing, low-power firmware, OTA updates, DFM.

## Deliverables
1. Schematic + 2-layer or 4-layer PCB (KiCad): ESP32-S3-MINI module, ADXL355 on its own quiet analog area, USB-C, Li-ion charger (MCP73831 or BQ24074), 3.3 V LDO or buck (TPS62740), fuel gauge or ADC divider, status LED, boot/reset buttons, SWD/UART pads.
2. Design rules: sensor placed on the mounting axis, ground pour under the sensor, decoupling at each IC, antenna keep-out, test points on every rail. Run DRC/ERC, review checklist.
3. Enclosure: IP54-ish printed case with a stud-mount or magnet base; mechanically rigid coupling to the machine (resonance check with a tap test).
4. Power: duty-cycled operation. Sample 1 s window, infer, transmit, deep sleep for 30-60 s. Target < 15 mA average, measured with a Nordic PPK2 or INA219 logger; estimate battery life (2000 mAh target >= 30 days).
5. Firmware: deep-sleep state machine, WiFi fast-reconnect (static IP, stored BSSID/channel), HTTPS/MQTT TLS, signed OTA (ESP-IDF OTA + rollback), provisioning via BLE or SoftAP captive portal.
6. Production test: pogo-pin jig script that checks rails, I2C/SPI WHO_AM_I, self-test of accelerometer, writes device ID and prints label.
7. Reliability: thermal soak (0-60 C), 7-day continuous run, brown-out test, ESD basics.

## Milestones
| Week | Output |
|---|---|
| 1-2 | Schematic review, BOM with 2 sources per part, order proto boards (5 pcs) |
| 3 | Bring-up checklist: rails, programming, sensor noise floor vs. dev-board |
| 4 | Power profiling, deep-sleep firmware |
| 5 | OTA + provisioning |
| 6 | Enclosure v1, mounting test on real machine |
| 7-8 | Revision B boards fixing bring-up issues, test jig, 5-unit pilot |

## Exit criteria
5 working units, average current < 15 mA, OTA works with rollback, noise floor equal to or better than the dev-board prototype, cost per unit at 100 qty < USD 25.
