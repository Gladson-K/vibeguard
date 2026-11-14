"""Tiny signed-OTA mock server for the V3 Docker test environment.

Generates a deterministic firmware blob, signs a manifest with the test key and
serves both over HTTP. The host SIL verifier then checks them exactly like the
device would.
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import ota_sign  # noqa: E402

DEFAULT_KEY_HEX = (
    "000102030405060708090a0b0c0d0e0f"
    "101112131415161718191a1b1c1d1e1f"
)


def demo_firmware(version: int, size: int = 65536) -> bytes:
    return bytes(((i * 31 + version * 7) & 0xFF) for i in range(size))


def prepare(directory: pathlib.Path) -> dict:
    key_hex = os.environ.get("VG_OTA_KEY_HEX", DEFAULT_KEY_HEX)
    version = int(os.environ.get("VG_OTA_VERSION", "4"))
    min_version = int(os.environ.get("VG_OTA_MIN_VERSION", "3"))
    firmware = demo_firmware(version)
    manifest = ota_sign.build_manifest(
        firmware, ota_sign.parse_key(key_hex), version, min_version
    )
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "firmware.bin").write_bytes(firmware)
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--dir", default="/tmp/ota")
    args = ap.parse_args()

    root = pathlib.Path(args.dir).resolve()
    manifest = prepare(root)
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *a, directory=str(root), **kw
    )
    handler.log_message = lambda *a, **kw: None  # type: ignore[assignment]
    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", args.port), handler)
    print(
        f"ota-mock ready on :{args.port} version={manifest['version']} "
        f"size={manifest['size']}",
        flush=True,
    )
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
