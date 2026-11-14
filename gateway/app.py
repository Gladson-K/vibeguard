import asyncio
import json
import os
import queue
import sqlite3
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel

try:  # package import (uvicorn gateway.app:app, tests/v4)
    from . import alerts as alerts_mod
    from . import codec, diagnosis, drift, rollout, rul
    from .detector import BaselineDetector, ModelScoreDetector
    from .notify import send_alert
except ImportError:  # run from inside gateway/ (V1/V2 test layout)
    import alerts as alerts_mod
    import codec
    import diagnosis
    import drift
    import rollout
    import rul
    from detector import BaselineDetector, ModelScoreDetector
    from notify import send_alert

DB_PATH = os.environ.get("VG_DB", "vibeguard.db")
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
DEFAULT_GEOMETRY = dict(n_balls=8, ball_d_mm=7.94, pitch_d_mm=39.04, contact_angle_deg=0.0)

app = FastAPI(title="VibeGuard Gateway")
_lock = threading.Lock()
_db = sqlite3.connect(DB_PATH, check_same_thread=False)
_db.execute(
    """CREATE TABLE IF NOT EXISTS windows(
  id INTEGER PRIMARY KEY, device_id TEXT, ts REAL, rms REAL, peak REAL, crest REAL,
  kurtosis REAL, dom_freq REAL, status TEXT, score REAL, worst TEXT,
  model_score REAL, model_version TEXT, sensor TEXT,
  machine_id TEXT, battery_mv INTEGER, rssi INTEGER, seq INTEGER,
  transport TEXT, diagnosis TEXT)"""
)
_db.execute(
    """CREATE TABLE IF NOT EXISTS devices(
  device_id TEXT PRIMARY KEY, machine_id TEXT, key_hex TEXT, fw_version TEXT,
  first_seen REAL, last_seen REAL, battery_mv INTEGER, rssi INTEGER,
  seq INTEGER, transport TEXT, model_version TEXT)"""
)
_db.execute(
    """CREATE TABLE IF NOT EXISTS machines(
  machine_id TEXT PRIMARY KEY, name TEXT, rpm REAL, n_balls INTEGER,
  ball_d_mm REAL, pitch_d_mm REAL, contact_angle_deg REAL,
  rms_warn REAL, rms_crit REAL)"""
)
_db.execute(
    """CREATE TABLE IF NOT EXISTS models(
  version TEXT PRIMARY KEY, path TEXT, created REAL, status TEXT, notes TEXT)"""
)
_db.execute(
    """CREATE TABLE IF NOT EXISTS rollouts(
  id INTEGER PRIMARY KEY, model_version TEXT, stage INTEGER, percent INTEGER,
  created REAL, active INTEGER)"""
)
_db.execute(
    """CREATE TABLE IF NOT EXISTS alerts(
  id INTEGER PRIMARY KEY, device_id TEXT, ts REAL, level TEXT, kind TEXT,
  message TEXT, acknowledged INTEGER)"""
)
_db.execute(
    """CREATE TABLE IF NOT EXISTS maintenance(
  device_id TEXT PRIMARY KEY, until REAL, note TEXT)"""
)


def _ensure_columns():
    have = {row[1] for row in _db.execute("PRAGMA table_info(windows)")}
    for col, decl in (
        ("model_score", "REAL"),
        ("model_version", "TEXT"),
        ("sensor", "TEXT"),
        ("machine_id", "TEXT"),
        ("battery_mv", "INTEGER"),
        ("rssi", "INTEGER"),
        ("seq", "INTEGER"),
        ("transport", "TEXT"),
        ("diagnosis", "TEXT"),
    ):
        if col not in have:
            _db.execute(f"ALTER TABLE windows ADD COLUMN {col} {decl}")
    _db.commit()


