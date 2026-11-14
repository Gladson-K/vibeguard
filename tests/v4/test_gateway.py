import importlib
import time

import pytest

from gateway import codec, rollout

KEY_HEX = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
KEY = bytes.fromhex(KEY_HEX)


@pytest.fixture()
def appmod(tmp_path, monkeypatch):
    monkeypatch.setenv("VG_DB", str(tmp_path / "t.db"))
    monkeypatch.delenv("VG_DEVICE_KEY_HEX", raising=False)
    import gateway.app as mod

    importlib.reload(mod)
    return mod


@pytest.fixture()
def client(appmod):
    from fastapi.testclient import TestClient

    return TestClient(appmod.app)


def _reading(device_id="bench-01", **kw):
    body = dict(
        device_id=device_id,
        rms=0.1,
        peak=0.3,
        crest=3.0,
        kurtosis=2.9,
        dom_freq=25,
    )
    body.update(kw)
    return body


def _frame(device_id=7, seq=1, ts=1000, rssi=-70):
    return codec.LoraFrame(
        device_id=device_id,
        seq=seq,
        ts=ts,
        rms=0.125,
        peak=0.4,
        crest=3.2,
        kurtosis=2.9,
        dom_freq=25,
        model_score=0.05,
        battery_mv=3800,
        rssi=rssi,
    )


def test_lora_ingest_and_fleet(client):
    r = client.post(
        "/api/ingest/lora",
        json={"frame_hex": codec.encode(_frame()).hex(), "device_id": "lora-0007"},
    )
    assert r.status_code == 200
    assert r.json()["device_id"] == "lora-0007"
    fleet = client.get("/api/fleet").json()
    assert fleet[0]["device_id"] == "lora-0007"
    assert fleet[0]["transport"] == "lora"
    assert fleet[0]["battery_mv"] == 3800
    assert fleet[0]["rssi"] == -70


def test_signed_lora_requires_key_and_rejects_tamper(client):
    raw = codec.sign(_frame(), KEY)
    assert client.put("/api/devices/lora-0007/key", json={"key_hex": KEY_HEX}).status_code == 200

    unsigned = client.post(
        "/api/ingest/lora",
        json={"frame_hex": codec.encode(_frame()).hex(), "device_id": "lora-0007"},
    )
    assert unsigned.status_code == 401

    ok = client.post(
        "/api/ingest/lora",
        json={"frame_hex": raw.hex(), "device_id": "lora-0007"},
    )
    assert ok.status_code == 200

    bad = bytearray(raw)
    bad[2] ^= 0x01
    rejected = client.post(
        "/api/ingest/lora",
        json={"frame_hex": bytes(bad).hex(), "device_id": "lora-0007"},
    )
    assert rejected.status_code == 401


def test_bad_crc_and_bad_hex(client):
    raw = bytearray(codec.encode(_frame()))
    raw[14] ^= 0x01
    assert client.post("/api/ingest/lora", json={"frame_hex": bytes(raw).hex()}).status_code == 401
    assert client.post("/api/ingest/lora", json={"frame_hex": "zz"}).status_code == 400
    assert client.post("/api/ingest/lora", json={"frame_hex": "00" * 10}).status_code == 400


def _calibrate(client, device_id, score=0.01, n=60):
    for i in range(n):
        client.post("/api/ingest", json=_reading(device_id, model_score=score, ts=1000 + i))


def test_alert_lifecycle_and_recovery(client):
    _calibrate(client, "fan-01")
    for i in range(3):
        r = client.post(
            "/api/ingest",
            json=_reading("fan-01", model_score=1.0, ts=2000 + i),
        )
    assert r.json()["status"] == "anomaly"
    alerts = client.get("/api/alerts").json()
    levels = [a["level"] for a in alerts]
    assert "warning" in levels and "critical" in levels

    for i in range(3):
        client.post("/api/ingest", json=_reading("fan-01", model_score=0.01, ts=3000 + i))
    recovery = [a for a in client.get("/api/alerts").json() if a["kind"] == "recovery"]
    assert recovery


def test_maintenance_suppresses_alerts(client):
    until = time.time() + 3600
    assert client.post(
        "/api/devices/maint-01/maintenance", json={"until": until, "note": "service"}
    ).status_code == 200
    _calibrate(client, "maint-01")
    for i in range(3):
        client.post("/api/ingest", json=_reading("maint-01", model_score=1.0, ts=2000 + i))
    assert client.get("/api/alerts").json() == []

    assert client.delete("/api/devices/maint-01/maintenance").status_code == 200
    client.post("/api/ingest", json=_reading("maint-01", model_score=1.0, ts=4000))
    assert any(a["device_id"] == "maint-01" for a in client.get("/api/alerts").json())


