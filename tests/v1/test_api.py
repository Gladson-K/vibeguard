import importlib

from fastapi.testclient import TestClient


def _reload_app(tmp_path, monkeypatch):
    monkeypatch.setenv("VG_DB", str(tmp_path / "t.db"))
    monkeypatch.delenv("MQTT_HOST", raising=False)
    import gateway.app as appmod

    return importlib.reload(appmod)


def test_ingest_learning_and_devices(tmp_path, monkeypatch):
    appmod = _reload_app(tmp_path, monkeypatch)
    c = TestClient(appmod.app)
    r = c.post(
        "/api/ingest",
        json=dict(device_id="d", rms=0.05, peak=0.1, crest=2, kurtosis=3, dom_freq=25),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "learning"
    devs = c.get("/api/devices").json()
    assert devs[0]["device_id"] == "d"


def test_history_and_reset(tmp_path, monkeypatch):
    appmod = _reload_app(tmp_path, monkeypatch)
    c = TestClient(appmod.app)
    for _ in range(3):
        c.post(
            "/api/ingest",
            json=dict(device_id="d2", rms=0.05, peak=0.1, crest=2, kurtosis=3, dom_freq=25),
        )
    hist = c.get("/api/history/d2").json()
    assert len(hist) == 3
    assert c.post("/api/reset/d2").json()["ok"] is True


def test_model_score_field(tmp_path, monkeypatch):
    appmod = _reload_app(tmp_path, monkeypatch)
    c = TestClient(appmod.app)
    r = c.post(
        "/api/ingest",
        json=dict(
            device_id="m",
            rms=0.05,
            peak=0.1,
            crest=2,
            kurtosis=3,
            dom_freq=25,
            model_score=0.01,
            model_version="test",
        ),
    )
    assert r.status_code == 200
    hist = c.get("/api/history/m").json()
    assert hist[-1]["model_score"] == 0.01
