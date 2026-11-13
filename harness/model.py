"""Load the NAS-selected TinyML autoencoder for Python-side scoring.

The model artifact (models/tinyml/model.json) is produced by tools/train_autoencoder.py
(NAS search + int8 export). If no artifact exists, callers fall back to None so tests
can skip model-dependent assertions.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "models" / "tinyml" / "model.json"


class TinyMLModel:
    def __init__(self, artifact: dict):
        self.input_mean = np.asarray(artifact["input_mean"], dtype=float)
        self.input_std = np.asarray(artifact["input_std"], dtype=float)
        self.layers = []
        for layer in artifact["layers"]:
            w = np.asarray(layer["w_int8"], dtype=float) * float(layer["w_scale"])
            b = np.asarray(layer["b"], dtype=float)
            self.layers.append((w, b, layer.get("activation", "linear")))
        self.threshold = float(artifact.get("threshold", 0.0))
        self.version = artifact.get("version", "tinyml-nas-v1")
        self.n_bands = int(artifact.get("n_bands", 15))

    @classmethod
    def load(cls, path: str | Path = DEFAULT_MODEL) -> "TinyMLModel | None":
        p = Path(path)
        if not p.exists():
            return None
        return cls(json.loads(p.read_text()))

    def _activate(self, x, name):
        if name == "tanh":
            return np.tanh(x)
        if name == "relu":
            return np.maximum(x, 0.0)
        return x

    def reconstruct(self, feature_vector) -> np.ndarray:
        x = (np.asarray(feature_vector, dtype=float) - self.input_mean) / self.input_std
        for w, b, act in self.layers:
            x = self._activate(w @ x + b, act)
        return x

    def score(self, feature_vector) -> float:
        v = np.asarray(feature_vector, dtype=float)
        xn = (v - self.input_mean) / self.input_std
        xr = self.reconstruct(v)
        return float(np.mean((xn - xr) ** 2))
