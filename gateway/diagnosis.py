"""Bearing frequencies and rule-based diagnosis (mirror of v4/diagnosis.cpp)."""

from __future__ import annotations

import math
from dataclasses import dataclass

FAULTS = ("unknown", "imbalance", "misalignment", "looseness", "bearing")


@dataclass
class BearingGeometry:
    rpm: float = 0.0
    n_balls: int = 0
    ball_d_mm: float = 0.0
    pitch_d_mm: float = 0.0
    contact_angle_deg: float = 0.0


@dataclass
class BearingFreqs:
    bpfo: float = 0.0
    bpfi: float = 0.0
    bsf: float = 0.0
    ftf: float = 0.0
    valid: bool = False


@dataclass
class DiagnosisInput:
    rms: float = 0.0
    crest: float = 0.0
    kurtosis: float = 0.0
    dom_freq: float = 0.0
    envelope_freq: float = 0.0


def _near(value: float, target: float, tol: float) -> bool:
    return target > 0.0 and abs(value - target) <= tol


def bearing_frequencies(g: BearingGeometry) -> BearingFreqs:
    if (
        g.rpm <= 0
        or g.n_balls <= 0
        or g.ball_d_mm <= 0
        or g.pitch_d_mm <= 0
        or g.pitch_d_mm <= g.ball_d_mm
    ):
        return BearingFreqs()
    fr = g.rpm / 60.0
    ratio = (g.ball_d_mm / g.pitch_d_mm) * math.cos(math.radians(g.contact_angle_deg))
    return BearingFreqs(
        bpfo=(g.n_balls / 2.0) * fr * (1.0 - ratio),
        bpfi=(g.n_balls / 2.0) * fr * (1.0 + ratio),
        bsf=(g.pitch_d_mm / (2.0 * g.ball_d_mm)) * fr * (1.0 - ratio * ratio),
        ftf=(fr / 2.0) * (1.0 - ratio),
        valid=True,
    )


def diagnose(inp: DiagnosisInput, freqs: BearingFreqs, tol_hz: float = 5.0) -> str:
    if inp.kurtosis >= 4.0 and inp.envelope_freq > 0 and freqs.valid:
        if any(
            _near(inp.envelope_freq, f, tol_hz * 2)
            for f in (freqs.bpfo, freqs.bpfi, freqs.bsf, freqs.ftf)
        ):
            return "bearing"
    if inp.kurtosis >= 5.0 and freqs.valid:
        if any(
            _near(inp.dom_freq, f, tol_hz * 2)
            for f in (freqs.bpfo, freqs.bpfi, freqs.bsf, freqs.ftf)
        ):
            return "bearing"
    one_x = freqs.ftf * 2.0 if freqs.valid else 0.0
    if one_x > 0 and _near(inp.dom_freq, 2.0 * one_x, tol_hz * 2):
        return "misalignment"
    if one_x > 0 and _near(inp.dom_freq, one_x, tol_hz * 2) and inp.kurtosis < 4.5:
        return "imbalance"
    if inp.crest >= 5.0 or inp.kurtosis >= 6.0:
        return "looseness"
    return "unknown"
