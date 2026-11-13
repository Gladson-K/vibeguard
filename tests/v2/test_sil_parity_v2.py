import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from harness.features_v2 import compute_features_v2
from harness.profiles import load_profiles
from harness.signal import generate_window


def _binary():
    return os.environ.get("VG_SIL_BIN_V2") or shutil.which("vg-sil-v2") or "/usr/local/bin/vg-sil-v2"


@pytest.mark.skipif(not Path(_binary()).exists(), reason="v2 SIL binary not built")
def test_cpp_v2_features_match_python():
    hw, machines = load_profiles()
    sensor, machine = hw["adxl345"], machines["fan_25hz"]
    fs, n = int(sensor["fs"]), int(sensor["window"])
    rng = np.random.default_rng(21)
    windows = [generate_window(rng, fs, n, machine, sensor) for _ in range(10)]
    payload = "\n".join(",".join(f"{v:.6f}" for v in w) for w in windows) + "\n"

    proc = subprocess.run(
        [_binary(), "--fs", str(fs), "--n", str(n)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln]
    assert len(lines) == len(windows)

    for w, line in zip(windows, lines):
        py = compute_features_v2(w, fs)
        cpp = json.loads(line)
        assert cpp["rms"] == pytest.approx(py["rms"], rel=2e-3)
        assert cpp["peak"] == pytest.approx(py["peak"], rel=2e-3)
        assert cpp["crest"] == pytest.approx(py["crest"], rel=2e-3)
        assert cpp["kurtosis"] == pytest.approx(py["kurtosis"], rel=5e-3)
        assert cpp["centroid"] == pytest.approx(py["spectral_centroid"], rel=5e-3)
        for a, b in zip(cpp["bands"], py["bands"]):
            assert abs(a - b) < 0.05
        assert abs(cpp["dom_freq"] - py["envelope_dom_freq"]) <= 2.0 * fs / n
