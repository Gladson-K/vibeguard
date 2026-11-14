import pytest

from gateway import diagnosis as d
from v4util import run_json

GEOM = d.BearingGeometry(rpm=1500, n_balls=8, ball_d_mm=7.94, pitch_d_mm=39.04)


def test_bearing_frequencies_ordering():
    f = d.bearing_frequencies(GEOM)
    assert f.valid
    assert 0 < f.ftf < f.bpfo < f.bpfi
    assert f.bsf > 0


def test_invalid_geometry():
    assert d.bearing_frequencies(d.BearingGeometry(rpm=0)).valid is False
    assert d.bearing_frequencies(
        d.BearingGeometry(rpm=1000, n_balls=8, ball_d_mm=40, pitch_d_mm=39)
    ).valid is False


def test_bearing_rule_via_envelope():
    f = d.bearing_frequencies(GEOM)
    out = d.diagnose(
        d.DiagnosisInput(kurtosis=6.0, envelope_freq=f.bpfo), f
    )
    assert out == "bearing"


def test_imbalance_and_misalignment_rules():
    f = d.bearing_frequencies(GEOM)
    one_x = f.ftf * 2.0
    assert d.diagnose(d.DiagnosisInput(dom_freq=one_x, kurtosis=3.0), f) == "imbalance"
    assert (
        d.diagnose(d.DiagnosisInput(dom_freq=2 * one_x, kurtosis=3.0), f)
        == "misalignment"
    )


def test_looseness_and_unknown():
    f = d.bearing_frequencies(GEOM)
    assert d.diagnose(d.DiagnosisInput(crest=6.0), f) == "looseness"
    assert d.diagnose(d.DiagnosisInput(rms=0.1, crest=3.0, kurtosis=2.9), f) == "unknown"


def test_sil_matches_python(diag_bin):
    f = d.bearing_frequencies(GEOM)
    data, rc, _ = run_json(
        diag_bin,
        "--rpm", 1500,
        "--n-balls", 8,
        "--ball-d", 7.94,
        "--pitch-d", 39.04,
        "--kurtosis", 6.0,
        "--envelope-freq", f.bpfo,
    )
    assert rc == 0
    assert data["valid"] is True
    assert data["bpfo"] == pytest.approx(f.bpfo, abs=0.1)
    assert data["bpfi"] == pytest.approx(f.bpfi, abs=0.1)
    assert data["ftf"] == pytest.approx(f.ftf, abs=0.05)
    assert data["class"] == "bearing"
