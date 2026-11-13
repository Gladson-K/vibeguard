"""NAS search + int8 TinyML export.

Usage:
    python -m tools.train_autoencoder --quick --out models/tinyml
Produces:
    models/tinyml/model.json                     (Python-side artifact)
    firmware/src/vg_core/model_data.h            (int8 C runtime weights)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from tools.dataset import build_dataset
from tools.nas import auc, search
from tools.tinyml import arena_bytes, emulate_int8, emit_header, quantize

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "models" / "tinyml"
HEADER_PATH = ROOT / "firmware" / "src" / "vg_core" / "model_data.h"


def train(quick: bool = False, seed: int = 0, out: Path = DEFAULT_OUT):
    n_per_class = 80 if quick else 150
    epochs = 120 if quick else 250

    X, y, classes = build_dataset(n_per_class=n_per_class, seed=seed)
    healthy = X[y == 0]
    fault = X[y != 0]

    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(healthy))
    split = int(0.7 * len(healthy))
    h_train, h_val = healthy[idx[:split]], healthy[idx[split:]]
    f_idx = rng.permutation(len(fault))
    f_val = fault[f_idx[: len(h_val)]]

    mean = h_train.mean(axis=0)
    std = h_train.std(axis=0)
    std[std < 1e-6] = 1e-6

    def norm(a):
        return (a - mean) / std

    Xtr = norm(h_train)
    model, best, ranking = search(Xtr, norm(h_val), norm(f_val), epochs=epochs, seed=seed, quick=quick)

    float_scores_h = model.score(norm(h_val))
    float_scores_f = model.score(norm(f_val))
    float_auc = auc(
        np.r_[np.zeros_like(float_scores_h), np.ones_like(float_scores_f)],
        np.r_[float_scores_h, float_scores_f],
    )
    threshold = float(np.percentile(float_scores_h, 99.5))

    layers = quantize(model, Xtr)
    int8_scores_h = emulate_int8(layers, norm(h_val))
    int8_scores_f = emulate_int8(layers, norm(f_val))
    int8_auc = auc(
        np.r_[np.zeros_like(int8_scores_h), np.ones_like(int8_scores_f)],
        np.r_[int8_scores_h, int8_scores_f],
    )

    artifact = {
        "version": "tinyml-nas-v1",
        "n_bands": 15,
        "in_dim": int(X.shape[1]),
        "input_mean": mean.tolist(),
        "input_std": std.tolist(),
        "layers": layers,
        "threshold": threshold,
        "float_auc": round(float_auc, 4),
        "int8_auc": round(float(int8_auc), 4),
        "arena_bytes": arena_bytes(layers, int(X.shape[1])),
        "config": {k: best[k] for k in ("latent", "hidden", "act")},
        "params": best["params"],
        "classes": classes,
    }

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "model.json").write_text(json.dumps(artifact))
    (out / "nas_ranking.json").write_text(json.dumps(ranking, indent=2))
    emit_header(HEADER_PATH, artifact)

    summary = {
        "best_config": artifact["config"],
        "params": artifact["params"],
        "float_auc": artifact["float_auc"],
        "int8_auc": artifact["int8_auc"],
        "auc_drop": round(artifact["float_auc"] - artifact["int8_auc"], 4),
        "threshold": threshold,
        "arena_bytes": artifact["arena_bytes"],
        "model_json": str(out / "model.json"),
        "header": str(HEADER_PATH),
    }
    print(json.dumps(summary, indent=2))
    return artifact, summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", default=str(DEFAULT_OUT))
    a = p.parse_args()
    train(quick=a.quick, seed=a.seed, out=Path(a.out))


if __name__ == "__main__":
    main()
