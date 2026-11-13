# Hardware (V1)

## BOM (approx. USD)
| Part | Qty | Cost |
|---|---|---|
| ESP32-S3 DevKitC-1 (or any ESP32-S3 board) | 1 | 6-8 |
| MPU-6050 (GY-521) breakout | 1 | 1.5-3 |
| USB 5V supply / power bank | 1 | 3-5 |
| Neodymium disc magnet 20 mm + epoxy or M4 stud mount | 1 | 2 |
| Jumper wires, small project box | 1 | 3 |

## Wiring
| MPU-6050 | ESP32-S3 |
|---|---|
| VCC | 3V3 |
| GND | GND |
| SDA | GPIO8 |
| SCL | GPIO9 |
| AD0 | GND (address 0x68) |

## Mounting
Rigid mount on the motor bearing housing, closest to the load. Loose mounting kills high frequencies. A magnet on bare metal is fine for V1; stud mount is better.

## Bench test procedure
1. Mount on a small DC fan or drill. Record 60+ windows healthy (baseline).
2. Add fault: tape a small weight on the rotor (imbalance), or lightly rub a card against the fan blade (impacts).
3. Confirm status turns ANOMALY within a few windows. Note rms, crest, kurtosis shifts.
4. Log results in a table: fault type, detection delay, score peak.

## V2 sensing upgrade (ADXL345 / ADXL355 over SPI)
| ADXL345 | ESP32-S3 |
|---|---|
| VCC | 3V3 |
| GND | GND |
| CS | GPIO10 |
| SCLK | GPIO12 |
| MOSI | GPIO11 |
| MISO | GPIO13 |

ADXL355 uses the same SPI pins (its registers are shifted, handled in `firmware/src/adxl.cpp`).
Both run at 3.2 kHz, giving bearing defect frequencies up to ~1.5 kHz.

## Known V1 limits
MPU-6050 is noisy and limited to about 1 kHz bursts over I2C, so bearing defect frequencies above 500 Hz are invisible. V2/V3 replace it with an ADXL355/ADXL345 over SPI.