def test_alert_ack(client):
    _calibrate(client, "ack-01")
    for i in range(3):
        client.post("/api/ingest", json=_reading("ack-01", model_score=1.0, ts=2000 + i))
    alert = client.get("/api/alerts").json()[0]
    assert client.post(f"/api/alerts/{alert['id']}/ack").status_code == 200
    assert client.get("/api/alerts", params={"acknowledged": True}).json()[0]["id"] == alert["id"]


def test_machine_registry_and_assignment(client):
    names = {m["machine_id"] for m in client.get("/api/machines").json()}
    assert {"fan_25hz", "pump_50hz", "bench_motor"} <= names
    assert client.put(
        "/api/devices/fan-01", json={"machine_id": "fan_25hz", "fw_version": "4.0.0"}
    ).status_code == 200
    fleet = client.get("/api/fleet").json()[0]
    assert fleet["machine_id"] == "fan_25hz"
    assert fleet["fw_version"] == "4.0.0"


def test_rollout_selection_and_gate(client):
    client.post("/api/models", json={"version": "stable-1", "status": "stable"})
    client.post("/api/models", json={"version": "candidate-2"})
    r = client.post("/api/rollout", json={"model_version": "candidate-2", "stage": 0})
    assert r.status_code == 200
    assert r.json()["active"]["percent"] == 10

    inside = next(d for d in (f"dev-{i}" for i in range(500)) if rollout.bucket(d) < 10)
    outside = next(d for d in (f"dev-{i}" for i in range(500)) if rollout.bucket(d) >= 10)
    assert client.get(f"/api/rollout/device/{inside}").json()["selected"] is True
    out = client.get(f"/api/rollout/device/{outside}").json()
    assert out["selected"] is False and out["version"] == "stable-1"

    created = client.get("/api/rollout").json()["active"]["created"]
    from gateway import app as app_module

    for _ in range(30):
        app_module._db.execute(
            "INSERT INTO windows(device_id,ts,status) VALUES(?,?,?)",
            (inside, created + 1, "ok"),
        )
    app_module._db.commit()
    check = client.post("/api/rollout/check").json()
    assert check["action"] == "advance"
    assert check["stage"] == 1


def test_rollout_auto_rollback(client):
    client.post("/api/models", json={"version": "candidate-3"})
    client.post("/api/rollout", json={"model_version": "candidate-3", "stage": 2})
    created = client.get("/api/rollout").json()["active"]["created"]
    from gateway import app as app_module

    for i in range(30):
        app_module._db.execute(
            "INSERT INTO windows(device_id,ts,status) VALUES(?,?,?)",
            ("rolling-01", created + 1 + i, "anomaly"),
        )
    app_module._db.commit()
    check = client.post("/api/rollout/check").json()
    assert check["action"] == "rollback"
    assert check["stage"] == 1
    assert client.get("/api/rollout").json()["active"]["percent"] == 50


def test_drift_endpoint(client):
    for i in range(10):
        client.post("/api/ingest", json=_reading("drift-01", rms=0.1, ts=1000 + i))
    for i in range(10):
        client.post("/api/ingest", json=_reading("drift-01", rms=1.0, ts=2000 + i))
    rep = client.get("/api/drift/drift-01").json()
    assert rep["drift"] is True
    assert rep["psi"] > 0.2


def test_diagnosis_endpoint(client):
    client.put("/api/devices/fan-01", json={"machine_id": "fan_25hz"})
    from gateway import diagnosis as diag

    geom = diag.BearingGeometry(rpm=1500, n_balls=8, ball_d_mm=7.94, pitch_d_mm=39.04)
    f = diag.bearing_frequencies(geom)
    client.post(
        "/api/ingest",
        json=_reading("fan-01", kurtosis=6.0, dom_freq=f.bpfo, ts=1000),
    )
    out = client.get("/api/diagnosis/fan-01").json()
    assert out["fault"] == "bearing"
    assert out["frequencies"]["bpfo"] == pytest.approx(f.bpfo, abs=0.1)


def test_rul_endpoint(client):
    for i, rms in enumerate((0.1, 0.2, 0.3, 0.4)):
        client.post(
            "/api/ingest",
            json=_reading("rul-01", rms=rms, ts=1000 + i * 86400),
        )
    out = client.get("/api/rul/rul-01", params={"threshold": 1.0}).json()
    assert out["valid"] is True
    assert out["rul_days"] == pytest.approx(6.0, rel=0.05)


def test_metrics_and_websocket(client):
    with client.websocket_connect("/ws/events") as ws:
        client.post("/api/ingest", json=_reading("ws-01"))
        event = ws.receive_json()
    assert event["type"] == "window" and event["device_id"] == "ws-01"
    text = client.get("/api/metrics").text
    assert "vibeguard_windows_total" in text
    assert "vibeguard_rollout_percent" in text
    health = client.get("/api/health").json()
    assert health["ok"] is True
