import os
import json
import sqlite3
import threading
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

try:  # works when imported as the `gateway` package (tests, uvicorn gateway.app:app)
    from .detector import BaselineDetector, ModelScoreDetector
except ImportError:  # works when run from inside the gateway/ directory
    from detector import BaselineDetector, ModelScoreDetector

DB_PATH = os.environ.get("VG_DB", "vibeguard.db")
app = FastAPI(title="VibeGuard Gateway")
_lock = threading.Lock()
_db = sqlite3.connect(DB_PATH, check_same_thread=False)
_db.execute(
    """CREATE TABLE IF NOT EXISTS windows(
  id INTEGER PRIMARY KEY, device_id TEXT, ts REAL, rms REAL, peak REAL, crest REAL,
  kurtosis REAL, dom_freq REAL, status TEXT, score REAL, worst TEXT,
  model_score REAL, model_version TEXT, sensor TEXT)"""
)


def _ensure_columns():
    have = {row[1] for row in _db.execute("PRAGMA table_info(windows)")}
    for col, decl in (
        ("model_score", "REAL"),
        ("model_version", "TEXT"),
        ("sensor", "TEXT"),
    ):
        if col not in have:
            _db.execute(f"ALTER TABLE windows ADD COLUMN {col} {decl}")
    _db.commit()


_ensure_columns()
_detectors = {}
_score_detectors = {}


class Reading(BaseModel):
    device_id: str
    rms: float
    peak: float
    crest: float
    kurtosis: float
    dom_freq: float
    fs: int | None = None
    ts: float | None = None
    sensor: str | None = None
    model_score: float | None = None
    model_version: str | None = None
    bands: list[float] | None = None


def process(r: Reading):
    with _lock:
        det = _detectors.setdefault(r.device_id, BaselineDetector())
        feats = r.model_dump()
        res = det.update(feats)
        status = res["status"]
        score = res["score"]
        worst = res["worst"]

        if r.model_score is not None:
            sdet = _score_detectors.setdefault(r.device_id, ModelScoreDetector())
            sres = sdet.update(r.model_score)
            if sres["status"] != "learning":
                # model score is the primary signal for V2 nodes
                status = sres["status"]
                score = sres["score"]
                worst = "model_score"

        _db.execute(
            "INSERT INTO windows(device_id,ts,rms,peak,crest,kurtosis,dom_freq,status,score,worst,"
            "model_score,model_version,sensor) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                r.device_id, r.ts or time.time(), r.rms, r.peak, r.crest, r.kurtosis,
                r.dom_freq, status, score, worst, r.model_score, r.model_version, r.sensor,
            ),
        )
        _db.commit()
    return {"status": status, "score": score, "worst": worst}


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/ingest")
def ingest(r: Reading):
    return process(r)


@app.get("/api/devices")
def devices():
    with _lock:
        rows = _db.execute(
            "SELECT device_id, COUNT(*), MAX(ts) FROM windows GROUP BY device_id"
        ).fetchall()
        out = []
        for a, b, c in rows:
            det = _detectors.get(a)
            out.append(
                {
                    "device_id": a,
                    "windows": b,
                    "last_seen": c,
                    "learning": det.learning if det else None,
                    "model_score": _score_detectors[a].threshold
                    if a in _score_detectors and not _score_detectors[a].learning
                    else None,
                }
            )
    return out


@app.get("/api/history/{device_id}")
def history(device_id: str, limit: int = 300):
    with _lock:
        rows = _db.execute(
            "SELECT ts,rms,crest,kurtosis,dom_freq,status,score,model_score FROM windows "
            "WHERE device_id=? ORDER BY id DESC LIMIT ?",
            (device_id, limit),
        ).fetchall()
    keys = ("ts", "rms", "crest", "kurtosis", "dom_freq", "status", "score", "model_score")
    return [dict(zip(keys, r)) for r in reversed(rows)]


@app.post("/api/reset/{device_id}")
def reset(device_id: str):
    with _lock:
        _detectors.pop(device_id, None)
        _score_detectors.pop(device_id, None)
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


def _start_mqtt():
    host = os.environ.get("MQTT_HOST")
    if not host:
        return

    def worker():
        import paho.mqtt.client as mqtt

        try:
            c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except (AttributeError, TypeError):
            c = mqtt.Client()

        def on_msg(_c, _u, msg):
            try:
                process(Reading(**json.loads(msg.payload)))
            except Exception as e:  # noqa: BLE001 - never kill the ingest loop
                print("bad mqtt payload", e)

        c.on_message = on_msg
        port = int(os.environ.get("MQTT_PORT", 1883))
        while True:
            try:
                c.connect(host, port)
                c.subscribe("vibeguard/+/features")
                c.loop_forever()
            except Exception as e:  # noqa: BLE001 - broker may not be up yet
                print("mqtt unavailable, retrying:", e)
                time.sleep(3)

    threading.Thread(target=worker, daemon=True).start()


_start_mqtt()
