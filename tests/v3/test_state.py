import pytest

from v3util import run_json


@pytest.mark.parametrize(
    "state,flags,expected",
    [
        ("boot", {}, "sample"),
        ("boot", {"--provisioned": 0}, "provision"),
        ("provision", {"--provisioned": 1}, "sample"),
        ("sample", {"--window-ready": 1}, "infer"),
        ("sample", {"--window-ready": 0}, "sample"),
        ("infer", {"--ota-requested": 1}, "ota"),
        ("infer", {"--ota-requested": 0}, "tx"),
        ("tx", {"--tx-done": 1}, "sleep"),
        ("tx", {"--tx-done": 1, "--ota-requested": 1}, "ota"),
        ("ota", {"--ota-done": 1}, "sleep"),
        ("sleep", {"--woke": 1}, "sample"),
        ("sleep", {"--woke": 0}, "sleep"),
        ("sample", {"--fault": 1}, "fault"),
        ("fault", {"--fault": 0}, "boot"),
    ],
)
def test_transitions(state_bin, state, flags, expected):
    args = ["--state", state]
    for key, value in flags.items():
        args.extend([key, value])
    data, rc, _ = run_json(state_bin, *args)
    assert rc == 0
    assert data["state"] == expected
