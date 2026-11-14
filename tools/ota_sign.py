"""Sign and inspect V3 OTA manifests.

The canonical payload must match firmware/src/vg_core/v3/ota_verify.cpp byte for
byte. Both sides are covered by tests/v3/test_ota.py so the mock server, the
tooling and the device verifier cannot drift.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import pathlib

PREFIX = "vg-ota-v1"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(version: int, min_version: int, size: int, digest: str) -> str:
    return f"{PREFIX}\n{version}\n{min_version}\n{size}\n{digest}\n"


def sign(key: bytes, version: int, min_version: int, size: int, digest: str) -> str:
    msg = canonical(version, min_version, size, digest).encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def build_manifest(
    firmware: bytes, key: bytes, version: int, min_version: int
) -> dict:
    digest = sha256_hex(firmware)
    return {
        "version": version,
        "min_version": min_version,
        "size": len(firmware),
        "sha256": digest,
        "sig": sign(key, version, min_version, len(firmware), digest),
    }


def parse_key(hexstr: str) -> bytes:
    key = bytes.fromhex(hexstr)
    if not key:
        raise ValueError("empty OTA key")
    return key


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--firmware", required=True)
    ap.add_argument("--key-hex", required=True)
    ap.add_argument("--version", type=int, required=True)
    ap.add_argument("--min-version", type=int, default=0)
    ap.add_argument("--out", default="-")
    ap.add_argument("--sha256-only", action="store_true")
    ap.add_argument("--print-canonical", action="store_true")
    args = ap.parse_args()

    data = pathlib.Path(args.firmware).read_bytes()
    digest = sha256_hex(data)

    if args.sha256_only:
        print(digest)
        return 0
    if args.print_canonical:
        print(canonical(args.version, args.min_version, len(data), digest), end="")
        return 0

    manifest = build_manifest(
        data, parse_key(args.key_hex), args.version, args.min_version
    )
    text = json.dumps(manifest, indent=2)
    if args.out == "-":
        print(text)
    else:
        pathlib.Path(args.out).write_text(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
