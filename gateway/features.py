"""Feature extraction, mirrors firmware/src/features.h."""
import numpy as np

def compute_features(x, fs):
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    rms = float(np.sqrt(np.mean(x ** 2)))
    peak = float(np.max(np.abs(x)))
    crest = peak / rms if rms > 1e-9 else 0.0
    var = np.mean(x ** 2)
    kurt = float(np.mean(x ** 4) / var ** 2) if var > 1e-12 else 0.0
    spec = np.abs(np.fft.rfft(x))
    spec[0] = 0
    dom = float(np.argmax(spec[: len(x) // 2]) * fs / len(x))
    return {"rms": rms, "peak": peak, "crest": crest, "kurtosis": kurt, "dom_freq": dom}
