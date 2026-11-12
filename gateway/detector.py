"""Per-device baseline learner: Welford mean/var, z-score alarm with persistence."""
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
