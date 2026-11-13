"""Software-in-the-loop source: pipes raw windows through a host-compiled firmware binary.

This exercises the real C/C++ DSP (and V2 int8 model) with zero hardware.
Protocol: one comma-separated window per line in, one JSON feature frame per line out.
"""
from __future__ import annotations

import json
import os
import subprocess

import numpy as np

from harness.signal import generate_window
from harness.sources.base import FrameSource

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SilSource(FrameSource):
    def __init__(self, scenario: dict, binary: str):
        self.scenario = scenario
        self.binary = binary

    def _windows(self):
        s = self.scenario
        sensor = s["sensor_profile"]
        machine = s["machine_profile"]
        fs = int(sensor["fs"])
        n = int(sensor["window"])
        rng = np.random.default_rng(int(s.get("seed", 1)))
        total = int(s.get("total_windows", 400))
        fault_after = s.get("fault_after")
        fault = s.get("fault")
        for i in range(total):
            active_fault = fault if (fault_after is not None and i >= fault_after) else None
            yield i, fs, generate_window(rng, fs, n, machine, sensor, active_fault)

    def frames(self):
        s = self.scenario
        sensor = s["sensor_profile"]
        fs = int(sensor["fs"])
        n = int(sensor["window"])
        proc = subprocess.Popen(
            [self.binary, "--fs", str(fs), "--n", str(n)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            for i, _fs, x in self._windows():
                line = ",".join(f"{v:.6f}" for v in x)
                proc.stdin.write(line + "\n")
                proc.stdin.flush()
                out = proc.stdout.readline()
                if not out:
                    err = proc.stderr.read()
                    raise RuntimeError(f"SIL binary died: {err}")
                feats = json.loads(out)
                frame = {
                    "device_id": s["device_id"],
                    "fs": fs,
                    "ts": float(i),
                    "sensor": s["sensor"],
                    "model_score": feats.pop("model_score", None),
                    "model_version": feats.pop("model_version", None),
                    **feats,
                }
                if frame["model_score"] is None:
                    frame.pop("model_score")
                    frame.pop("model_version")
                yield frame
        finally:
            try:
                proc.stdin.close()
            except Exception:  # noqa: BLE001
                pass
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
