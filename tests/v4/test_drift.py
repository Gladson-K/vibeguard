import pytest

from gateway import drift
from v4util import run_json


def test_identical_distributions_do_not_drift():
    ref = [float(i) for i in range(20)]
    rep = drift.report(ref, list(ref))
    assert rep.psi == pytest.approx(0.0)
    assert rep.ks == pytest.approx(0.0)
    assert rep.drift is False


def test_shifted_distribution_drifts():
    ref = [float(i) for i in range(100)]
    cur = [float(i + 60) for i in range(100)]
    rep = drift.report(ref, cur)
    assert rep.psi > 0.2
    assert rep.ks > 0.5
    assert rep.ks_pvalue < 0.01
    assert rep.drift is True


def test_empty_inputs_are_safe():
    rep = drift.report([], [1.0])
    assert rep.drift is False and rep.ks_pvalue == 1.0


def test_sil_matches_python(drift_bin):
    ref = [float(i) for i in range(50)]
    cur = [float(i) for i in range(50)]
    rep = drift.report(ref, cur)
    data, rc, _ = run_json(
        drift_bin,
        "--reference", ",".join(map(str, ref)),
        "--current", ",".join(map(str, cur)),
    )
    assert rc == 0
    assert data["psi"] == pytest.approx(rep.psi, abs=1e-4)
    assert data["ks"] == pytest.approx(rep.ks, abs=1e-4)
    assert data["drift"] == rep.drift
