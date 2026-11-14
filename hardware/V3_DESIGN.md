# VibeGuard V3 — hardware, power and OTA design

Status: design + firmware + Docker verification complete; PCB/enclosure are ready
for prototype order. This document is the review artifact for the V3 milestones
in `plans/PLAN_V3.md`.

## 1. System blocks

```
USB-C ──ESD──> MCP73831 charger ──> Li-ion (JST-PH, 2000 mAh)
                                      │
                                      ├── VBAT ADC divider ──> ESP32 ADC
                                      └── TPS62740 buck 3V3 ──┬── ESP32-S3-MINI-1
                                                              ├── ADXL355 VDD
                                                              ├── TPS7A0218 1V8 ── ADXL355 VDDIO
                                                              └── status LED / dividers

ESP32-S3 SPI ──> ADXL355 (CS 10, SCLK 12, MOSI 11, MISO 13)
ESP32-S3 GPIO0 ──> provision button (INPUT_PULLUP)
ESP32-S3 GPIO2 ──> status LED
UART0 + SWD/test pads ──> factory pogo-pin jig
```

References: `hardware/v3/bom.csv`, `hardware/v3/design_rules.md`,
`hardware/v3/enclosure.scad`.

## 2. Schematic notes

- **MCU** — ESP32-S3-MINI-1-N8R2 (8 MB flash, 2 MB PSRAM). USB D+/D- to the
  USB-C receptacle through a USBLC6-2SC6 ESD array. Reset + boot buttons, UART0
  header, and test pads for 3V3, 1V8, GND, EN, IO0, TX, RX.
- **Sensor** — ADXL355B on SPI. VDD = 3V3, VDDIO = 1V8. 100 nF + 1 µF at each
  supply pin, ground pour under the package, no traces under the sensor. The
  package X/Y axes are aligned to the enclosure mounting plane; document the
  axis convention on the silkscreen.
- **Charger** — MCP73831 (2.0 A variant not required; 500 mA setting via 2 kΩ
  PROG resistor). Charge status LED, reverse-protection Schottky, 1 µF input and
  4.7 µF output capacitors.
- **Rail generation** — TPS62740 buck (3.3 V, 360 nA Iq) for the MCU/sensor,
  TPS7A0218 LDO (1.8 V, low noise) for sensor VDDIO. Both rails have test points
  and are checked by the production jig.
- **Battery monitoring** — 1 MΩ / 1 MΩ divider into an ADC pin, plus optional
  BQ27441-G1 footprint for coulomb counting on revision B.
- **Antenna** — module antenna at the board edge with a 15 mm copper-free
  keep-out on all layers and no battery/stud directly beneath it.

## 3. Power budget

Default duty cycle (`firmware/src/vg_core/v3/power_model.h`) replicates the
production profile: 1 s window at 12 mA, 50 ms inference at 20 mA, 100 ms
transmit at 80 mA, 45 s deep sleep at 20 µA.

| Phase | Current | Duration | Charge |
|---|---|---|---|
| Sample | 12 mA | 1000 ms | 12 000 mA·ms |
| Infer | 20 mA | 50 ms | 1 000 mA·ms |
| Transmit | 80 mA | 100 ms | 8 000 mA·ms |
| Deep sleep | 0.02 mA | 45 000 ms | 900 mA·ms |
| **Average** | **0.4745 mA** | 46.15 s | 21 900 mA·ms |

- Battery life (2000 mAh, no aging/DC-DC losses): **≈175 days**.
- Exit target < 15 mA average is met with roughly 30× margin; the binding
  constraint is real sleep current, which must be measured with a PPK2/INA219.
- `sil/v3_power_main.cpp` exposes this model to CI; `tests/v3/test_power_model.py`
  asserts the target and monotonicity, and flags aggressive profiles.

## 4. PCB design rules

Checklist and rationale in `hardware/v3/design_rules.md`. Summary:

- 4-layer: signal / GND / PWR / signal; continuous ground under the sensor and
  MCU; no splits under SPI or the antenna keep-out.
- Sensor on the mounting axis, close to the stud, SPI traces < 30 mm and
  length-matched.
- Decoupling within 2 mm of every supply pin; bulk 10 µF per rail.
- USB-C differential pair 90 Ω, ESD at the connector.
- Test points on every rail and on EN/IO0/TX/RX for the pogo jig.
- Run ERC + DRC with the project rules; review the checklist before ordering.

## 5. Firmware architecture (V3)

