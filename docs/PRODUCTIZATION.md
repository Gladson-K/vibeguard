# V4 Productization: pricing, FMEA, regulatory

## Packaging and pricing (placeholder, validate with 5 customers)

| Tier | Hardware | Software | Target price |
|---|---|---|---|
| Starter | 1 node + gateway | local dashboard, alerts | $249 one-time |
| Site | 5 nodes + Pi gateway | fleet, Grafana, 1 year updates | $1,200 + $25/mo |
| Pro | 20 nodes | hosted dashboard, Telegram/email, model rollout | $3,500 + $99/mo |

Hardware BOM at 100 units ≈ $22/node + gateway ≈ $90. Price includes install
support, not just hardware. Hosting cost is dominated by support time, not
compute; keep the local-first option to avoid connectivity assumptions on farms.

## Top-10 FMEA

| # | Failure mode | Effect | RPN driver | Mitigation |
|---|---|---|---|---|
| 1 | Node falls off machine | Lost monitoring | High detect | Mounting checklist, last-seen alert |
| 2 | Battery depleted | Lost monitoring | Medium | 3.3 V alert, 175-day budget, solar option |
| 3 | LoRa interference | Packet loss | High | SF9 fallback, ESP-NOW/Wi-Fi fallback, ACK/retry |
| 4 | Gateway SD card corruption | Site outage | High | Nightly backup, read-only root, UPS |
| 5 | Wrong machine profile | Bad diagnosis | Medium | Guided install, geometry check in prodtest |
| 6 | False alarm fatigue | Alerts ignored | High | Hysteresis, maintenance suppression, per-machine thresholds |
| 7 | Key lost/leaked | Spoofed data | High | Secure boot, flash encryption, key revocation |
| 8 | Bad model rollout | Fleet-wide noise | High | 10/50/100 staging, alarm-rate rollback |
| 9 | Sensor cable fatigue | Noisy data | Medium | Strain relief, cable gland, self-test |
| 10 | Water ingress | Corrosion | Medium | IP65 enclosure, conformal coat, gland down |

## Regulatory basics

- **Radio**: use a pre-certified SX1262 module and follow its CE/RED (EU) or FCC
  (US) grant; keep the antenna as certified, do not modify the RF path without
  re-testing. 868 MHz (EU) vs 915 MHz (US) is a build-time SKU.
- **Battery**: 18650 LiFePO4 shipped at < 30% SoC; UN38.3 test summary and
  Class 9 paperwork for air transport. Provide a charger with protection.
- **EMC/safety**: CE EMC + LVD for the charger; keep the gateway on a certified
  PSU. Machinery-directive responsibility stays with the machine integrator;
  VibeGuard is a monitoring accessory, not a safety device.
- **Data**: document what leaves the site (features, not raw vibration); offer a
  local-only mode. Add a privacy note for worker-adjacent installations.
- **Labeling**: model, serial, radio band, battery type, and "not a safety
  shutdown device" on the enclosure.

## Release checklist

- [ ] `make test-all` green (V1–V4)
- [ ] `pio run -e esp32s3_v4` green on the release toolchain
- [ ] Two-node LoRa range test + 24 h soak
- [ ] Signed OTA from 3.x to 4.x on a bench unit
- [ ] Secure boot/flash encryption verified on a pilot unit
- [ ] Install guide tested by someone outside the project
- [ ] Backup/restore and alert runbook walked through
