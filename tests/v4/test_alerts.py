from gateway.alerts import AlertEngine


def test_warning_then_critical_deduplicated():
    e = AlertEngine()
    assert [a.level for a in e.evaluate("d", "warning")] == ["warning"]
    assert e.evaluate("d", "warning") == []
    assert [a.level for a in e.evaluate("d", "anomaly")] == ["critical"]
    assert e.evaluate("d", "anomaly") == []


def test_critical_does_not_downgrade_to_warning():
    e = AlertEngine()
    e.evaluate("d", "anomaly")
    assert e.evaluate("d", "warning") == []
    assert e.states["d"].level == "critical"


def test_clear_requires_consecutive_ok_windows():
    e = AlertEngine(clear_after=3)
    e.evaluate("d", "warning")
    assert e.evaluate("d", "ok") == []
    assert e.evaluate("d", "warning") == []
    assert e.evaluate("d", "ok") == []
    assert e.evaluate("d", "ok") == []
    assert [a.kind for a in e.evaluate("d", "ok")] == ["recovery"]
    assert e.states["d"].level == "ok"


def test_maintenance_suppresses_alerts():
    e = AlertEngine()
    assert e.evaluate("d", "anomaly", maintenance=True) == []
    assert e.states["d"].level == "ok"
    assert [a.level for a in e.evaluate("d", "anomaly")] == ["critical"]