def _seed_machines():
    path = CONFIG_DIR / "machines.yaml"
    if not path.exists():
        return
    try:
        import yaml
    except ImportError:
        return
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except Exception:  # noqa: BLE001 - bad config must not stop gateway
        return
    data = data.get("machines", data)
    for name, spec in data.items():
        if not isinstance(spec, dict):
            continue
        rpm = float(spec.get("rpm", 0) or 0)
        geom = dict(DEFAULT_GEOMETRY)
        geom.update({k: spec[k] for k in DEFAULT_GEOMETRY if k in spec})
        _db.execute(
            "INSERT OR IGNORE INTO machines(machine_id,name,rpm,n_balls,ball_d_mm,"
            "pitch_d_mm,contact_angle_deg,rms_warn,rms_crit) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                name,
                name,
                rpm,
                geom["n_balls"],
                geom["ball_d_mm"],
                geom["pitch_d_mm"],
                geom["contact_angle_deg"],
                float(spec.get("rms_warn", 0.35)),
                float(spec.get("rms_crit", 0.5)),
            ),
        )
    _db.commit()


_ensure_columns()
_seed_machines()
_detectors = {}
_score_detectors = {}
_alert_engine = alerts_mod.AlertEngine()
_metrics = {
    "windows": 0,
    "warnings": 0,
    "anomalies": 0,
    "alerts": 0,
    "ingest_errors": 0,
    "lora_frames": 0,
}
_sub_lock = threading.Lock()
_subscribers: list[queue.Queue] = []


def _subscribe() -> queue.Queue:
    q: queue.Queue = queue.Queue(maxsize=100)
    with _sub_lock:
        _subscribers.append(q)
    return q


def _unsubscribe(q: queue.Queue) -> None:
    with _sub_lock:
        if q in _subscribers:
            _subscribers.remove(q)


def _broadcast(event: dict) -> None:
    with _sub_lock:
        subs = list(_subscribers)
    for q in subs:
        try:
            q.put_nowait(event)
        except queue.Full:
            pass


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
    machine_id: str | None = None
    battery_mv: int | None = None
    rssi: int | None = None
    seq: int | None = None
    transport: str | None = None
    fw_version: str | None = None
    envelope_freq: float | None = None


class MachineSpec(BaseModel):
    machine_id: str
    name: str | None = None
    rpm: float = 0
    n_balls: int = DEFAULT_GEOMETRY["n_balls"]
    ball_d_mm: float = DEFAULT_GEOMETRY["ball_d_mm"]
    pitch_d_mm: float = DEFAULT_GEOMETRY["pitch_d_mm"]
    contact_angle_deg: float = DEFAULT_GEOMETRY["contact_angle_deg"]
    rms_warn: float = 0.35
    rms_crit: float = 0.5


class LoraPayload(BaseModel):
    frame_hex: str
    device_id: str | None = None
    rssi: int | None = None


class KeyPayload(BaseModel):
    key_hex: str


class DeviceMeta(BaseModel):
    device_id: str | None = None
    machine_id: str | None = None
    fw_version: str | None = None


class MachinePayload(BaseModel):
    device_id: str
    machine_id: str | None = None
    fw_version: str | None = None


class MaintenancePayload(BaseModel):
    until: float
    note: str = ""


class ModelPayload(BaseModel):
    version: str
    path: str = ""
    notes: str = ""
    status: str = "registered"


class RolloutPayload(BaseModel):
    model_version: str
    stage: int = 0


def _machine_row(machine_id: str | None):
    if not machine_id:
        return None
    row = _db.execute(
        "SELECT machine_id,rpm,n_balls,ball_d_mm,pitch_d_mm,contact_angle_deg,"
        "rms_warn,rms_crit FROM machines WHERE machine_id=?",
        (machine_id,),
    ).fetchone()
    if not row:
        return None
    return dict(
        zip(
            (
                "machine_id",
                "rpm",
                "n_balls",
                "ball_d_mm",
                "pitch_d_mm",
                "contact_angle_deg",
                "rms_warn",
                "rms_crit",
            ),
            row,
        )
    )


def _device_machine(device_id: str, explicit: str | None = None) -> str | None:
    if explicit:
        return explicit
    row = _db.execute(
        "SELECT machine_id FROM devices WHERE device_id=?", (device_id,)
    ).fetchone()
    return row[0] if row and row[0] else None


