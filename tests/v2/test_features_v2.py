import numpy as np

from harness.features_v2 import FEATURE_DIM, N_BANDS, compute_features_v2


def test_vector_dimensions():
    x = np.random.default_rng(0).normal(1.0, 0.01, 2048)
    f = compute_features_v2(x, 3200)
    assert len(f["feature_vector"]) == FEATURE_DIM == 24
    assert len(f["bands"]) == N_BANDS == 15


def test_centroid_of_sine():
    t = np.arange(2048) / 3200
    f = compute_features_v2(np.sin(2 * np.pi * 100 * t), 3200)
    assert abs(f["spectral_centroid"] - 100) < 10


def test_band_energy_increases_with_tone():
    t = np.arange(2048) / 3200
    quiet = compute_features_v2(0.001 * np.sin(2 * np.pi * 100 * t), 3200)
    loud = compute_features_v2(1.0 * np.sin(2 * np.pi * 100 * t), 3200)
    # a louder tone must raise the total band energy
    assert sum(loud["bands"]) > sum(quiet["bands"])


def test_kurtosis_high_for_impacts():
    rng = np.random.default_rng(1)
    x = rng.normal(0, 0.01, 2048)
    x[::128] += 1.0
    f = compute_features_v2(x, 3200)
    assert f["kurtosis"] > 5