| Concern | File |
|---|---|
| Deep-sleep duty cycle + wake bookkeeping | `firmware/src/v3/power.{h,cpp}`, `vg_core/v3/state_machine.*` |
| Fast Wi-Fi reconnect (BSSID/channel/static IP) | `firmware/src/v3/wifi_fast.{h,cpp}` |
| SoftAP captive provisioning | `firmware/src/v3/provisioning.{h,cpp}` |
| Signed OTA + rollback | `firmware/src/v3/ota.{h,cpp}`, `vg_core/v3/ota_verify.*`, `vg_core/v3/sha256.*` |
| Production test policy | `firmware/src/v3/prodtest.{h,cpp}`, `vg_core/v3/prodtest.*` |
| Glue + sensing | `firmware/src/main_v3.cpp`, `adxl.*`, `vg_core/features_v2.*`, `vg_core/model.*` |

OTA policy: the manifest is HMAC-SHA256 authenticated over a canonical
newline-delimited payload (`vg-ota-v1\nversion\nmin_version\nsize\nsha256\n`).
The firmware rejects bad signatures, hash/size mismatches, downgrades and
versions below the minimum. A new image boots as `PENDING_VERIFY`; it is only
confirmed after the accelerometer self-test passes, otherwise the boot partition
is switched back. `firmware/src/v3/v3_config.h` documents the per-device key and
duty-cycle constants.

## 6. Production test (pogo-pin jig)

1. Flash the `esp32s3_v3_prodtest` image over UART.
2. Jig asserts power, reads the printed label from UART.
3. Firmware checks 3V3 and 1V8 rails, flash/NVS, ADXL WHO_AM_I and self-test.
4. On pass it stores the device ID in NVS and prints
   `VG3-<id>-<sensor>-<fw>-PASS`; failures print `FAIL-<reason>`.
5. Operator applies the label and moves the unit to the burn-in rack.

The policy is `vg::prodtest_evaluate` (`vg_core/v3/prodtest.cpp`) and is
exercised for every failure path by `tests/v3/test_prodtest.py`.

## 7. Enclosure and mounting

`hardware/v3/enclosure.scad` provides a parametric two-part case:

- rigid boss under the sensor, aligned with the M3 stud/magnet pocket;
- USB-C and provision-button openings;
- internal battery pocket and antenna keep-out;
- wall thickness 2 mm, lid with four M2 screws.

Tap-test each new enclosure revision: mount on a bench motor, sweep 10–500 Hz,
and compare the sensor spectrum to the bare dev board. A resonance in the
mounting band invalidates the configuration.

## 8. Reliability and bring-up

| Test | Procedure | Pass criterion |
|---|---|---|
| Rails | Jig / DMM at test points | 3.3 V ±5 %, 1.8 V ±5 % |
| Sensor noise | 60 s still, compute RMS | ≤ dev-board prototype + 10 % |
| Thermal soak | 0 °C / 25 °C / 60 °C, 2 h each | no resets, score drift < 5 % |
| Brown-out | Ramp VBAT 3.6 → 2.5 → 3.6 V | clean reset, no flash corruption |
| ESD | IEC 61000-4-2 contact ±4 kV on case/USB | no latch-up; recover on reset |
| 7-day run | Bench motor, 45 s cycle | no watchdog resets, packet loss < 2 % |
| OTA | Signed update + power-cut mid-flash | valid image or rollback to previous |

## 9. Verification mapping (Docker)

`make test-v3` builds the V3 SIL binaries and runs:

- `test_power_model.py` — duty-cycle math, target and monotonicity;
- `test_ota.py` — canonical parity, valid/tampered/wrong-key/downgrade/too-old/
  size/signature cases;
- `test_prodtest.py` — pass label plus every first-failure reason;
- `test_state.py` — deep-sleep state-machine transitions;
- `test_ota_e2e.py` — fetches manifest + firmware from the mock OTA server and
  verifies them, then rejects a tampered download.

Physical measurements (PPK2, thermal, ESD, tap test) remain hardware-in-the-loop
and are listed above for the pilot build.

## 10. Exit criteria

| Criterion | Target | Where tracked |
|---|---|---|
| Working units | 5 | pilot build (hardware) |
| Average current | < 15 mA | power model + PPK2 |
| OTA with rollback | required | `test_ota.py`, `test_ota_e2e.py`, bench |
| Noise floor | ≤ dev board | bring-up test |
| Cost @100 qty | < USD 25 | `bom.csv` roll-up |
