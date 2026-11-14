"""Deterministic staged model rollout (mirror of vg_core/v4/rollout.cpp)."""

from __future__ import annotations

STAGE_PERCENT = {0: 10, 1: 50, 2: 100}


def fnv1a32(text: str) -> int:
    h = 2166136261
    for byte in text.encode("utf-8"):
        h ^= byte
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def bucket(device_id: str) -> int:
    return fnv1a32(device_id) % 100


def selected(device_id: str, percent: int) -> bool:
    if percent >= 100:
        return True
    if percent <= 0:
        return False
    return bucket(device_id) < percent


def stage_percent(stage: int) -> int:
    return STAGE_PERCENT.get(stage, 100)
