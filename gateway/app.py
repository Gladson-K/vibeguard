import os, sqlite3, threading, time, json
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from detector import BaselineDetector

DB_PATH = os.environ.get("VG_DB", "vibeguard.db")
app = FastAPI(title="VibeGuard Gateway")
_lock = threading.Lock()
_db = sqlite3.connect(DB_PATH, check_same_thread=False)
_db.execute("""CREATE TABLE IF NOT EXISTS windows(
  id INTEGER PRIMARY KEY, device_id TEXT, ts REAL, rms REAL, peak REAL, crest REAL,
  kurtosis REAL, dom_freq REAL, status TEXT, score REAL, worst TEXT)""")
_db.commit()
_detectors = {}

class Reading(BaseModel):
    device_id: str
    rms: float
    peak: float
    crest: float
    kurtosis: float
    dom_freq: float
    fs: int | None = None
    ts: float | None = None

def process(r: Reading):
    with _lock:
        det = _detectors.setdefault(r.device_id, BaselineDetector())
        feats = r.model_dump()
        res = det.update(feats)
        _db.execute("INSERT INTO windows(device_id,ts,rms,peak,crest,kurtosis,dom_freq,status,score,worst) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (r.device_id, r.ts or time.time(), r.rms, r.peak, r.crest, r.kurtosis, r.dom_freq,
                     res["status"], res["score"], res["worst"]))
        _db.commit()
    return res

@app.post("/api/ingest")
def ingest(r: Reading):
    return process(r)

@app.get("/api/devices")
def devices():
    with _lock:
        rows = _db.execute("SELECT device_id, COUNT(*), MAX(ts) FROM windows GROUP BY device_id").fetchall()
    return [{"device_id": a, "windows": b, "last_seen": c, "learning": _detectors[a].learning if a in _detectors else None} for a, b, c in rows]

@app.get("/api/history/{device_id}")
def history(device_id: str, limit: int = 300):
    with _lock:
        rows = _db.execute("SELECT ts,rms,crest,kurtosis,dom_freq,status,score FROM windows WHERE device_id=? ORDER BY id DESC LIMIT ?", (device_id, limit)).fetchall()
    keys = ("ts", "rms", "crest", "kurtosis", "dom_freq", "status", "score")
    return [dict(zip(keys, r)) for r in reversed(rows)]

@app.post("/api/reset/{device_id}")
def reset(device_id: str):
    with _lock:
        _detectors.pop(device_id, None)
    return {"ok": True}

@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")

def _start_mqtt():
    host = os.environ.get("MQTT_HOST")
    if not host:
        return
    import paho.mqtt.client as mqtt
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    def on_msg(_c, _u, msg):
        try:
            process(Reading(**json.loads(msg.payload)))
        except Exception as e:
            print("bad mqtt payload", e)
    c.on_message = on_msg
    c.connect(host, int(os.environ.get("MQTT_PORT", 1883)))
    c.subscribe("vibeguard/+/features")
    c.loop_start()

_start_mqtt()