def _diagnose(r: Reading) -> str | None:
    machine_id = _device_machine(r.device_id, r.machine_id)
    spec = _machine_row(machine_id)
    if not spec:
        return None
    geom = diagnosis.BearingGeometry(
        rpm=spec["rpm"],
        n_balls=spec["n_balls"],
        ball_d_mm=spec["ball_d_mm"],
        pitch_d_mm=spec["pitch_d_mm"],
        contact_angle_deg=spec["contact_angle_deg"],
    )
    freqs = diagnosis.bearing_frequencies(geom)
    inp = diagnosis.DiagnosisInput(
        rms=r.rms,
        crest=r.crest,
        kurtosis=r.kurtosis,
        dom_freq=r.dom_freq,
        envelope_freq=r.envelope_freq or 0.0,
    )
    return diagnosis.diagnose(inp, freqs)


def _record_alert(device_id: str, event: alerts_mod.AlertEvent, now: float) -> None:
    _db.execute(
        "INSERT INTO alerts(device_id,ts,level,kind,message,acknowledged)"
        " VALUES(?,?,?,?,?,0)",
        (device_id, now, event.level, event.kind, event.message),
    )
    _metrics["alerts"] += 1
    send_alert(device_id, event.level, event.message)
    _broadcast(
        {
            "type": "alert",
            "device_id": device_id,
            "ts": now,
            "level": event.level,
            "message": event.message,
        }
    )


def process(r: Reading):
    now = time.time()
    with _lock:
        det = _detectors.setdefault(r.device_id, BaselineDetector())
        res = det.update(r.model_dump())
        status = res["status"]
        score = res["score"]
        worst = res["worst"]

        if r.model_score is not None:
            sdet = _score_detectors.setdefault(r.device_id, ModelScoreDetector())
            sres = sdet.update(r.model_score)
            if sres["status"] != "learning":
                status = sres["status"]
                score = sres["score"]
                worst = "model_score"

        diag = _diagnose(r)
        _db.execute(
            "INSERT INTO windows(device_id,ts,rms,peak,crest,kurtosis,dom_freq,status,score,"
            "worst,model_score,model_version,sensor,machine_id,battery_mv,rssi,seq,"
            "transport,diagnosis) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                r.device_id,
                r.ts or now,
                r.rms,
                r.peak,
                r.crest,
                r.kurtosis,
                r.dom_freq,
                status,
                score,
                worst,
                r.model_score,
                r.model_version,
                r.sensor,
                _device_machine(r.device_id, r.machine_id),
                r.battery_mv,
                r.rssi,
                r.seq,
                r.transport,
                diag,
            ),
        )
        _db.execute(
            """INSERT INTO devices(device_id,machine_id,fw_version,first_seen,last_seen,
               battery_mv,rssi,seq,transport,model_version)
               VALUES(?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(device_id) DO UPDATE SET
                 machine_id=COALESCE(excluded.machine_id,devices.machine_id),
                 fw_version=COALESCE(excluded.fw_version,devices.fw_version),
                 last_seen=excluded.last_seen,
                 battery_mv=COALESCE(excluded.battery_mv,devices.battery_mv),
                 rssi=COALESCE(excluded.rssi,devices.rssi),
                 seq=COALESCE(excluded.seq,devices.seq),
                 transport=COALESCE(excluded.transport,devices.transport),
                 model_version=COALESCE(excluded.model_version,devices.model_version)""",
            (
                r.device_id,
                r.machine_id,
                r.fw_version,
                now,
                now,
                r.battery_mv,
                r.rssi,
                r.seq,
                r.transport,
                r.model_version,
            ),
        )
        _db.commit()

        if status == "warning":
            _metrics["warnings"] += 1
        elif status == "anomaly":
            _metrics["anomalies"] += 1
        _metrics["windows"] += 1

        maint = _db.execute(
            "SELECT until FROM maintenance WHERE device_id=?", (r.device_id,)
        ).fetchone()
        suppressed = bool(maint and maint[0] > now)
        events = _alert_engine.evaluate(
            r.device_id,
            status,
            maintenance=suppressed,
            detail=worst or "",
        )
        for event in events:
            _record_alert(r.device_id, event, now)
        _db.commit()

        _broadcast(
            {
                "type": "window",
                "device_id": r.device_id,
                "ts": r.ts or now,
                "status": status,
                "score": score,
                "diagnosis": diag,
            }
        )
    return {"status": status, "score": score, "worst": worst, "diagnosis": diag}


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
        _alert_engine.reset(device_id)
    return {"ok": True}


