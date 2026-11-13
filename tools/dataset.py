"""Build a labelled V2 feature dataset from synthetic machine windows."""
from __future__ import annotations

import numpy as np

from harness.features_v2 import compute_features_v2
from harness.profiles import load_profiles
from harness.signal import generate_window

CLASSES = ["healthy", "imbalance", "looseness", "bearing", "belt"]


def build_dataset(
    n_per_class: int = 120,
    seed: int = 0,
    sensor: str = "adxl345",
    machine: str = "fan_25hz",
    amplitude: float = 0.3,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    hw, machines = load_profiles()
    sensor_p = hw[sensor]
    machine_p = machines[machine]
    fs = int(sensor_p["fs"])
    n = int(sensor_p["window"])
    rng = np.random.default_rng(seed)

    X, y = [], []
    for ci, label in enumerate(CLASSES):
        for _ in range(n_per_class):
            fault = None if label == "healthy" else {"type": label, "amplitude": amplitude}
            w = generate_window(rng, fs, n, machine_p, sensor_p, fault)
            X.append(compute_features_v2(w, fs)["feature_vector"])
            y.append(ci)
    return np.asarray(X, dtype=float), np.asarray(y, dtype=int), CLASSES
