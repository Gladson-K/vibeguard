# VibeGuard V4 Hardware Design — LoRa Fleet Node + Site Gateway

Status: design implemented in firmware (`esp32s3_v4`) and gateway software.
Host/SIL tests are authoritative; the PlatformIO toolchain build is still the
hardware gate before a pilot deployment.

## 1. Node architecture

```
ADXL345/ADXL355 ──SPI──┐
                       ├── ESP32-S3 ──SPI── SX1262 (868 MHz) ── antenna
battery divider ──ADC──┘      │
                              ├── USB-C (flash / prodtest / charging)
                              ├── status LED + provisioning button
                              └── optional ESP-NOW fallback (Wi-Fi associated)
```

- Sensing stays on the V2 path: ADXL over SPI, 3200 Hz, 2048-sample window.
- Features and the int8 TinyML autoencoder run on-device (V2 core).
- V4 adds a **compact 32-byte LoRa frame** (40 bytes signed) instead of JSON.
- A 45 s duty cycle plus LoRa TX fits the V3 power budget (~0.47 mA average,
  >175 days on 2000 mAh).

## 2. LoRa link

| Parameter | Value |
|---|---|
| Radio | SX1262 (Semtech), SPI mode 0, 8 MHz |
| Band | 868 MHz (EU) / 915 MHz (US) — build-time frequency |
| Spreading factor | SF7 (fleet default), SF9 for long-range sites |
| Bandwidth | 125 kHz |
| Coding rate | 4/5 |
| TX power | +14 dBm |
| Sync word | 0x12 private |
| Payload | 32 B telemetry, 40 B authenticated |
| Air time | ~60 ms at SF7/125 kHz |

Pins (ESP32-S3): SCK 12, MISO 13, MOSI 11, CS 14, RESET 15, BUSY 16, DIO1 17.
Keep the antenna keep-out free of copper and route the 50 Ω trace with a
grounded coplanar waveguide.

### Frame layout

See `firmware/src/vg_core/v4/codec.h` (the single source of truth) and
`gateway/codec.py`. All multi-byte fields are little-endian.

```
0  version u8         8  ts u32           16 peak u16/1000    24 model_score u16/100
1  flags u8           12 rms u16/1000     18 crest u16/100    26 battery_mv u16
2  device_id u32      14 (reserved u16)   20 kurtosis u16/100 28 rssi i16
6  seq u32                                  22 dom_freq u16    30 crc16-ccitt
```

Flags: bit0 drift, bit1 low battery, bit2 ESP-NOW fallback. Signed frames
append `HMAC-SHA256(device_key, frame)[:8]`.

## 3. Site gateway

A Raspberry Pi 4/5 (2 GB+) or an ESP32-S3 LoRa bridge runs:

- Mosquitto MQTT broker (`1883`),
- the FastAPI gateway (`gateway/app.py`, port 8000 / host 18000),
- SQLite in WAL mode (single site) or TimescaleDB (multi-site, 30-day pilot),
- optional Prometheus + Grafana (compose profile `obs`).

LoRa frames arrive either through a serial/SPI bridge or an MQTT topic; the
gateway verifies CRC/HMAC, applies per-device replay protection and ingests the
same feature schema as V1/V2.

## 4. Security and provisioning

- Each node has a unique 32-byte key written to NVS during production test.
- Frames are signed and replay-protected by monotonic `seq`.
- Flash encryption + secure boot v2 are enabled on pilot units; see
  `docs/V4_SECURITY.md` for the eFuse procedure and key custody.
- OTA reuses the V3 signed-manifest flow (HMAC-SHA256, anti-downgrade,
  pending-verify rollback).

## 5. Power

| Block | Current | Duty |
|---|---|---|
| Deep sleep | 20 µA | 45 s |
| ADXL + sampling | 20 mA | 50 ms |
| TinyML inference | 12 mA | 1 s |
| SX1262 TX | 80 mA | 100 ms |

Expected average 0.4745 mA → ~175 days on 2000 mAh. Low-battery flag at 3.3 V.

## 6. Enclosure and environment

IP65 ABS enclosure, 90 × 60 × 35 mm, M8 cable gland, external 868 MHz antenna
with a 10 cm ground plane. Mount with a magnet/bolt plate on the machine
bearing housing; keep the antenna vertical. Operating range −20…+60 °C; the
ADXL is rated beyond this but battery life degrades below 0 °C.

## 7. Production test

`esp32s3_v3_prodtest` remains for battery-node hardware. V4 adds the LoRa
self-test through `sil/v4_codec_main` on the host and the following factory
checks:

1. Rail voltages (3V3/1V8) and battery divider.
2. ADXL WHOAMI + self-test.
3. SX1262 version/status read, TX at +14 dBm into a dummy load.
4. Key injection (unique, not the bench key) and sequence reset.
5. Signed frame round-trip against the factory gateway.
6. Secure-boot/encryption fuse verification and OTA manifest signature check.

## 8. Open hardware gate

The PlatformIO xtensa toolchain download is blocked in the current environment,
so `pio run -e esp32s3_v4` has not run. Compile the firmware, then validate the
LoRa link with two nodes and one gateway before the 30-day pilot.
