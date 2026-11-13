"""Load hardware/machine profiles and scenario definitions (YAML)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
SCENARIOS = Path(__file__).resolve().parent / "scenarios"


def load_yaml(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_profiles() -> tuple[dict, dict]:
    hw = load_yaml(CONFIG / "hardware.yaml")["sensors"]
    machines = load_yaml(CONFIG / "machines.yaml")["machines"]
    return hw, machines


def resolve_scenario(path: str | Path) -> dict:
    """Return a scenario dict with sensor/machine profiles merged in."""
    scenario = load_yaml(path)
    hw, machines = load_profiles()
    sensor_name = scenario.get("sensor", "mpu6050")
    machine_name = scenario.get("machine", "fan_25hz")
    if sensor_name not in hw:
        raise KeyError(f"unknown sensor profile: {sensor_name}")
    if machine_name not in machines:
        raise KeyError(f"unknown machine profile: {machine_name}")
    scenario = dict(scenario)
    scenario["sensor_profile"] = hw[sensor_name]
    scenario["machine_profile"] = machines[machine_name]
    scenario["sensor"] = sensor_name
    scenario["machine"] = machine_name
    return scenario
