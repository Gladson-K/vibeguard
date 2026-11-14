import json
import os
import urllib.request

import pytest

from v3util import ota_args, run_json

BASE_URL = os.environ.get("OTA_MOCK_URL")

pytestmark = pytest.mark.skipif(not BASE_URL, reason="OTA mock not configured")


def _fetch(path):
    with urllib.request.urlopen(BASE_URL + path, timeout=10) as resp:
        return resp.read()


def test_served_manifest_and_firmware_verify(ota_bin, tmp_path):
    manifest = json.loads(_fetch("/manifest.json"))
    firmware = _fetch("/firmware.bin")
    path = tmp_path / "firmware.bin"
    path.write_bytes(firmware)

    assert len(firmware) == manifest["size"]
    data, rc, _ = run_json(
        ota_bin, *ota_args(path, manifest, current=manifest["version"] - 1)
    )
    assert rc == 0
    assert data["valid"] is True


def test_served_firmware_tamper_rejected(ota_bin, tmp_path):
    manifest = json.loads(_fetch("/manifest.json"))
    firmware = bytearray(_fetch("/firmware.bin"))
    firmware[0] ^= 0xFF
    path = tmp_path / "firmware.bin"
    path.write_bytes(bytes(firmware))

    data, rc, _ = run_json(
        ota_bin, *ota_args(path, manifest, current=manifest["version"] - 1)
    )
    assert rc == 1
    assert data["result"] == "bad_hash"
