"""Fake motor node: healthy 25 Hz rotation + harmonics; fault adds bearing-like impacts."""
import argparse, time
import numpy as np, requests
from features import compute_features

def window(rng, fs=1000, n=512, fault=False):
    t = np.arange(n) / fs
    x = 1.0 + 0.05 * np.sin(2 * np.pi * 25 * t) + 0.02 * np.sin(2 * np.pi * 50 * t) + rng.normal(0, 0.01, n)
    if fault:
        period = int(fs / 87)  # impact train ~87 Hz
        for i in range(0, n, period):
            k = np.arange(min(20, n - i))
            x[i:i + len(k)] += 0.35 * np.exp(-k / 4) * np.sin(2 * np.pi * 300 * k / fs)
        x += rng.normal(0, 0.02, n)
    return x

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8000/api/ingest")
    p.add_argument("--device", default="sim-01")
    p.add_argument("--fault-after", type=int, default=120)
    p.add_argument("--interval", type=float, default=0.3)
    p.add_argument("--count", type=int, default=400)
    a = p.parse_args()
    rng = np.random.default_rng(1)
    for i in range(a.count):
        f = compute_features(window(rng, fault=i >= a.fault_after), 1000)
        r = requests.post(a.url, json={"device_id": a.device, "fs": 1000, **f}, timeout=5).json()
        print(i, r)
        time.sleep(a.interval)

if __name__ == "__main__":
    main()
