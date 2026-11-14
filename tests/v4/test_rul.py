import pytest

from gateway import rul
from v4util import run_json

DAY = 86400.0


def test_linear_trend_rul():
    values = [0.10, 0.12, 0.14, 0.16]
    times = [0, DAY, 2 * DAY, 3 * DAY]
    est = rul.estimate(values, times, threshold=0.30)
    assert est.valid
    assert est.slope_per_day == pytest.approx(0.02, rel=1e-6)
    assert est.rul_days == pytest.approx((0.30 - 0.16) / 0.02, rel=1e-6)


def test_flat_or_decreasing_has_no_rul():
    assert rul.estimate([0.1, 0.1, 0.1], [0, DAY, 2 * DAY], 0.5).valid is False
    assert rul.estimate([0.3, 0.2, 0.1], [0, DAY, 2 * DAY], 0.5).valid is False


def test_too_few_samples():
    assert rul.estimate([0.1, 0.2], [0, DAY], 0.5).valid is False


def test_already_over_threshold_clamps_to_zero():
    est = rul.estimate([0.1, 0.4, 0.7], [0, DAY, 2 * DAY], 0.5)
    assert est.valid and est.rul_days == 0.0


def test_sil_matches_python(rul_bin):
    values = [0.1, 0.2, 0.3]
    times = [0, 86400, 172800]
    est = rul.estimate(values, times, 0.5)
    data, rc, _ = run_json(
        rul_bin,
        "--values", ",".join(map(str, values)),
        "--times", ",".join(map(str, times)),
        "--threshold", 0.5,
    )
    assert rc == 0 and data["valid"] is True
    assert data["slope_per_day"] == pytest.approx(est.slope_per_day, rel=1e-5)
    assert data["rul_days"] == pytest.approx(est.rul_days, rel=1e-5)
