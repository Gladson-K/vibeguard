from __future__ import annotations

import json
import os
import subprocess

DEFAULT_KEY_HEX = (
    "000102030405060708090a0b0c0d0e0f"
    "101112131415161718191a1b1c1d1e1f"
)
KEY_HEX = os.environ.get("VG_OTA_KEY_HEX", DEFAULT_KEY_HEX)


def bin_path(env: str, default: str) -> str:
    return os.environ.get(env, default)


def run_json(binary, *args):
    cmd = [str(binary), *[str(a) for a in args]]
    r = subprocess.run(cmd, capture_output=True, text=True)
    text = r.stdout.strip()
    if not text:
        raise AssertionError(f"{binary} produced no output (rc={r.returncode}): {r.stderr}")
    return json.loads(text.splitlines()[-1]), r.returncode, r