@app.post("/api/ingest/lora")
def ingest_lora(p: LoraPayload):
    try:
        raw = bytes.fromhex(p.frame_hex)
    except ValueError:
        _metrics["ingest_errors"] += 1
        raise HTTPException(status_code=400, detail="bad hex")

    key = None
    if p.device_id:
        row = _db.execute(
            "SELECT key_hex FROM devices WHERE device_id=?", (p.device_id,)
        ).fetchone()
        if row and row[0]:
            key = bytes.fromhex(row[0])
    env_key = os.environ.get("VG_DEVICE_KEY_HEX")
    if key is None and env_key:
        key = bytes.fromhex(env_key)

    status = "ok"
    if len(raw) == codec.SIGNED_FRAME_SIZE:
        if not key:
            _metrics["ingest_errors"] += 1
            raise HTTPException(status_code=401, detail="unknown device key")
        frame, status = codec.decode_signed(raw, key)
        if frame is None and p.device_id:
            row = _db.execute(
                "SELECT key_hex FROM devices WHERE device_id=?", (p.device_id,)
            ).fetchone()
            if row and row[0] and bytes.fromhex(row[0]) != key:
                frame, status = codec.decode_signed(raw, bytes.fromhex(row[0]))
    elif len(raw) == codec.FRAME_SIZE:
        if key:
            _metrics["ingest_errors"] += 1
            raise HTTPException(status_code=401, detail="signed frame required")
        frame, _ = codec.decode(raw)
        if frame is None:
            status = "bad_crc"
    else:
        _metrics["ingest_errors"] += 1
        raise HTTPException(status_code=400, detail="bad frame length")

    if frame is None:
        _metrics["ingest_errors"] += 1
        raise HTTPException(status_code=401, detail=status)

    device_id = p.device_id or f"lora-{frame.device_id:04x}"
    if p.rssi is not None:
        frame.rssi = p.rssi
    reading = Reading(
        device_id=device_id,
        rms=frame.rms,
        peak=frame.peak,
        crest=frame.crest,
        kurtosis=frame.kurtosis,
        dom_freq=frame.dom_freq,
        ts=frame.ts or None,
        sensor="lora",
        model_score=frame.model_score,
        battery_mv=frame.battery_mv,
        rssi=frame.rssi,
        seq=frame.seq,
        transport="lora",
    )
    with _lock:
        _metrics["lora_frames"] += 1
    result = process(reading)
    result["device_id"] = device_id
    return result


@app.get("/api/fleet")
def fleet():
    with _lock:
        rows = _db.execute(
            """SELECT d.device_id,d.machine_id,d.fw_version,d.last_seen,d.battery_mv,
                      d.rssi,d.transport,d.model_version,
                      (SELECT status FROM windows w WHERE w.device_id=d.device_id
                       ORDER BY w.id DESC LIMIT 1) AS status,
                      (SELECT ts FROM windows w WHERE w.device_id=d.device_id
                       ORDER BY w.id DESC LIMIT 1) AS last_window
               FROM devices d ORDER BY d.device_id"""
        ).fetchall()
        keys = (
            "device_id",
            "machine_id",
            "fw_version",
            "last_seen",
            "battery_mv",
            "rssi",
            "transport",
            "model_version",
            "status",
            "last_window",
        )
        return [dict(zip(keys, row)) for row in rows]


@app.put("/api/devices/{device_id}")
def register_device(device_id: str, meta: DeviceMeta):
    with _lock:
        _db.execute(
            """INSERT INTO devices(device_id,machine_id,fw_version,first_seen,last_seen)
               VALUES(?,?,?,?,?)
               ON CONFLICT(device_id) DO UPDATE SET
                 machine_id=COALESCE(excluded.machine_id,devices.machine_id),
                 fw_version=COALESCE(excluded.fw_version,devices.fw_version)""",
            (device_id, meta.machine_id, meta.fw_version, time.time(), time.time()),
        )
        _db.commit()
    return {"ok": True, "device_id": device_id}


