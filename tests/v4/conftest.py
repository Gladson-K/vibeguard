import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from v4util import bin_path  # noqa: E402


@pytest.fixture(scope="session")
def codec_bin():
    return bin_path("VG_SIL_V4_CODEC", "/usr/local/bin/vg-sil-v4_codec")


@pytest.fixture(scope="session")
def rollout_bin():
    return bin_path("VG_SIL_V4_ROLLOUT", "/usr/local/bin/vg-sil-v4_rollout")


@pytest.fixture(scope="session")
def diag_bin():
    return bin_path("VG_SIL_V4_DIAG", "/usr/local/bin/vg-sil-v4_diag")


@pytest.fixture(scope="session")
def rul_bin():
    return bin_path("VG_SIL_V4_RUL", "/usr/local/bin/vg-sil-v4_rul")


@pytest.fixture(scope="session")
def drift_bin():
    return bin_path("VG_SIL_V4_DRIFT", "/usr/local/bin/vg-sil-v4_drift")
