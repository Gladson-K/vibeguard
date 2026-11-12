"""Synthetic machine vibration generator.

Produces raw acceleration windows (g) for a machine profile with an optional
seed fault. This is the hardware-independent signal source used by both the
Python node and the SIL (software-in-the-loop) firmware binaries.
"""
from __future__ import annotations

import numpy as np


def generate_window(
    rng: np.random.Generator,
    fs: int,
    n: int,
    machine: dict,
    sensor: dict,
    fault: dict | None = None,
) -> np.ndarray:
    t = np.arange(n) / fs
    f_rot = float(machine.get("rpm", 1500)) / 60.0
    noise = float(sensor.get("noise_g", 0.01))

    x = 1.0 + 0.05 * np.sin(2 * np.pi * f_rot * t) + 0.02 * np.sin(2 * np.pi * 2 * f_rot * t)
    x = x + rng.normal(0.0, noise, n)

    if fault:
        ftype = fault.get("type", "bearing")
        amp = float(fault.get("amplitude", 0.35))
        if ftype == "imbalance":
            x = x + amp * np.sin(2 * np.pi * f_rot * t)
        elif ftype == "looseness":
            for h in (1, 2, 3, 4):
                x = x + amp / h * np.sin(2 * np.pi * h * f_rot * t + h)
            x = x + rng.normal(0.0, amp * 0.1, n)
        elif ftype == "belt":
            x = x + amp * rng.normal(0.0, 1.0, n) * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * t))
            x = x + amp * 0.5 * np.sin(2 * np.pi * (f_rot / 3.0) * t)
        elif ftype in ("bearing", "impact"):
            bpfo = float(fault.get("freq", machine.get("bpfo_hz", 87)))
            period = max(1, int(fs / bpfo))
            for i in range(0, n, period):
                k = np.arange(min(20, n - i))
                x[i:i + len(k)] += amp * np.exp(-k / 4.0) * np.sin(2 * np.pi * 300.0 * k / fs)
            x = x + rng.normal(0.0, amp * 0.05, n)
        else:
            raise ValueError(f"unknown fault type: {ftype}")
    return x


def window_is_fault(index: int, fault_after: int | None) -> bool:
    return fault_after is not None and index >= fault_after
