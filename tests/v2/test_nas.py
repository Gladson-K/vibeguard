import numpy as np

from tools.dataset import build_dataset
from tools.nas import search


def test_nas_selects_separating_model():
    X, y, _ = build_dataset(n_per_class=25, seed=3)
    healthy, fault = X[y == 0], X[y != 0]
    rng = np.random.default_rng(0)
    idx = rng.permutation(len(healthy))
    split = int(0.7 * len(healthy))
    h_train, h_val = healthy[idx[:split]], healthy[idx[split:]]
    mean, std = h_train.mean(0), h_train.std(0) + 1e-6
    model, best, ranking = search(
        (h_train - mean) / std,
        (h_val - mean) / std,
        (fault[: len(h_val)] - mean) / std,
        epochs=60,
        seed=0,
        quick=True,
    )
    assert best["auc"] > 0.9
    assert model.n_params > 0
    assert len(ranking) >= 4
