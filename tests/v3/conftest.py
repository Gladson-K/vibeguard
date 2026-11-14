import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from v3util import bin_path  # noqa: E402


@pytest.fixture(scope="session")
def power_bin():
    return bin_path("VG_SIL_POWER", "/usr/local/bin/vg-sil-v3_power")


@pytest.fixture(scope="session")
def ota_bin():
    return bin_path("VG_SIL_OTA", "/usr/local/bin/vg-sil-v3_ota")


@pytest.fixture(scope="session")
def prodtest_bin():
    return bin_path("VG_SIL_PRODTEST", "/usr/local/bin/vg-sil-v3_prodtest")


@pytest.fixture(scope="session")
def state_bin():
    return bin_path("VG_SIL_STATE", "/usr/local/bin/vg-sil-v3_state")
