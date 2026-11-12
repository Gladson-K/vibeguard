"""Scenario metrics: recall, false alarms, detection delay, latency."""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class ScenarioMetrics:
    total_windows: int
    fault_after: int | None
    baseline_windows: int
    false_alarms: int
    detected: bool
    detection_delay: int | None
    fault_window_recall: float
    max_latency_ms: float
    statuses: list[str]

    def as_dict(self) -> dict:
        d = asdict(self)
        d.pop("statuses")
        return d


def evaluate(
    statuses: list[str],
    latencies_ms: list[float],
    fault_after: int | None,
    baseline_windows: int,
) -> ScenarioMetrics:
    healthy_end = fault_after if fault_after is not None else len(statuses)
    # Post-learning, pre-fault healthy region is where false alarms are counted.
    healthy_region = statuses[baseline_windows:healthy_end]
    false_alarms = sum(1 for s in healthy_region if s == "anomaly")

    detected = False
    detection_delay = None
    recall = 0.0
    if fault_after is not None:
        fault_region = statuses[fault_after:]
        anomalies = [i for i, s in enumerate(fault_region) if s == "anomaly"]
        if anomalies:
            detected = True
            detection_delay = anomalies[0]
        recall = len(anomalies) / len(fault_region) if fault_region else 0.0

    return ScenarioMetrics(
        total_windows=len(statuses),
        fault_after=fault_after,
        baseline_windows=baseline_windows,
        false_alarms=false_alarms,
        detected=detected,
        detection_delay=detection_delay,
        fault_window_recall=round(recall, 4),
        max_latency_ms=round(max(latencies_ms) if latencies_ms else 0.0, 3),
        statuses=statuses,
    )


def check_expectations(m: ScenarioMetrics, expect: dict) -> list[str]:
    """Return a list of failure messages (empty == pass)."""
    failures = []
    if "min_recall" in expect:
        recall = 1.0 if m.detected else 0.0
        if recall < float(expect["min_recall"]):
            failures.append(f"recall {recall:.2f} < {expect['min_recall']}")
    if "max_false_alarms" in expect and m.false_alarms > int(expect["max_false_alarms"]):
        failures.append(f"false alarms {m.false_alarms} > {expect['max_false_alarms']}")
    if "max_detection_delay" in expect:
        if m.detection_delay is None:
            failures.append("fault never detected")
        elif m.detection_delay > int(expect["max_detection_delay"]):
            failures.append(
                f"detection delay {m.detection_delay} > {expect['max_detection_delay']}"
            )
    if "max_latency_ms" in expect and m.max_latency_ms > float(expect["max_latency_ms"]):
        failures.append(f"latency {m.max_latency_ms:.1f}ms > {expect['max_latency_ms']}ms")
    return failures
