import pytest

from gateway import rollout
from v4util import run_json


def test_bucket_is_deterministic_and_bounded():
    assert rollout.bucket("bench-01") == rollout.bucket("bench-01")
    for name in ("a", "bench-01", "lora-ff-01", "ümlaut"):
        assert 0 <= rollout.bucket(name) < 100


def test_percent_boundaries():
    for name in ("a", "b", "c", "d"):
        assert rollout.selected(name, 100) is True
        assert rollout.selected(name, 0) is False


def test_stage_mapping():
    assert [rollout.stage_percent(i) for i in range(4)] == [10, 50, 100, 100]


def test_cohort_is_stable_across_percentages():
    ids = [f"dev-{i}" for i in range(200)]
    ten = {d for d in ids if rollout.selected(d, 10)}
    fifty = {d for d in ids if rollout.selected(d, 50)}
    hundred = {d for d in ids if rollout.selected(d, 100)}
    assert ten <= fifty <= hundred
    assert 10 <= len(ten) <= 40
    assert 70 <= len(fifty) <= 130


@pytest.mark.parametrize("device_id", ["bench-01", "fan-25hz", "lora-001"])
def test_sil_matches_python(rollout_bin, device_id):
    data, rc, _ = run_json(rollout_bin, "--device-id", device_id, "--stage", 1)
    assert rc == 0
    assert data["bucket"] == rollout.bucket(device_id)
    assert data["percent"] == 50
    assert data["selected"] == rollout.selected(device_id, 50)
