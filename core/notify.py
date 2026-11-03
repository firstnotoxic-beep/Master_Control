# ส่งการแจ้งเตือนผ่าน Windows toast และ Discord โดยไม่ทำให้แอปหยุดเมื่อช่องทางล้มเหลว
from __future__ import annotations

import logging
import os
import platform
from enum import StrEnum
from pathlib import Path

import requests
from dotenv import load_dotenv

from core.db import DEFAULT_DB_PATH, execute, init_db

logger = logging.getLogger(__name__)
load_dotenv()


class NotificationLevel(StrEnum):
    NORMAL = "Normal"
    WARNING = "Warning"
    CRITICAL = "Critical"


def send_notification(
    title: str,
    message: str,
    level: NotificationLevel = NotificationLevel.NORMAL,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, str]:
    init_db(db_path)
    results: dict[str, str] = {}
    for channel, sender in (("windows_toast", _send_windows_toast), ("discord", _send_discord)):
        try:
            sender(title, message, level)
            results[channel] = "sent"
            execute(
                """
                INSERT INTO notifications (channel, level, title, message, status)
                VALUES (?, ?, ?, ?, 'sent')
                """,
                (channel, level.value, title, message),
                db_path,
            )
        except (ImportError, OSError, RuntimeError, requests.RequestException) as error:
            logger.error("%s notification failed: %s", channel, error)
            results[channel] = "failed"
            execute(
                """
                INSERT INTO notifications
                    (channel, level, title, message, status, error)
                VALUES (?, ?, ?, ?, 'failed', ?)
                """,
                (channel, level.value, title, message, str(error)),
                db_path,
            )
    return results


def _send_windows_toast(title: str, message: str, level: NotificationLevel) -> None:
    if platform.system() != "Windows":
        raise RuntimeError("Windows toast ใช้ได้เฉพาะ Windows")
    from winotify import Notification

    toast = Notification(app_id="MasterControl", title=title, msg=message)
    toast.show()


def _send_discord(title: str, message: str, level: NotificationLevel) -> None:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        raise RuntimeError("ยังไม่ได้ตั้งค่า DISCORD_WEBHOOK_URL ใน .env")
    response = requests.post(
        webhook_url,
        json={"content": f"**[{level.value}] {title}**\n{message}"},
        timeout=10,
    )
    response.raise_for_status()