@app.put("/api/devices/{device_id}/key")
def register_key(device_id: str, payload: KeyPayload):
    try:
        key = bytes.fromhex(payload.key_hex)
    except ValueError:
        raise HTTPException(status_code=400, detail="bad key hex")
    if not 16 <= len(key) <= 64:
        raise HTTPException(status_code=400, detail="key must be 16..64 bytes")
    with _lock:
        _db.execute(
            """INSERT INTO devices(device_id,key_hex,first_seen,last_seen)
               VALUES(?,?,?,?)
               ON CONFLICT(device_id) DO UPDATE SET key_hex=excluded.key_hex""",
            (device_id, key.hex(), time.time(), time.time()),
        )
        _db.commit()
    return {"ok": True, "device_id": device_id}


@app.get("/api/machines")
def machines():
    with _lock:
        rows = _db.execute(
            "SELECT machine_id,name,rpm,n_balls,ball_d_mm,pitch_d_mm,"
            "contact_angle_deg,rms_warn,rms_crit FROM machines ORDER BY machine_id"
        ).fetchall()
    keys = (
        "machine_id",
        "name",
        "rpm",
        "n_balls",
        "ball_d_mm",
        "pitch_d_mm",
        "contact_angle_deg",
        "rms_warn",
        "rms_crit",
    )
    return [dict(zip(keys, r)) for r in rows]


@app.post("/api/machines")
def upsert_machine(spec: MachineSpec):
    with _lock:
        _db.execute(
            """INSERT INTO machines(machine_id,name,rpm,n_balls,ball_d_mm,pitch_d_mm,
               contact_angle_deg,rms_warn,rms_crit) VALUES(?,?,?,?,?,?,?,?,?)
               ON CONFLICT(machine_id) DO UPDATE SET
                 name=excluded.name,rpm=excluded.rpm,n_balls=excluded.n_balls,
                 ball_d_mm=excluded.ball_d_mm,pitch_d_mm=excluded.pitch_d_mm,
                 contact_angle_deg=excluded.contact_angle_deg,
                 rms_warn=excluded.rms_warn,rms_crit=excluded.rms_crit""",
            (
                spec.machine_id,
                spec.name or spec.machine_id,
                spec.rpm,
                spec.n_balls,
                spec.ball_d_mm,
                spec.pitch_d_mm,
                spec.contact_angle_deg,
                spec.rms_warn,
                spec.rms_crit,
            ),
        )
        _db.commit()
    return {"ok": True, "machine_id": spec.machine_id}


@app.post("/api/machines/{device_id}/assign")
def assign_machine(device_id: str, payload: MachinePayload):
    with _lock:
        _db.execute(
            "UPDATE devices SET machine_id=? WHERE device_id=?",
            (payload.machine_id, device_id),
        )
        _db.commit()
    return {"ok": True, "device_id": device_id, "machine_id": payload.machine_id}


@app.post("/api/devices/{device_id}/maintenance")
def set_maintenance(device_id: str, payload: MaintenancePayload):
    with _lock:
        _db.execute(
            "INSERT INTO maintenance(device_id,until,note) VALUES(?,?,?) "
            "ON CONFLICT(device_id) DO UPDATE SET until=excluded.until,"
            "note=excluded.note",
            (device_id, payload.until, payload.note),
        )
        _db.commit()
    return {"ok": True, "device_id": device_id, "until": payload.until}


@app.delete("/api/devices/{device_id}/maintenance")
def clear_maintenance(device_id: str):
    with _lock:
        _db.execute("DELETE FROM maintenance WHERE device_id=?", (device_id,))
        _db.commit()
    return {"ok": True, "device_id": device_id}


