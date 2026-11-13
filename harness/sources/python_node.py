"""Pure-Python virtual node: generates windows, extracts features, scores them."""
from __future__ import annotations

import time

import numpy as np

from harness.signal import generate_window
from harness.sources.base import FrameSource

try:
    from gateway.features import compute_features as compute_features_v1
except ImportError:  # pragma: no cover - path set by container/tests
    from features import compute_features as compute_features_v1


class PythonNodeSource(FrameSource):
    def __init__(self, scenario: dict, model=None):
        self.scenario = scenario
        self.model = model
        self.version = scenario.get("version", "v1")

    def frames(self):
        s = self.scenario
        sensor = s["sensor_profile"]
        machine = s["machine_profile"]
        fs = int(sensor["fs"])
        n = int(sensor["window"])
        rng = np.random.default_rng(int(s.get("seed", 1)))
        total = int(s.get("total_windows", 400))
        fault_after = s.get("fault_after")
        fault = s.get("fault")
        device_id = s["device_id"]

        for i in range(total):
            active_fault = fault if (fault_after is not None and i >= fault_after) else None
            x = generate_window(rng, fs, n, machine, sensor, active_fault)

            if self.version == "v2":
                from harness.features_v2 import compute_features_v2

                feats = compute_features_v2(x, fs)
                frame = {
                    "device_id": device_id,
                    "fs": fs,
                    "ts": float(i),
                    "sensor": s["sensor"],
                    **{k: feats[k] for k in ("rms", "peak", "crest", "kurtosis", "dom_freq")},
                    "bands": feats["bands"],
                }
                if self.model is not None:
                    src = self.model
                    score = src.score(feats["feature_vector"]) if hasattr(src, "score") else src(feats["feature_vector"])
                    frame["model_score"] = float(score)
                    frame["model_version"] = getattr(src, "version", "tinyml-nas-v1")
            else:
                feats = compute_features_v1(x, fs)
                frame = {
                    "device_id": device_id,
                    "fs": fs,
                    "ts": float(i),
                    "sensor": s["sensor"],
                    **feats,
                }
            yield frame
