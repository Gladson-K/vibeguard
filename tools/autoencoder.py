"""Minimal numpy dense autoencoder (Adam) used for the NAS search.

No deep-learning framework required, so the default Docker profile stays light.
"""
from __future__ import annotations

import numpy as np

ACT_LINEAR, ACT_TANH, ACT_RELU = 0, 1, 2


def _act(z: np.ndarray, kind: int) -> np.ndarray:
    if kind == ACT_TANH:
        return np.tanh(z)
    if kind == ACT_RELU:
        return np.maximum(z, 0.0)
    return z


def _dact(a: np.ndarray, kind: int) -> np.ndarray:
    if kind == ACT_TANH:
        return 1.0 - a * a
    if kind == ACT_RELU:
        return (a > 0).astype(a.dtype)
    return np.ones_like(a)


class Autoencoder:
    def __init__(self, dims: list[int], acts: list[int], seed: int = 0):
        rng = np.random.default_rng(seed)
        self.W, self.b, self.acts = [], [], acts
        for i in range(len(dims) - 1):
            fan_in, fan_out = dims[i], dims[i + 1]
            scale = np.sqrt(2.0 / fan_in) if acts[i] == ACT_RELU else np.sqrt(1.0 / fan_in)
            self.W.append(rng.normal(0.0, scale, (fan_in, fan_out)))
            self.b.append(np.zeros(fan_out))

    @property
    def n_params(self) -> int:
        return sum(w.size for w in self.W) + sum(b.size for b in self.b)

    def forward(self, X: np.ndarray, cache: bool = False):
        a = X
        acts, zs = [a], []
        for W, b, kind in zip(self.W, self.b, self.acts):
            z = a @ W + b
            zs.append(z)
            a = _act(z, kind)
            acts.append(a)
        return (a, acts, zs) if cache else a

    def _grads(self, X: np.ndarray):
        m = X.shape[0]
        _, acts, _ = self.forward(X, cache=True)
        delta = 2.0 * (acts[-1] - X) / m
        gW = [None] * len(self.W)
        gb = [None] * len(self.b)
        for l in reversed(range(len(self.W))):
            gW[l] = acts[l].T @ delta
            gb[l] = delta.sum(axis=0)
            if l > 0:
                delta = (delta @ self.W[l].T) * _dact(acts[l], self.acts[l - 1])
        return gW, gb

    def fit(self, X: np.ndarray, epochs: int = 200, lr: float = 0.01, batch: int = 64, seed: int = 0):
        rng = np.random.default_rng(seed)
        mW = [np.zeros_like(w) for w in self.W]
        vW = [np.zeros_like(w) for w in self.W]
        mb = [np.zeros_like(b) for b in self.b]
        vb = [np.zeros_like(b) for b in self.b]
        b1, b2, eps, t = 0.9, 0.999, 1e-8, 0
        N = X.shape[0]
        for _ in range(epochs):
            idx = rng.permutation(N)
            for s in range(0, N, batch):
                gW, gb = self._grads(X[idx[s:s + batch]])
                t += 1
                for l in range(len(self.W)):
                    mW[l] = b1 * mW[l] + (1 - b1) * gW[l]
                    vW[l] = b2 * vW[l] + (1 - b2) * gW[l] ** 2
                    self.W[l] -= lr * (mW[l] / (1 - b1 ** t)) / (np.sqrt(vW[l] / (1 - b2 ** t)) + eps)
                    mb[l] = b1 * mb[l] + (1 - b1) * gb[l]
                    vb[l] = b2 * vb[l] + (1 - b2) * gb[l] ** 2
                    self.b[l] -= lr * (mb[l] / (1 - b1 ** t)) / (np.sqrt(vb[l] / (1 - b2 ** t)) + eps)
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        return np.mean((self.forward(X) - X) ** 2, axis=1)
