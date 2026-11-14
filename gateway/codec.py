"""V4 compact LoRa frame codec (mirror of firmware/src/vg_core/v4/codec.cpp).

32-byte frame (little-endian)::

    version u8 | flags u8 | device_id u32 | seq u32 | ts u32
    rms u16/1000 | peak u16/1000 | crest u16/100 | kurtosis u16/100
    dom_freq u16 | model_score u16/100 | battery_mv u16 | rssi i16
    crc16-ccitt u16

A signed frame appends 8 bytes of HMAC-SHA256(key, frame).
"""

from __future__ import annotations

import hashlib
import hmac
import math
import struct
from dataclasses import asdict, dataclass

FRAME_SIZE = 32
SIGNED_FRAME_SIZE = 40


@dataclass
class LoraFrame:
    version: int = 1
    flags: int = 0
    device_id: int = 0
    seq: int = 0
    ts: int = 0
    rms: float = 0.0
    peak: float = 0.0
    crest: float = 0.0
    kurtosis: float = 0.0
    dom_freq: float = 0.0
    model_score: float = 0.0
    battery_mv: int = 0
    rssi: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


def crc16_ccitt(data: bytes, init: int = 0xFFFF) -> int:
    crc = init
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def _scale_u16(value: float, scale: float) -> int:
    if not math.isfinite(value) or value < 0:
        value = 0.0
    x = value * scale
    if x > 65535:
        x = 65535
    return int(math.floor(x + 0.5))


def encode(frame: LoraFrame) -> bytes:
    body = struct.pack(
        "<BBIIIHHHHHHHh",
        frame.version or 1,
        frame.flags & 0xFF,
        frame.device_id & 0xFFFFFFFF,
        frame.seq & 0xFFFFFFFF,
        frame.ts & 0xFFFFFFFF,
        _scale_u16(frame.rms, 1000.0),
        _scale_u16(frame.peak, 1000.0),
        _scale_u16(frame.crest, 100.0),
        _scale_u16(frame.kurtosis, 100.0),
        _scale_u16(frame.dom_freq, 1.0),
        _scale_u16(frame.model_score, 100.0),
        int(frame.battery_mv) & 0xFFFF,
        int(frame.rssi),
    )
    assert len(body) == 30
    return body + struct.pack("<H", crc16_ccitt(body))


def decode(data: bytes, crc_got: list | None = None) -> tuple[LoraFrame | None, int]:
    if len(data) < FRAME_SIZE:
        return None, 0
    body, crc = data[:30], struct.unpack_from("<H", data, 30)[0]
    if crc_got is not None:
        crc_got.append(crc)
    if crc16_ccitt(body) != crc:
        return None, crc
    (
        version,
        flags,
        device_id,
        seq,
        ts,
        rms,
        peak,
        crest,
        kurtosis,
        dom_freq,
        model_score,
        battery,
        rssi,
    ) = struct.unpack("<BBIIIHHHHHHHh", body)
    frame = LoraFrame(
        version=version,
        flags=flags,
        device_id=device_id,
        seq=seq,
        ts=ts,
        rms=rms / 1000.0,
        peak=peak / 1000.0,
        crest=crest / 100.0,
        kurtosis=kurtosis / 100.0,
        dom_freq=float(dom_freq),
        model_score=model_score / 100.0,
        battery_mv=battery,
        rssi=rssi,
    )
    return frame, crc


def sign(frame: LoraFrame, key: bytes) -> bytes:
    raw = encode(frame)
    return raw + hmac.new(key, raw, hashlib.sha256).digest()[:8]


def decode_signed(data: bytes, key: bytes) -> tuple[LoraFrame | None, str]:
    if len(data) < SIGNED_FRAME_SIZE:
        return None, "short"
    if not hmac.compare_digest(data[FRAME_SIZE:SIGNED_FRAME_SIZE], _tag(data[:FRAME_SIZE], key)):
        return None, "bad_signature"
    frame, _ = decode(data[:FRAME_SIZE])
    return frame, "ok" if frame else "bad_crc"


def _tag(raw: bytes, key: bytes) -> bytes:
    return hmac.new(key, raw, hashlib.sha256).digest()[:8]
