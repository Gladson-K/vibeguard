import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from gateway.features import compute_features
from harness.signal import generate_window

ROOT = Path(__file__).resolve().parents[2]
PROFILES = {"noise_g": 0.01}
MACHINE = {"rpm": 1500, "bpfo_hz": 87}


def _binary():
    return os.environ.get("VG_SIL_BIN") or shutil.which("vg-sil-v1") or "/usr/local/bin/vg-sil-v1"


@pytest.mark.skipif(not Path(_binary()).exists(), reason="SIL binary not built")
def test_cpp_dsp_matches_python():
    rng = np.random.default_rng(7)
    windows = [generate_window(rng, 1000, 512, MACHINE, PROFILES) for _ in range(20)]
    payload = "\n".join(",".join(f"{v:.6f}" for v in w) for w in windows) + "\n"

    proc = subprocess.run(
        [_binary(), "--fs", "1000", "--n", "512"],
        input=payload,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln]
    assert len(lines) == len(windows)

    for w, line in zip(windows, lines):
        py = compute_features(w, 1000)
        cpp = json.loads(line)
        assert cpp["rms"] == pytest.approx(py["rms"], rel=2e-3)
        assert cpp["peak"] == pytest.approx(py["peak"], rel=2e-3)
        assert cpp["crest"] == pytest.approx(py["crest"], rel=2e-3)
        assert cpp["kurtosis"] == pytest.approx(py["kurtosis"], rel=2e-3)
        assert abs(cpp["dom_freq"] - py["dom_freq"]) <= 2.5
