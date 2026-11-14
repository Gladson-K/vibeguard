from v3util import run_json


def test_default_profile_meets_target(power_bin):
    data, rc, _ = run_json(power_bin, "--battery-mah", 2000)
    assert rc == 0
    assert data["meets_current"] and data["meets_battery"]
    assert data["avg_ma"] < 1.0
    assert data["battery_days"] > 100


def test_aggressive_profile_is_flagged(power_bin):
    data, rc, _ = run_json(
        power_bin,
        "--idle-ma",
        40,
        "--idle-ms",
        1000,
        "--infer-ms",
        200,
        "--tx-ma",
        150,
        "--tx-ms",
        800,
        "--sleep-s",
        5,
    )
    assert rc == 1
    assert not data["meets_current"] or not data["meets_battery"]


def test_longer_sleep_improves_life(power_bin):
    short, _, _ = run_json(power_bin, "--sleep-s", 15)
    long, _, _ = run_json(power_bin, "--sleep-s", 60)
    assert long["avg_ma"] < short["avg_ma"]
    assert long["battery_days"] > short["battery_days"]


def test_imperial_units_do_not_matter(power_bin):
    # Guard the open-circuit assumption: 2x battery capacity doubles runtime.
    one, _, _ = run_json(power_bin, "--battery-mah", 1000)
    two, _, _ = run_json(power_bin, "--battery-mah", 2000)
    assert abs(two["battery_days"] - 2 * one["battery_days"]) < 0.1
