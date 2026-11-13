import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session", autouse=True)
def model_artifact():
    model = ROOT / "models" / "tinyml" / "model.json"
    header = ROOT / "firmware" / "src" / "vg_core" / "model_data.h"
    if not model.exists() or not header.exists():
        subprocess.run(
            [sys.executable, "-m", "tools.train_autoencoder", "--quick"],
            cwd=ROOT,
            check=True,
        )
    return model
