import numpy as np

from gateway.features import compute_features


def test_dominant_freq():
    t = np.arange(512) / 1000
    f = compute_features(np.sin(2 * np.pi * 125 * t), 1000)
    assert abs(f["dom_freq"] - 125) < 2.5


def test_rms_of_sine():
    t = np.arange(1000) / 1000
    assert abs(compute_features(np.sin(2 * np.pi * 50 * t), 1000)["rms"] - 0.7071) < 0.01


def test_crest_and_kurtosis_of_sine():
    t = np.arange(1024) / 1000
    f = compute_features(np.sin(2 * np.pi * 40 * t), 1000)
    assert 1.3 < f["crest"] < 1.6
    assert 1.3 < f["kurtosis"] < 1.7
