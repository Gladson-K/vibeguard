import numpy as np

from gateway.detector import BaselineDetector, ModelScoreDetector
from gateway.features import compute_features
from gateway.simulator import window


def run(det, rng, n, fault):
    return [
        det.update(compute_features(window(rng, fault=fault), 1000))["status"]
        for _ in range(n)
    ]


def test_learns_in_60_windows():
    rng = np.random.default_rng(0)
    det = BaselineDetector()
    statuses = run(det, rng, 60, False)
    assert all(s == "learning" for s in statuses)
    assert det.learning is False


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


def test_model_score_threshold():
    det = ModelScoreDetector(calib_windows=20, persistence=1)
    healthy = [0.010, 0.012, 0.011, 0.013, 0.010] * 4
    for s in healthy:
        det.update(s)
    assert det.learning is False
    assert det.threshold == 0.013
    assert det.update(0.011)["status"] == "ok"
    assert det.update(0.5)["status"] == "anomaly"
