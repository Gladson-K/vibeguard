"""Linear-trend RUL estimate (mirror of vg_core/v4/rul.cpp)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RulEstimate:
    slope_per_day: float = 0.0
    current: float = 0.0
    rul_days: float = 0.0
    valid: bool = False


def estimate(
    values: list[float],
    times_s: list[float],
    threshold: float,
    min_slope_per_s: float = 1e-9,
) -> RulEstimate:
    n = len(values)
    if n < 3 or len(times_s) < n:
        return RulEstimate()
    t_mean = sum(times_s[:n]) / n
    v_mean = sum(values) / n
    num = sum((t - t_mean) * (v - v_mean) for t, v in zip(times_s[:n], values))
    den = sum((t - t_mean) ** 2 for t in times_s[:n])
    if den <= 0:
        return RulEstimate()
    slope = num / den
    est = RulEstimate(current=values[-1], slope_per_day=slope * 86400.0)
    if slope <= min_slope_per_s:
        return est
    est.rul_days = max(0.0, (threshold - est.current) / (slope * 86400.0))
    est.valid = True
    return est
