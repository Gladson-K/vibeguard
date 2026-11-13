import json
import os
import time
import uuid

import numpy as np
import pytest
import requests

from gateway.features import compute_features
from gateway.simulator import window

HOST = os.environ.get("MQTT_HOST")
URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")

pytestmark = pytest.mark.skipif(not HOST, reason="MQTT_HOST not set")


def test_mqtt_frames_reach_gateway():
    import paho.mqtt.client as mqtt

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except (AttributeError, TypeError):
        client = mqtt.Client()
    client.connect(HOST, int(os.environ.get("MQTT_PORT", 1883)))
    client.loop_start()

    device = f"mqtt-{uuid.uuid4().hex[:8]}"
    rng = np.random.default_rng(11)
    for _ in range(5):
        feats = compute_features(window(rng, fault=False), 1000)
        payload = {"device_id": device, "fs": 1000, **feats}
        info = client.publish(f"vibeguard/{device}/features", json.dumps(payload))
        info.wait_for_publish()
    client.loop_stop()
    client.disconnect()

    deadline = time.time() + 20
    seen = 0
    while time.time() < deadline:
        devices = requests.get(f"{URL}/api/devices", timeout=5).json()
        match = [d for d in devices if d["device_id"] == device]
        if match and match[0]["windows"] >= 5:
            seen = match[0]["windows"]
            break
        time.sleep(0.5)
    assert seen >= 5
