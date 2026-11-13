"""Neural Architecture Search over small dense autoencoders.

Searches latent size, hidden width and activation; selects the architecture with
the best anomaly separation (AUC) on held-out healthy vs fault windows, breaking
ties by fewer parameters (friendlier to the ESP32-S3 flash budget).
"""
from __future__ import annotations

import numpy as np

from tools.autoencoder import ACT_RELU, ACT_TANH, Autoencoder

# (latent, hidden, activation)
CONFIGS = [
    {"latent": 2, "hidden": 12, "act": ACT_TANH},
    {"latent": 3, "hidden": 12, "act": ACT_TANH},
    {"latent": 4, "hidden": 16, "act": ACT_TANH},
    {"latent": 2, "hidden": 16, "act": ACT_TANH},
    {"latent": 4, "hidden": 24, "act": ACT_TANH},
    {"latent": 3, "hidden": 16, "act": ACT_RELU},
    {"latent": 4, "hidden": 16, "act": ACT_RELU},
    {"latent": 6, "hidden": 24, "act": ACT_TANH},
]

ACT_NAMES = {ACT_TANH: "tanh", ACT_RELU: "relu", 0: "linear"}


def auc(labels: np.ndarray, scores: np.ndarray) -> float:
    labels = np.asarray(labels)
    scores = np.asarray(scores)
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)
    n_pos = int(labels.sum())
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5
    sum_pos = ranks[labels == 1].sum()
    return float((sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def dims_for(dim: int, cfg: dict) -> list[int]:
    h = cfg["hidden"]
    return [dim, h, cfg["latent"], h, dim]


def acts_for(cfg: dict) -> list[int]:
    return [cfg["act"], cfg["act"], cfg["act"], 0]


def search(
    X_train: np.ndarray,
    X_healthy: np.ndarray,
    X_fault: np.ndarray,
    epochs: int = 200,
    seed: int = 0,
    quick: bool = False,
):
    dim = X_train.shape[1]
    configs = CONFIGS[:4] if quick else CONFIGS
    results = []
    for cfg in configs:
        model = Autoencoder(dims_for(dim, cfg), acts_for(cfg), seed=seed)
        model.fit(X_train, epochs=epochs, seed=seed)
        sh = model.score(X_healthy)
        sf = model.score(X_fault)
        a = auc(np.r_[np.zeros_like(sh), np.ones_like(sf)], np.r_[sh, sf])
        results.append(
            {"auc": round(a, 4), "params": model.n_params, "model": model, **cfg}
        )
    results.sort(key=lambda r: (r["auc"], -r["params"]), reverse=True)
    best = results[0]
    ranking = [{k: v for k, v in r.items() if k != "model"} for r in results]
    return best["model"], best, ranking
