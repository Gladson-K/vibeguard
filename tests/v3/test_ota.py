import subprocess

from tools import ota_sign
from v3util import KEY_HEX, make_firmware, ota_args, run_json

KEY = bytes.fromhex(KEY_HEX)


def _write(tmp_path, data=None):
    data = data if data is not None else make_firmware()
    path = tmp_path / "firmware.bin"
    path.write_bytes(data)
    return path, data


def test_canonical_matches_cpp(ota_bin, tmp_path):
    path, fw = _write(tmp_path)
    manifest = ota_sign.build_manifest(fw, KEY, 4, 3)
    r = subprocess.run(
        [
            str(ota_bin),
            "--firmware",
            str(path),
            "--version",
            "4",
            "--min-version",
            "3",
            "--print-canonical",
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert r.stdout == ota_sign.canonical(4, 3, len(fw), manifest["sha256"])


def test_valid_manifest_accepted(ota_bin, tmp_path):
    path, fw = _write(tmp_path)
    manifest = ota_sign.build_manifest(fw, KEY, 4, 3)
    data, rc, _ = run_json(ota_bin, *ota_args(path, manifest, current=3))
    assert rc == 0
    assert data["valid"] is True
    assert data["result"] == "ok"


def test_tampered_firmware_rejected(ota_bin, tmp_path):
    path, fw = _write(tmp_path)
    manifest = ota_sign.build_manifest(fw, KEY, 4, 3)
    tampered = bytearray(fw)
    tampered[len(tampered) // 2] ^= 0xFF
    path.write_bytes(tampered)
    data, rc, _ = run_json(ota_bin, *ota_args(path, manifest, current=3))
    assert rc == 1
    assert data["result"] == "bad_hash"


def test_wrong_key_rejected(ota_bin, tmp_path):
    path, fw = _write(tmp_path)
    manifest = ota_sign.build_manifest(fw, KEY, 4, 3)
    data, rc, _ = run_json(
        ota_bin, *ota_args(path, manifest, current=3, key_hex="ff" * 32)
    )
    assert rc == 1
    assert data["result"] == "bad_signature"


def test_downgrade_rejected(ota_bin, tmp_path):
    path, fw = _write(tmp_path)
    manifest = ota_sign.build_manifest(fw, KEY, 4, 3)
    data, rc, _ = run_json(ota_bin, *ota_args(path, manifest, current=4))
    assert rc == 1
    assert data["result"] == "downgrade"


def test_below_minimum_version_rejected(ota_bin, tmp_path):
    path, fw = _write(tmp_path)
    manifest = ota_sign.build_manifest(fw, KEY, 4, 5)
    data, rc, _ = run_json(ota_bin, *ota_args(path, manifest, current=3))
    assert rc == 1
    assert data["result"] == "too_old"


def test_size_mismatch_rejected(ota_bin, tmp_path):
    path, fw = _write(tmp_path)
    manifest = ota_sign.build_manifest(fw, KEY, 4, 3)
    data, rc, _ = run_json(
        ota_bin, *ota_args(path, manifest, current=3, size=manifest["size"] + 1)
    )
    assert rc == 1
    assert data["result"] == "bad_size"


def test_bad_signature_hex_rejected(ota_bin, tmp_path):
    path, fw = _write(tmp_path)
    manifest = ota_sign.build_manifest(fw, KEY, 4, 3)
    data, rc, _ = run_json(
        ota_bin, *ota_args(path, manifest, current=3, sig="zz" * 32)
    )
    assert rc == 1
    assert data["result"] == "bad_signature"
