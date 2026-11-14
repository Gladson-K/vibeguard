"""Frame transports: HTTP ingest (synchronous result) and MQTT publish."""
from __future__ import annotations

import json
import time

import requests


class HttpTransport:
    def __init__(self, url: str):
        self.url = url.rstrip("/")
        # Keep-alive avoids a fresh TCP handshake per frame; connection churn
        # otherwise shows up as spurious latency spikes under CI load.
        self.session = requests.Session()
        self.session.headers.update({"Connection": "keep-alive"})

    def close(self) -> None:
        self.session.close()

    def send(self, frame: dict) -> tuple[dict, float]:
        t0 = time.perf_counter()
        resp = self.session.post(f"{self.url}/api/ingest", json=frame, timeout=10)
        resp.raise_for_status()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return resp.json(), dt_ms

    def reset(self, device_id: str) -> None:
        self.session.post(f"{self.url}/api/reset/{device_id}", timeout=10)

    def history(self, device_id: str, limit: int = 500) -> list[dict]:
        resp = self.session.get(
            f"{self.url}/api/history/{device_id}", params={"limit": limit}, timeout=10
        )
        resp.raise_for_status()
        return resp.json()

    def devices(self) -> list[dict]:
        resp = self.session.get(f"{self.url}/api/devices", timeout=10)
        resp.raise_for_status()
        return resp.json()


class MqttTransport:
    def __init__(self, host: str, port: int = 1883):
        self.host = host
        self.port = port

    def send(self, frame: dict) -> tuple[dict, float]:
        import paho.mqtt.client as mqtt

        try:
            c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except (AttributeError, TypeError):
            c = mqtt.Client()
        c.connect(self.host, self.port)
        c.loop_start()
        t0 = time.perf_counter()
        info = c.publish(f"vibeguard/{frame['device_id']}/features", json.dumps(frame))
        info.wait_for_publish()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        c.loop_stop()
        c.disconnect()
        return {"status": "published"}, dt_ms
