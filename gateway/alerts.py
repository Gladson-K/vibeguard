"""Alarm state machine with hysteresis and maintenance suppression.

The detector already requires persistence before emitting `anomaly`; this layer
adds warning/critical deduplication and a clear-debounce so a single healthy
window does not flap an alert closed. Rules are intentionally small and
testable; thresholds can be overridden by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SEVERITY = {"ok": 0, "warning": 1, "critical": 2}
STATUS_LEVEL = {"learning": "ok", "ok": "ok", "warning": "warning", "anomaly": "critical"}


@dataclass
class AlertEvent:
    level: str
    kind: str
    message: str


@dataclass
class _State:
    level: str = "ok"
    clear_streak: int = 0
    suppressed: int = 0


@dataclass
class AlertEngine:
    clear_after: int = 3
    states: dict[str, _State] = field(default_factory=dict)

    def evaluate(
        self,
        device_id: str,
        status: str,
        *,
        maintenance: bool = False,
        detail: str = "",
    ) -> list[AlertEvent]:
        st = self.states.setdefault(device_id, _State())
        target = STATUS_LEVEL.get(status, "ok")

        if maintenance:
            st.suppressed += 1
            return []

        if target == "ok":
            if st.level == "ok":
                st.clear_streak = 0
                return []
            st.clear_streak += 1
            if st.clear_streak >= self.clear_after:
                previous = st.level
                st.level = "ok"
                st.clear_streak = 0
                return [
                    AlertEvent(
                        "ok",
                        "recovery",
                        f"{device_id} recovered from {previous}",
                    )
                ]
            return []

        st.clear_streak = 0
        if SEVERITY[target] > SEVERITY[st.level]:
            previous = st.level
            st.level = target
            suffix = f" ({detail})" if detail else ""
            return [
                AlertEvent(
                    target,
                    "anomaly" if target == "critical" else "warning",
                    f"{device_id} {previous} -> {target}{suffix}",
                )
            ]
        return []

    def reset(self, device_id: str | None = None) -> None:
        if device_id is None:
            self.states.clear()
        else:
            self.states.pop(device_id, None)
