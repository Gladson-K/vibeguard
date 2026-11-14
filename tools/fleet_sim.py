#!/usr/bin/env python3
"""Generate a synthetic V4 fleet against a running gateway.

    python tools/fleet_sim.py --device-count 20 --interval 2
    python tools/fleet_sim.py --key-hex <per-device-key> --signed

By default it posts unsigned compact frames to /api/ingest/lora. Use --json to
exercise the legacy /api/ingest path instead.
"""

from __future__ import annotations

import argparse
import random
import time

import requests

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from gateway import codec  # noqa: E402


def make_frame(device: int, seq: int, fault: bool, rng: random.Random) -> codec.LoraFrame:
    base = 0.85 if fault else 0.08
    return codec.LoraFrame(
        version=4,
        device_id=device,
        seq=seq,
        ts=int(time.time()),
        rms=max(0.01, rng.gauss(base, base * 0.1)),
        peak=max(0.02, rng.gauss(base * 3.5, base * 0.4)),
        crest=max(1.5, rng.gauss(4.5 if fault else 3.0, 0.3)),
        kurtosis=max(1.5, rng.gauss(7.0 if fault else 2.9, 0.4)),
        dom_freq=rng.choice([25.0, 50.0, 87.0]),
        model_score=max(0.0, rng.gauss(0.9 if fault else 0.05, 0.05)),
        battery_mv=int(max(3200, rng.gauss(3900, 40))),
        rssi=int(rng.gauss(-85, 5)),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:18000")
    ap.add_argument("--device-count", type=int, default=10)
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--fault-after", type=int, default=30)
    ap.add_argument("--key-hex", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    key = bytes.fromhex(args.key_hex) if args.key_hex else None
    rng = random.Random(4)
    seq = 0
    sent = failed = 0
    print(f"sending {args.device_count} devices to {args.url} every {args.interval}s")
    try:
        while True:
            for dev in range(1, args.device_count + 1):
                seq += 1
                fault = seq > args.fault_after and dev % 3 == 0
                frame = make_frame(dev, seq, fault, rng)
                if args.json:
                    body = {
                        "device_id": f"sim-{dev:03d}",
                        "rms": frame.rms,
                        "peak": frame.peak,
                        "crest": frame.crest,
                        "kurtosis": frame.kurtosis,
                        "dom_freq": frame.dom_freq,
                        "model_score": frame.model_score,
                        "ts": frame.ts,
                    }
                    resp = requests.post(f"{args.url}/api/ingest", json=body, timeout=5)
                else:
                    raw = codec.sign(frame, key) if key else codec.encode(frame)
                    resp = requests.post(
                        f"{args.url}/api/ingest/lora",
                        json={"frame_hex": raw.hex(), "device_id": f"sim-{dev:03d}"},
                        timeout=5,
                    )
                if resp.ok:
                    sent += 1
                else:
                    failed += 1
            print(f"sent={sent} failed={failed}", end="\r", flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\nsent={sent} failed={failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
