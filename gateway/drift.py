"""PSI + two-sample KS drift detector (mirror of vg_core/v4/drift.cpp)."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class DriftReport:
    psi: float = 0.0
    ks: float = 0.0
    ks_pvalue: float = 1.0
    drift: bool = False


def report(
    reference: list[float],
    current: list[float],
    bins: int = 10,
    psi_threshold: float = 0.2,
    alpha: float = 0.05,
) -> DriftReport:
    if not reference or not current or bins < 1:
        return DriftReport()

    lo = min(min(reference), min(current))
    hi = max(max(reference), max(current))
    width = hi - lo

    def bin_of(value: float) -> int:
        if width <= 0:
            return 0
        b = int((value - lo) / width * bins)
        return 0 if b < 0 else bins - 1 if b >= bins else b

    rc = [0.0] * bins
    cc = [0.0] * bins
    for v in reference:
        rc[bin_of(v)] += 1.0
    for v in current:
        cc[bin_of(v)] += 1.0

    eps = 1e-6
    psi = 0.0
    for p, q in zip(rc, cc):
        p = max(p / len(reference), eps)
        q = max(q / len(current), eps)
        psi += (q - p) * math.log(q / p)

    a = sorted(reference)
    b = sorted(current)
    i = j = 0
    d = 0.0
    while i < len(a) or j < len(b):
        v = a[i] if j >= len(b) or (i < len(a) and a[i] <= b[j]) else b[j]
        while i < len(a) and a[i] <= v:
            i += 1
        while j < len(b) and b[j] <= v:
            j += 1
        d = max(d, abs(i / len(a) - j / len(b)))

    ne = len(a) * len(b) / (len(a) + len(b))
    lam = (math.sqrt(ne) + 0.12 + 0.11 / math.sqrt(ne)) * d
    pvalue = 1.0
    if lam > 0:
        pvalue = sum(
            2.0 * (1 if k % 2 else -1) * math.exp(-2.0 * k * k * lam * lam)
            for k in range(1, 101)
        )
        pvalue = min(1.0, max(0.0, pvalue))

    return DriftReport(
        psi=psi,
        ks=d,
        ks_pvalue=pvalue,
        drift=psi >= psi_threshold or pvalue < alpha,
    )
