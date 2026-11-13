import os
from pathlib import Path

import pytest

from harness.run_scenario import run_scenario

URL = os.environ.get("GATEWAY_URL")
SCENARIOS = Path(__file__).resolve().parents[2] / "harness" / "scenarios"

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.timeout(180),
    pytest.mark.skipif(not URL, reason="GATEWAY_URL not set (needs docker gateway)"),
]


@pytest.mark.parametrize(
    "name",
    ["v1_healthy", "v1_bearing", "v1_imbalance", "v1_looseness"],
)
def test_python_node_scenario(name):
    _, failures = run_scenario(
        SCENARIOS / f"{name}.yaml",
        URL,
        report_dir=os.environ.get("VG_REPORT_DIR"),
        verbose=False,
    )
    assert not failures, f"{name} failed: {failures}"


def test_sil_node_scenario():
    sil = os.environ.get("VG_SIL_BIN")
    if not sil or not Path(sil).exists():
        pytest.skip("SIL binary unavailable")
    _, failures = run_scenario(
        SCENARIOS / "v1_bearing_sil.yaml",
        URL,
        source="sil",
        sil_binary=sil,
        report_dir=os.environ.get("VG_REPORT_DIR"),
        verbose=False,
    )
    assert not failures, f"v1_bearing_sil failed: {failures}"
