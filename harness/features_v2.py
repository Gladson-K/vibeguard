"""V2 spectral feature extraction, mirrors firmware/src/vg_core/features_v2.cpp.

Feature vector (24 dims):
  [rms, peak, crest, kurtosis, spectral_centroid,
   15 log-spaced band log-energies,
   envelope_rms, envelope_peak, envelope_kurtosis, envelope_dom_freq]
"""
from __future__ import annotations

import numpy as np

N_BANDS = 15
FEATURE_DIM = 5 + N_BANDS + 4


def _kurtosis(x: np.ndarray) -> float:
    var = float(np.mean(x ** 2))
    if var <= 1e-12:
        return 0.0
    return float(np.mean(x ** 4) / (var * var))


def _moving_average(x: np.ndarray, w: int) -> np.ndarray:
    pad = w // 2
    xp = np.pad(x, (pad, w - 1 - pad), mode="constant")
    return np.convolve(xp, np.ones(w) / w, mode="valid")


def compute_features_v2(x: np.ndarray, fs: float) -> dict:
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    n = len(x)

    rms = float(np.sqrt(np.mean(x ** 2)))
    peak = float(np.max(np.abs(x)))
    crest = peak / rms if rms > 1e-9 else 0.0
    kurt = _kurtosis(x)

    spec = np.fft.rfft(x)
    mag = np.abs(spec)
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    mag[0] = 0.0
    centroid = float(np.sum(freqs * mag) / np.sum(mag)) if np.sum(mag) > 1e-12 else 0.0

    fmin, fmax = 20.0, fs / 2.0
    edges = np.geomspace(fmin, fmax, N_BANDS + 1)
    power = mag ** 2
    bands = []
    for k in range(N_BANDS):
        lo, hi = edges[k], edges[k + 1]
        mask = (freqs >= lo) & ((freqs < hi) if k < N_BANDS - 1 else (freqs <= hi))
        energy = float(np.sum(power[mask]))
        bands.append(float(np.log(energy + 1e-12)))

    w = max(1, n // 256)
    env = _moving_average(np.abs(x), w)
    env = env - env.mean()
    env_rms = float(np.sqrt(np.mean(env ** 2)))
    env_peak = float(np.max(np.abs(env)))
    env_kurt = _kurtosis(env)
    espec = np.abs(np.fft.rfft(env))
    espec[0] = 0.0
    efreqs = np.fft.rfftfreq(n, d=1.0 / fs)
    env_dom = float(efreqs[int(np.argmax(espec))]) if np.max(espec) > 1e-12 else 0.0

    vector = [rms, peak, crest, kurt, centroid] + bands + [env_rms, env_peak, env_kurt, env_dom]
    return {
        "rms": rms,
        "peak": peak,
        "crest": crest,
        "kurtosis": kurt,
        "dom_freq": env_dom,
        "spectral_centroid": centroid,
        "bands": bands,
        "envelope_dom_freq": env_dom,
        "feature_vector": vector,
    }