@app.get("/api/alerts")
def list_alerts(limit: int = 100, acknowledged: bool | None = None):
    with _lock:
        if acknowledged is None:
            rows = _db.execute(
                "SELECT id,device_id,ts,level,kind,message,acknowledged FROM alerts "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = _db.execute(
                "SELECT id,device_id,ts,level,kind,message,acknowledged FROM alerts "
                "WHERE acknowledged=? ORDER BY id DESC LIMIT ?",
                (1 if acknowledged else 0, limit),
            ).fetchall()
    keys = ("id", "device_id", "ts", "level", "kind", "message", "acknowledged")
    return [dict(zip(keys, r)) for r in rows]


@app.post("/api/alerts/{alert_id}/ack")
def ack_alert(alert_id: int):
    with _lock:
        cur = _db.execute(
            "UPDATE alerts SET acknowledged=1 WHERE id=?", (alert_id,)
        )
        _db.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="alert not found")
    return {"ok": True, "id": alert_id}


@app.get("/api/drift/{device_id}")
def drift_report(device_id: str, metric: str = "rms", limit: int = 200):
    if metric not in ("rms", "model_score", "kurtosis"):
        raise HTTPException(status_code=400, detail="bad metric")
    with _lock:
        rows = _db.execute(
            f"SELECT {metric} FROM windows WHERE device_id=? AND {metric} IS NOT NULL "
            "ORDER BY id DESC LIMIT ?",
            (device_id, limit),
        ).fetchall()
    values = [float(r[0]) for r in reversed(rows)]
    if len(values) < 10:
        return {
            "device_id": device_id,
            "metric": metric,
            "n": len(values),
            "drift": False,
            "psi": 0.0,
            "ks": 0.0,
            "ks_pvalue": 1.0,
            "note": "insufficient windows",
        }
    mid = max(5, len(values) // 2)
    rep = drift.report(values[:mid], values[mid:])
    return {
        "device_id": device_id,
        "metric": metric,
        "n": len(values),
        "reference_n": mid,
        "current_n": len(values) - mid,
        "psi": rep.psi,
        "ks": rep.ks,
        "ks_pvalue": rep.ks_pvalue,
        "drift": rep.drift,
    }


@app.get("/api/diagnosis/{device_id}")
def device_diagnosis(device_id: str, machine_id: str | None = None):
    with _lock:
        mid = _device_machine(device_id, machine_id)
        spec = _machine_row(mid)
        row = _db.execute(
            "SELECT rms,crest,kurtosis,dom_freq FROM windows WHERE device_id=? "
            "ORDER BY id DESC LIMIT 1",
            (device_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="no windows")
    if not spec:
        raise HTTPException(status_code=404, detail="machine not configured")
    geom = diagnosis.BearingGeometry(
        rpm=spec["rpm"],
        n_balls=spec["n_balls"],
        ball_d_mm=spec["ball_d_mm"],
        pitch_d_mm=spec["pitch_d_mm"],
        contact_angle_deg=spec["contact_angle_deg"],
    )
    freqs = diagnosis.bearing_frequencies(geom)
    cls = diagnosis.diagnose(
        diagnosis.DiagnosisInput(
            rms=row[0],
            crest=row[1],
            kurtosis=row[2],
            dom_freq=row[3],
            envelope_freq=row[3],
        ),
        freqs,
    )
    return {
        "device_id": device_id,
        "machine_id": mid,
        "fault": cls,
        "frequencies": {
            "bpfo": freqs.bpfo,
            "bpfi": freqs.bpfi,
            "bsf": freqs.bsf,
            "ftf": freqs.ftf,
        },
    }


@app.get("/api/rul/{device_id}")
def device_rul(device_id: str, threshold: float | None = None, metric: str = "rms"):
    if metric not in ("rms", "kurtosis"):
        raise HTTPException(status_code=400, detail="bad metric")
    with _lock:
        spec = _machine_row(_device_machine(device_id))
        rows = _db.execute(
            f"SELECT ts,{metric} FROM windows WHERE device_id=? AND {metric} IS NOT NULL "
            "ORDER BY id DESC LIMIT 200",
            (device_id,),
        ).fetchall()
    values = [float(r[1]) for r in reversed(rows)]
    times = [float(r[0]) for r in reversed(rows)]
    if len(values) < 3:
        return {
            "device_id": device_id,
            "metric": metric,
            "valid": False,
            "rul_days": 0.0,
            "note": "insufficient windows",
        }
    limit = threshold if threshold is not None else (
        spec["rms_crit"] if spec else 0.5
    )
    est = rul.estimate(values, times, limit)
    return {
        "device_id": device_id,
        "metric": metric,
        "threshold": limit,
        "valid": est.valid,
        "slope_per_day": est.slope_per_day,
        "current": est.current,
        "rul_days": est.rul_days,
    }


@app.get("/api/models")
def list_models():
    with _lock:
        rows = _db.execute(
            "SELECT version,path,created,status,notes FROM models ORDER BY created DESC"
        ).fetchall()
    keys = ("version", "path", "created", "status", "notes")
    return [dict(zip(keys, r)) for r in rows]


@app.post("/api/models")
def register_model(payload: ModelPayload):
    with _lock:
        _db.execute(
            "INSERT INTO models(version,path,created,status,notes) VALUES(?,?,?,?,?) "
            "ON CONFLICT(version) DO UPDATE SET path=excluded.path,notes=excluded.notes,"
            "status=excluded.status",
            (payload.version, payload.path, time.time(), payload.status, payload.notes),
        )
        _db.commit()
    return {"ok": True, "version": payload.version}


def _active_rollout():
    row = _db.execute(
        "SELECT id,model_version,stage,percent,created FROM rollouts "
        "WHERE active=1 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    return dict(zip(("id", "model_version", "stage", "percent", "created"), row))


@app.get("/api/rollout")
def get_rollout():
    with _lock:
        active = _active_rollout()
        rows = _db.execute(
            "SELECT id,model_version,stage,percent,created,active FROM rollouts "
            "ORDER BY id DESC LIMIT 20"
        ).fetchall()
    keys = ("id", "model_version", "stage", "percent", "created", "active")
    return {"active": active, "history": [dict(zip(keys, r)) for r in rows]}


@app.post("/api/rollout")
def set_rollout(payload: RolloutPayload):
    stage = max(0, min(2, payload.stage))
    percent = rollout.stage_percent(stage)
    with _lock:
        _db.execute("UPDATE rollouts SET active=0 WHERE active=1")
        _db.execute(
            "INSERT INTO rollouts(model_version,stage,percent,created,active) "
            "VALUES(?,?,?,?,1)",
            (payload.model_version, stage, percent, time.time()),
        )
        _db.commit()
        active = _active_rollout()
    _broadcast({"type": "rollout", "model_version": payload.model_version, "stage": stage, "percent": percent})
    return {"ok": True, "active": active}


@app.get("/api/rollout/device/{device_id}")
def device_rollout(device_id: str):
    with _lock:
        active = _active_rollout()
        stable = _db.execute(
            "SELECT version FROM models WHERE status='stable' ORDER BY created DESC LIMIT 1"
        ).fetchone()
    if not active:
        return {
            "device_id": device_id,
            "version": stable[0] if stable else None,
            "percent": 0,
            "selected": False,
        }
    sel = rollout.selected(device_id, int(active["percent"]))
    return {
        "device_id": device_id,
        "version": active["model_version"] if sel else (stable[0] if stable else None),
        "percent": active["percent"],
        "stage": active["stage"],
        "selected": sel,
        "bucket": rollout.bucket(device_id),
    }


@app.post("/api/rollout/check")
def check_rollout(min_samples: int = 20):
    with _lock:
        active = _active_rollout()
        if not active:
            return {"action": "none", "reason": "no active rollout"}
        rows = _db.execute(
            "SELECT DISTINCT device_id FROM windows WHERE ts>=?", (active["created"],)
        ).fetchall()
        selected = [
            r[0] for r in rows if rollout.selected(r[0], int(active["percent"]))
        ]
        total = bad = 0
        for dev in selected:
            counts = _db.execute(
                "SELECT COUNT(*), SUM(CASE WHEN status IN ('warning','anomaly') THEN 1 ELSE 0 END) "
                "FROM windows WHERE device_id=? AND ts>=?",
                (dev, active["created"]),
            ).fetchone()
            total += counts[0] or 0
            bad += counts[1] or 0
        rate = bad / total if total else 0.0
        if total >= min_samples and rate > 0.25:
            new_stage = max(0, int(active["stage"]) - 1)
            _db.execute(
                "UPDATE rollouts SET stage=?,percent=? WHERE id=?",
                (new_stage, rollout.stage_percent(new_stage), active["id"]),
            )
            _db.commit()
            return {
                "action": "rollback",
                "alarm_rate": rate,
                "samples": total,
                "stage": new_stage,
                "percent": rollout.stage_percent(new_stage),
            }
        if total >= min_samples and rate < 0.05 and int(active["stage"]) < 2:
            new_stage = int(active["stage"]) + 1
            _db.execute(
                "UPDATE rollouts SET stage=?,percent=? WHERE id=?",
                (new_stage, rollout.stage_percent(new_stage), active["id"]),
            )
            _db.commit()
            return {
                "action": "advance",
                "alarm_rate": rate,
                "samples": total,
                "stage": new_stage,
                "percent": rollout.stage_percent(new_stage),
            }
    return {"action": "hold", "alarm_rate": rate, "samples": total}


@app.get("/api/metrics", response_class=PlainTextResponse)
def metrics():
    with _lock:
        total = _db.execute("SELECT COUNT(*) FROM windows").fetchone()[0]
        bad = _db.execute(
            "SELECT COUNT(*) FROM windows WHERE status IN ('warning','anomaly')"
        ).fetchone()[0]
        devices_n = _db.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
        alerts_n = _db.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        active = _active_rollout()
        device_rows = _db.execute(
            "SELECT device_id,battery_mv,rssi,last_seen FROM devices ORDER BY device_id"
        ).fetchall()
    lines = [
        "# HELP vibeguard_windows_total Ingested feature windows.",
        "# TYPE vibeguard_windows_total counter",
        f"vibeguard_windows_total {total}",
        "# HELP vibeguard_ingest_errors_total Rejected frames.",
        "# TYPE vibeguard_ingest_errors_total counter",
        f"vibeguard_ingest_errors_total {_metrics['ingest_errors']}",
        "# HELP vibeguard_anomalies_total Windows flagged warning/anomaly.",
        "# TYPE vibeguard_anomalies_total counter",
        f"vibeguard_anomalies_total {bad}",
        "# HELP vibeguard_alerts_total Alerts persisted.",
        "# TYPE vibeguard_alerts_total counter",
        f"vibeguard_alerts_total {alerts_n}",
        "# HELP vibeguard_devices Number of known devices.",
        "# TYPE vibeguard_devices gauge",
        f"vibeguard_devices {devices_n}",
        "# HELP vibeguard_rollout_percent Active staged-rollout percentage.",
        "# TYPE vibeguard_rollout_percent gauge",
        f"vibeguard_rollout_percent {int(active['percent']) if active else 0}",
        "# HELP vibeguard_battery_mv Last reported battery voltage.",
        "# TYPE vibeguard_battery_mv gauge",
    ]
    for dev, mv, rssi, seen in device_rows:
        label = dev.replace("\\", "").replace('"', '')
        if mv is not None:
            lines.append(f'vibeguard_battery_mv{{device_id="{label}"}} {mv}')
        if rssi is not None:
            lines.append(f'vibeguard_rssi_dbm{{device_id="{label}"}} {rssi}')
        if seen is not None:
            lines.append(f'vibeguard_last_seen_seconds{{device_id="{label}"}} {seen}')
    return "\n".join(lines) + "\n"


@app.get("/api/events")
async def events_stream():
    q = _subscribe()

    async def gen():
        try:
            while True:
                try:
                    event = q.get_nowait()
                except queue.Empty:
                    yield ": ping\n\n"
                    await asyncio.sleep(1.0)
                    continue
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            _unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.websocket("/ws/events")
async def ws_events(ws: WebSocket):
    await ws.accept()
    q = _subscribe()
    try:
        while True:
            try:
                event = q.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.1)
                continue
            await ws.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        _unsubscribe(q)


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
