# V4 Install Guide (10-minute site install)

## What you need

- 1 site gateway: Raspberry Pi 4/5 (2 GB+), 16 GB SD card, Ethernet or Wi-Fi.
- 1–50 V4 LoRa nodes with charged 18650 cells and 868/915 MHz antennas.
- A machine per node: clean mounting pad on the bearing housing, M6 bolt or
  magnet plate.
- A phone/laptop on the same network for the dashboard.

## 1. Gateway (5 minutes)

```bash
git clone git@github.com:Gladson-K/vibeguard.git
cd vibeguard
cp .env.example .env            # set VG_GATEWAY_PORT, VG_DEVICE_KEY_HEX if used
make up                         # gateway + mosquitto
open http://<pi-ip>:18000       # dashboard
```

Optional observability:

```bash
make obs                        # Prometheus :19090, Grafana :13000
```

The gateway creates `vibeguard.db` (SQLite, WAL) in the `vgdata` volume. Back it
up nightly: `docker run --rm -v docker_vgdata:/data -v $PWD:/backup alpine tar
czf /backup/vibeguard-$(date +%F).tgz /data`.

## 2. Node (2 minutes per node)

1. Flash the V4 image: `cd firmware && pio run -e esp32s3_v4 -t upload`.
2. Hold the provisioning button at boot; join the `VibeGuard-XXXX` SoftAP and
   enter the site Wi-Fi (used for OTA/ESP-NOW fallback only; data goes over LoRa).
3. Register the node on the gateway:
   ```bash
   curl -X PUT http://<pi-ip>:18000/api/devices/lora-0007 \
        -H 'content-type: application/json' \
        -d '{"machine_id":"pump_50hz","fw_version":"4.0.0"}'
   ```
4. Mount the node with the antenna vertical and the cable gland pointing down.
5. Confirm telemetry: `curl http://<pi-ip>:18000/api/fleet`.

## 3. Per-device signing key

```bash
curl -X PUT http://<pi-ip>:18000/api/devices/lora-0007/key \
     -H 'content-type: application/json' \
     -d '{"key_hex":"<32-byte-hex-from-prodtest>"}'
```

Once a key is registered the gateway rejects unsigned frames for that device.
Use `tools/fleet_sim.py --signed --key-hex ...` for a bench check.

## 4. Machine metadata

`config/machines.yaml` is seeded at startup (rpm + bearing defect frequencies).
Add a machine or override geometry:

```bash
curl -X POST http://<pi-ip>:18000/api/machines \
     -H 'content-type: application/json' \
     -d '{"machine_id":"pump_50hz","rpm":3000,"n_balls":9,"ball_d_mm":8.7,
          "pitch_d_mm":42.0,"rms_warn":0.35,"rms_crit":0.5}'
```

Then assign it to a node (`PUT /api/devices/<id>` with `machine_id`).

## 5. Verify

```bash
curl http://<pi-ip>:18000/api/health
curl http://<pi-ip>:18000/api/metrics | head
curl http://<pi-ip>:18000/api/alerts
```

Next: [`OPERATIONS_V4.md`](OPERATIONS_V4.md) for alert response, rollout and the
30-day pilot checklist.
