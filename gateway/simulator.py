"""Fake motor node: healthy rotation + harmonics; fault adds bearing-like impacts.

Supports HTTP (default) and MQTT transport, and a zero-interval mode for tests.
"""
import argparse
import json
import time

import numpy as np
import requests

try:
    from .features import compute_features
except ImportError:
    from features import compute_features


def window(rng, fs=1000, n=512, fault=False, rpm=1500, fault_type="bearing", amplitude=0.35):
    t = np.arange(n) / fs
    f_rot = rpm / 60.0
    x = 1.0 + 0.05 * np.sin(2 * np.pi * f_rot * t) + 0.02 * np.sin(2 * np.pi * 2 * f_rot * t)
    x = x + rng.normal(0, 0.01, n)
    if fault:
        if fault_type == "imbalance":
            x += amplitude * np.sin(2 * np.pi * f_rot * t)
        elif fault_type == "looseness":
            for h in (1, 2, 3, 4):
                x += amplitude / h * np.sin(2 * np.pi * h * f_rot * t)
            x += rng.normal(0, amplitude * 0.1, n)
        elif fault_type == "belt":
            x += amplitude * rng.normal(0, 1, n) * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * t))
            x += amplitude * 0.5 * np.sin(2 * np.pi * (f_rot / 3) * t)
        else:  # bearing-like impact train
            period = max(1, int(fs / 87))
            for i in range(0, n, period):
                k = np.arange(min(20, n - i))
                x[i:i + len(k)] += amplitude * np.exp(-k / 4) * np.sin(2 * np.pi * 300 * k / fs)
            x += rng.normal(0, amplitude * 0.05, n)
    return x


def _send_http(url, payload):
    return requests.post(url, json=payload, timeout=5).json()


def _send_mqtt(host, port, device, payload):
    import paho.mqtt.client as mqtt

    try:
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except (AttributeError, TypeError):
        c = mqtt.Client()
    c.connect(host, port)
    c.loop_start()
    info = c.publish(f"vibeguard/{device}/features", json.dumps(payload))
    info.wait_for_publish()
    c.loop_stop()
    c.disconnect()
    return {"status": "published"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8000/api/ingest")
    p.add_argument("--device", default="sim-01")
    p.add_argument("--fault-after", type=int, default=120)
    p.add_argument("--interval", type=float, default=0.3)
    p.add_argument("--count", type=int, default=400)
    p.add_argument("--rpm", type=float, default=1500)
    p.add_argument("--fault-type", default="bearing",
                   choices=["bearing", "imbalance", "looseness", "belt"])
    p.add_argument("--mqtt-host", default=None, help="publish over MQTT instead of HTTP")
    p.add_argument("--mqtt-port", type=int, default=1883)
    p.add_argument("--quiet", action="store_true")
    a = p.parse_args()

    rng = np.random.default_rng(1)
    for i in range(a.count):
        fault = i >= a.fault_after
        x = window(rng, fault=fault, rpm=a.rpm, fault_type=a.fault_type)
        f = compute_features(x, 1000)
        payload = {"device_id": a.device, "fs": 1000, "sensor": "mpu6050", **f}
        if a.mqtt_host:
            r = _send_mqtt(a.mqtt_host, a.mqtt_port, a.device, payload)
        else:
            r = _send_http(a.url, payload)
        if not a.quiet:
            print(i, r)
        if a.interval > 0:
            time.sleep(a.interval)


if __name__ == "__main__":
    main()
