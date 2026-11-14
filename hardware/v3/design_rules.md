# V3 PCB design rules and review checklist

Run this checklist before every prototype and pilot order. Tick each item in the
review; unresolved items block the order.

## Stackup and planes

- [ ] 4 layers: L1 signal, L2 continuous GND, L3 power, L4 signal.
- [ ] GND plane unsplit under the MCU, sensor, SPI and USB pair.
- [ ] No copper (any layer) in the 15 mm antenna keep-out.
- [ ] Power plane stitched to GND near each decoupling capacitor.

## Sensor (ADXL355)

- [ ] Package centered on the enclosure mounting axis/stud.
- [ ] X/Y axes marked on silkscreen; documented in the assembly note.
- [ ] No traces or vias under the sensor body; ground pour with thermal reliefs.
- [ ] SPI: CS/SCLK/MOSI/MISO < 30 mm, length-matched ±2 mm, no stubs.
- [ ] VDD 100 nF + 1 µF within 2 mm; VDDIO 100 nF + 1 µF within 2 mm.
- [ ] Sensor kept > 5 mm from the buck inductor and antenna.

## Power

- [ ] USB-C VBUS → ESD → charger → battery → buck; reverse Schottky present.
- [ ] 3V3 and 1V8 test points accessible with a pogo pin.
- [ ] VBAT divider values give < 3.3 V at full charge (1 MΩ / 1 MΩ).
- [ ] Charger PROG resistor sets ≤ 500 mA.
- [ ] Bulk 10 µF per rail plus local 100 nF at each IC.
- [ ] Buck layout: short input loop, ground pour, no routing under inductor.

## MCU and interfaces

- [ ] ESP32-S3-MINI-1 antenna at board edge; keep-out respected.
- [ ] USB D+/D- 90 Ω differential, equal length, ESD at connector.
- [ ] EN pull-up + 100 nF; IO0 accessible for download mode.
- [ ] UART0 TX/RX, EN, IO0, 3V3, 1V8, GND on pogo pads.
- [ ] Status LED and provision button on GPIO2/GPIO0 respectively.

## Manufacturing

- [ ] ERC clean (no unconnected pins, no power conflicts).
- [ ] DRC clean with the project rules (0.15 mm trace/space, 0.3 mm via).
- [ ] Courtyard/silkscreen references for every part; polarity marked.
- [ ] Fiducials on both sides if reflow; panel rails ≥ 5 mm.
- [ ] BOM has two sources for every active part (`bom.csv`).
- [ ] No parts with < 5 units MOQ gaps; alternates noted.
- [ ] Test-point labels match the jig fixture.

## Bring-up (first 5 boards)

- [ ] VBAT/3V3/1V8 rails measured before powering the MCU.
- [ ] Download mode + UART boot log captured.
- [ ] Sensor WHO_AM_I and self-test pass (`esp32s3_v3_prodtest`).
- [ ] Sensor noise floor compared with the dev-board prototype.
- [ ] Deep-sleep current measured with PPK2/INA219 (< 30 µA target).
- [ ] OTA from the pilot image succeeds and rollback survives a forced failure.
- [ ] Tap test on the enclosure, 10–500 Hz sweep, no mounting resonance.
