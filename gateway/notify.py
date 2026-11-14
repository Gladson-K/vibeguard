"""Optional Telegram/email alert fan-out.

Configured entirely through environment variables; if they are absent this is a
no-op, which keeps tests and local runs offline. Secrets are never logged.
"""

from __future__ import annotations

import json
import os
import smtplib
import threading
import urllib.request
from email.message import EmailMessage


def _telegram(text: str) -> None:
    token = os.environ.get("VG_TELEGRAM_TOKEN")
    chat_id = os.environ.get("VG_TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    body = json.dumps({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10):
        pass


def _email(text: str) -> None:
    host = os.environ.get("VG_SMTP_HOST")
    to_addr = os.environ.get("VG_ALERT_EMAIL")
    if not host or not to_addr:
        return
    msg = EmailMessage()
    msg["Subject"] = "VibeGuard alert"
    msg["From"] = os.environ.get("VG_SMTP_FROM", "vibeguard@localhost")
    msg["To"] = to_addr
    msg.set_content(text)
    port = int(os.environ.get("VG_SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=10) as smtp:
        user = os.environ.get("VG_SMTP_USER")
        if user:
            smtp.starttls()
            smtp.login(user, os.environ.get("VG_SMTP_PASSWORD", ""))
        smtp.send_message(msg)


def _send(text: str) -> None:
    for fn in (_telegram, _email):
        try:
            fn(text)
        except Exception as exc:  # noqa: BLE001 - notification must never break ingest
            print("notify failed:", type(exc).__name__)


def send_alert(device_id: str, level: str, message: str) -> None:
    if level not in ("warning", "critical"):
        return
    text = f"[{level.upper()}] {device_id}: {message}"
    threading.Thread(target=_send, args=(text,), daemon=True).start()
