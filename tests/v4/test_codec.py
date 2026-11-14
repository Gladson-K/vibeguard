import pytest

from gateway import codec
from v4util import KEY_HEX, run_json

KEY = bytes.fromhex(KEY_HEX)


def _frame(**kw):
    base = dict(
        device_id=7,
        seq=3,
        ts=1000,
        rms=0.125,
        peak=0.456,
        crest=3.75,
        kurtosis=4.25,
        dom_freq=87.0,
        model_score=0.42,
        battery_mv=3900,
        rssi=-70,
    )
    base.update(kw)
    return codec.LoraFrame(**base)


def test_roundtrip_and_length():
    frame = _frame()
    raw = codec.encode(frame)
    assert len(raw) == codec.FRAME_SIZE
    got, crc = codec.decode(raw)
    assert got is not None
    assert crc == codec.crc16_ccitt(raw[:30])
    assert got.device_id == 7 and got.seq == 3 and got.ts == 1000
    assert got.rms == pytest.approx(0.125)
    assert got.peak == pytest.approx(0.456)
    assert got.crest == pytest.approx(3.75)
    assert got.kurtosis == pytest.approx(4.25)
    assert got.dom_freq == pytest.approx(87.0)
    assert got.model_score == pytest.approx(0.42)
    assert got.battery_mv == 3900
    assert got.rssi == -70


def test_crc_rejects_corruption():
    raw = bytearray(codec.encode(_frame()))
    raw[14] ^= 0x01
    got, _ = codec.decode(bytes(raw))
    assert got is None


def test_signed_frame_roundtrip_and_tamper():
    frame = _frame()
    signed = codec.sign(frame, KEY)
    assert len(signed) == codec.SIGNED_FRAME_SIZE
    got, status = codec.decode_signed(signed, KEY)
    assert status == "ok" and got is not None
    bad = bytearray(signed)
    bad[2] ^= 0x01
    got, status = codec.decode_signed(bytes(bad), KEY)
    assert got is None and status == "bad_signature"


def test_sil_encode_matches_python(codec_bin):
    frame = _frame()
    data, rc, _ = run_json(
        codec_bin,
        "--device-id", frame.device_id,
        "--seq", frame.seq,
        "--ts", frame.ts,
        "--rms", frame.rms,
        "--peak", frame.peak,
        "--crest", frame.crest,
        "--kurtosis", frame.kurtosis,
        "--dom-freq", frame.dom_freq,
        "--model-score", frame.model_score,
        "--battery", frame.battery_mv,
        "--rssi", frame.rssi,
    )
    assert rc == 0
    assert data["len"] == 32
    assert data["frame_hex"] == codec.encode(frame).hex()


def test_sil_signed_matches_python(codec_bin):
    frame = _frame()
    data, rc, _ = run_json(
        codec_bin,
        "--device-id", frame.device_id,
        "--seq", frame.seq,
        "--ts", frame.ts,
        "--rms", frame.rms,
        "--peak", frame.peak,
        "--crest", frame.crest,
        "--kurtosis", frame.kurtosis,
        "--dom-freq", frame.dom_freq,
        "--model-score", frame.model_score,
        "--battery", frame.battery_mv,
        "--rssi", frame.rssi,
        "--key-hex", KEY_HEX,
    )
    assert rc == 0
    assert data["len"] == 40
    assert data["frame_hex"] == codec.sign(frame, KEY).hex()


def test_sil_decode_and_corruption(codec_bin):
    raw = codec.encode(_frame()).hex()
    data, rc, _ = run_json(codec_bin, "--decode-hex", raw)
    assert rc == 0 and data["valid"] is True and data["device_id"] == 7
    data, rc, _ = run_json(codec_bin, "--decode-hex", raw, "--corrupt")
    assert rc == 1 and data["valid"] is False
