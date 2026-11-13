"""Per-device baseline learners.

BaselineDetector: Welford mean/var, z-score alarm with persistence (V1).
ModelScoreDetector: percentile-calibrated threshold on a TinyML reconstruction
score (V2). Higher score == more anomalous.
"""
import math

FEATURES = ("rms", "peak", "crest", "kurtosis", "dom_freq")
MIN_STD = {"rms": 0.002, "peak": 0.01, "crest": 0.15, "kurtosis": 0.15, "dom_freq": 1.5}


class BaselineDetector:
    def __init__(self, learn_windows=60, z_threshold=4.0, persistence=3):
        self.n_learn, self.z_thr, self.persist = learn_windows, z_threshold, persistence
        self.n = 0
        self.mean = {k: 0.0 for k in FEATURES}
        self.m2 = {k: 0.0 for k in FEATURES}
        self.streak = 0

    @property
    def learning(self):
        return self.n < self.n_learn

    def _std(self, k):
        s = math.sqrt(self.m2[k] / (self.n - 1)) if self.n > 1 else 0.0
        return max(s, MIN_STD[k])

    def update(self, feats):
        """Returns dict(status, score, worst_feature)."""
        if self.learning:
            self.n += 1
            for k in FEATURES:
                d = feats[k] - self.mean[k]
                self.mean[k] += d / self.n
                self.m2[k] += d * (feats[k] - self.mean[k])
            return {"status": "learning", "score": 0.0, "worst": None}
        z = {k: abs(feats[k] - self.mean[k]) / self._std(k) for k in FEATURES}
        worst = max(z, key=z.get)
        score = z[worst]
        self.streak = self.streak + 1 if score > self.z_thr else 0
        status = "anomaly" if self.streak >= self.persist else ("warning" if score > self.z_thr else "ok")
        return {"status": status, "score": round(score, 2), "worst": worst}


class ModelScoreDetector:
    """Calibrate a threshold from healthy model scores, then flag drift."""

    def __init__(self, calib_windows=60, percentile=99.5, persistence=3, floor=0.0):
        self.n_calib = calib_windows
        self.percentile = percentile
        self.persist = persistence
        self.floor = floor
        self.scores = []
        self.threshold = None
        self.streak = 0
        self.n = 0

    @property
    def learning(self):
        return self.threshold is None

    def _percentile(self):
        xs = sorted(self.scores)
        if not xs:
            return 0.0
        k = min(len(xs) - 1, max(0, int(round(self.percentile / 100.0 * (len(xs) - 1)))))
        return xs[k]

    def update(self, score):
        score = float(score)
        if self.learning:
            self.scores.append(score)
            self.n += 1
            if self.n >= self.n_calib:
                self.threshold = max(self._percentile(), self.floor)
            return {"status": "learning", "score": 0.0, "threshold": None, "worst": None}
        ratio = score / self.threshold if self.threshold > 1e-12 else 0.0
        self.streak = self.streak + 1 if ratio > 1.0 else 0
        status = "anomaly" if self.streak >= self.persist else ("warning" if ratio > 1.0 else "ok")
        return {"status": status, "score": round(ratio, 3), "threshold": self.threshold, "worst": "model_score"}
