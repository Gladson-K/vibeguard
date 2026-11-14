import pytest

from v3util import run_json

BASE = {
    "--device-id": "node-01",
    "--sensor": "adxl355",
    "--firmware": "3.0.0",
    "--rail-3v3": 1,
    "--rail-1v8": 1,
    "--flash": 1,
    "--whoami": 1,
    "--selftest": 1,
}


def _args(**overrides):
    values = dict(BASE)
    values.update(overrides)
    out = []
    for key, value in values.items():
        out.extend([key, value])
    return out


def test_good_board_passes(prodtest_bin):
    data, rc, _ = run_json(prodtest_bin, *_args())
    assert rc == 0
    assert data["pass"] is True
    assert data["reason"] == "ok"
    assert data["label"] == "VG3-node-01-adxl355-3.0.0-PASS"


@pytest.mark.parametrize(
    "flag,reason",
    [
        ("--rail-3v3", "rail_3v3"),
        ("--rail-1v8", "rail_1v8"),
        ("--flash", "flash"),
        ("--whoami", "whoami"),
        ("--selftest", "selftest"),
    ],
)
def test_each_failure_is_reported(prodtest_bin, flag, reason):
    data, rc, _ = run_json(prodtest_bin, *_args(**{flag: 0}))
    assert rc == 1
    assert data["pass"] is False
    assert data["reason"] == reason
    assert data["label"].endswith(f"FAIL-{reason}")


def test_first_failure_wins(prodtest_bin):
    data, _, _ = run_json(
        prodtest_bin, *_args(**{"--rail-3v3": 0, "--selftest": 0})
    )
    assert data["reason"] == "rail_3v3"
