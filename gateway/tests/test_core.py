import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
import numpy as np
from features import compute_features
from detector import BaselineDetector
from simulator import window

def test_dominant_freq():
    t = np.arange(512) / 1000
    f = compute_features(np.sin(2 * np.pi * 125 * t), 1000)
    assert abs(f["dom_freq"] - 125) < 2.5

def test_rms_of_sine():
    t = np.arange(1000) / 1000
    assert abs(compute_features(np.sin(2 * np.pi * 50 * t), 1000)["rms"] - 0.7071) < 0.01

def run(det, rng, n, fault):
    out = []
    for _ in range(n):
        out.append(det.update(compute_features(window(rng, fault=fault), 1000))["status"])
    return out

def test_no_false_alarms_on_healthy():
    rng = np.random.default_rng(0)
    det = BaselineDetector()
    run(det, rng, 60, False)
    assert "anomaly" not in run(det, rng, 300, False)

def test_fault_detected():
    rng = np.random.default_rng(0)
    det = BaselineDetector()
    run(det, rng, 60, False)
    assert "anomaly" in run(det, rng, 10, True)

def test_api_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("VG_DB", str(tmp_path / "t.db"))
    from fastapi.testclient import TestClient
    import importlib, app as appmod
    importlib.reload(appmod)
    c = TestClient(appmod.app)
    r = c.post("/api/ingest", json=dict(device_id="d", rms=.05, peak=.1, crest=2, kurtosis=3, dom_freq=25))
    assert r.json()["status"] == "learning"
    assert c.get("/api/devices").json()[0]["device_id"] == "d"
