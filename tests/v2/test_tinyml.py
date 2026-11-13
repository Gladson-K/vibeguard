import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "models" / "tinyml" / "model.json"


def _bench():
    return os.environ.get("VG_SIL_BENCH") or shutil.which("vg-sil-bench") or "/usr/local/bin/vg-sil-bench"


def test_artifact_shape_and_auc():
    assert MODEL.exists(), "run python -m tools.train_autoencoder"
    art = json.loads(MODEL.read_text())
    assert art["in_dim"] == 24
    assert len(art["layers"]) == 4
    assert art["float_auc"] >= 0.9
    assert art["int8_auc"] >= 0.9
    assert art["float_auc"] - art["int8_auc"] < 0.02  # int8 within 2% of float
    assert art["arena_bytes"] < 60 * 1024


def test_inference_latency():
    if not Path(_bench()).exists():
        pytest.skip("bench binary not built")
    out = subprocess.run([_bench(), "--iters", "5000"], capture_output=True, text=True, check=True)
    us = json.loads(out.stdout)["us_per_infer"]
    assert us < 20000, f"inference {us} us exceeds 20 ms budget"


def test_generated_header_present():
    header = ROOT / "firmware" / "src" / "vg_core" / "model_data.h"
    assert header.exists()
    text = header.read_text()
    assert "VG_MODEL" in text and "VG_LAYERS" in text
