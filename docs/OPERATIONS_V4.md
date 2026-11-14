# V4 Operations Runbook

## Daily checks

- `GET /api/fleet` — every expected node present, battery > 3.3 V, RSSI > −110.
- `GET /api/alerts?acknowledged=false` — triage, then `POST /api/alerts/{id}/ack`.
- `GET /api/metrics` — error rate, anomalies, rollout percentage.
- Grafana (`make obs`) — anomalies/hour, battery, RSSI, ingest errors.

## Alert policy

Alerts are created by the gateway after the detector's persistence rule:

- `warning`: one feature z-score above threshold (or model ratio > 1).
- `critical`: detector reaches `anomaly` (3 consecutive windows).
- `recovery`: 3 consecutive healthy windows (`AlertEngine.clear_after`).
- Critical does not downgrade to warning; only recovery clears it.

Maintenance suppression:

```bash
curl -X POST http://<pi>:18000/api/devices/<id>/maintenance \
     -H 'content-type: application/json' \
     -d '{"until":1760000000,"note":"bearing replacement"}'
curl -X DELETE http://<pi>:18000/api/devices/<id>/maintenance
```

While suppressed, windows are still stored and drift/RUL keep updating, but no
alerts are emitted or notified.

## Diagnosis

`GET /api/diagnosis/<device_id>` returns BPFO/BPFI/BSF/FTF computed from the
machine geometry and a first-pass class (`imbalance`, `misalignment`,
`looseness`, `bearing`, `unknown`). Rules run before any classifier; a
bearing-class result requires envelope energy near a defect frequency.

Use ISO 10816/20816 velocity limits for the final severity decision; the V4
RMS thresholds are a starting point, not a certification.

## RUL

`GET /api/rul/<device_id>?threshold=0.5&metric=rms` fits a linear trend over the
last 200 windows. It is only valid when the slope is positive and there are at
least 3 samples. Treat < 7 days as "plan maintenance", < 2 days as "stop and
inspect". Do not use RUL for safety-critical shutdowns.

## Drift and baseline refresh

`GET /api/drift/<device_id>?metric=rms` compares the first half of the window
history with the second half (PSI + KS). `drift=true` means the machine or its
operating point changed; it is a prompt for an operator, not an automatic
baseline update.

Approved refresh workflow:

1. Confirm the change is benign (new load/speed regime, sensor remount).
2. Collect ≥ 2 hours of healthy data in the new regime.
3. `POST /api/reset/<device_id>` and let the detector learn 60 windows again.
4. Record the change in the maintenance note; keep the old DB backup.

## Staged model rollout

```bash
curl -X POST http://<pi>:18000/api/models \
     -H 'content-type: application/json' \
     -d '{"version":"tinyml-v2","path":"/models/tinyml-v2","status":"stable"}'
curl -X POST http://<pi>:18000/api/rollout \
     -H 'content-type: application/json' \
     -d '{"model_version":"tinyml-v2","stage":0}'   # 10%
```

- `GET /api/rollout/device/<id>` shows the assigned version and bucket.
- `POST /api/rollout/check` advances 10% → 50% → 100% when the alarm rate is
  < 5%, and rolls back one stage when > 25% after 20 samples.
- Manual rollback: set stage to 0 or re-activate the previous model.
- Device selection is deterministic (FNV-1a bucket), so a node does not bounce
  between versions across reboots.

## 30-day pilot

Week 0: install 5–10 nodes, verify packet delivery > 98%, baseline learning.
Week 1: tune per-machine thresholds; record the first true/false alarms.
Week 2: add the remaining nodes; test one seeded fault (loosen a mounting bolt).
Week 3: exercise maintenance suppression and one staged model rollout.
Week 4: review false-alarm rate (< 1 per 10 machine-days), battery, RSSI,
export a report, and decide go/no-go.

Keep a daily log of: node count, missing nodes, alerts, false alarms, battery
min/median, RSSI min, packets lost, and any maintenance windows.

## Backup / restore

SQLite WAL: stop the gateway or use `sqlite3 vibeguard.db ".backup"`. Keep
`vibeguard.db`, `models/`, and `config/machines.yaml` together. Restore to a
fresh volume, start the gateway, then re-run `GET /api/health` and `/api/fleet`.
