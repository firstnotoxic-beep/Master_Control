# จัดการกฎแจ้งเตือนแบบ local-first พร้อม anti-spam และการรับทราบของผู้ใช้
from __future__ import annotations

import json
import logging
import platform
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from core.db import DEFAULT_DB_PATH, execute, fetch_all, fetch_one, init_db
from core.notify import NotificationLevel, send_notification

LOGGER = logging.getLogger(__name__)
DEFAULT_CONFIG_PATH = Path("config/alerts.toml")


def _parse_time(value: str) -> tuple[int, int]:
    hour, minute = (int(part) for part in value.split(":", 1))
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(f"เวลาไม่ถูกต้อง: {value}")
    return hour, minute


def load_alert_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    import tomllib

    path = Path(config_path)
    if not path.exists():
        return {
            "bedtime": {"enabled": False, "time": "22:15", "interval_minutes": 15, "max_repeats": 3},
            "deadline": {"enabled": True, "normal_hours": 24, "warning_hours": 2, "critical_minutes": 30, "interval_minutes": 15, "daily_max": 20},
            "vip": {"enabled": True, "keywords": ["urgent", "ด่วน"], "senders": [], "interval_minutes": 15, "daily_max": 20},
            "quiet_hours": {"enabled": True, "start": "23:00", "end": "07:00"},
        }
    try:
        with path.open("rb") as config_file:
            config = tomllib.load(config_file)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"อ่าน alerts config ไม่ได้: {error}") from error
    bedtime = config.setdefault("bedtime", {})
    _parse_time(str(bedtime.get("time", "22:15")))
    quiet = config.setdefault("quiet_hours", {})
    _parse_time(str(quiet.get("start", "23:00")))
    _parse_time(str(quiet.get("end", "07:00")))
    return config


def _iso(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat()


def _within_quiet_hours(now: datetime, config: dict[str, Any]) -> bool:
    quiet = config.get("quiet_hours", {})
    if not quiet.get("enabled", True):
        return False
    start = _parse_time(str(quiet.get("start", "23:00")))
    end = _parse_time(str(quiet.get("end", "07:00")))
    current = now.hour * 60 + now.minute
    start_minutes = start[0] * 60 + start[1]
    end_minutes = end[0] * 60 + end[1]
    return current >= start_minutes or current < end_minutes if start_minutes > end_minutes else start_minutes <= current < end_minutes


def set_alert_setting(key: str, value: str, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    init_db(db_path)
    execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value), db_path)


def get_alert_setting(key: str, db_path: str | Path = DEFAULT_DB_PATH) -> str | None:
    row = fetch_one("SELECT value FROM settings WHERE key = ?", (key,), db_path)
    return row["value"] if row else None


class AlertEngine:
    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        config_path: str | Path = DEFAULT_CONFIG_PATH,
        clock: Callable[[], datetime] | None = None,
        notifier: Callable[..., dict[str, str]] = send_notification,
    ) -> None:
        self.db_path = db_path
        self.config_path = config_path
        self.clock = clock or datetime.now
        self.notifier = notifier
        init_db(db_path)

    def evaluate(self, now: datetime | None = None) -> list[int]:
        current = now or self.clock()
        config = load_alert_config(self.config_path)
        event_ids: list[int] = []
        if config.get("bedtime", {}).get("enabled", False):
            event_id = self._evaluate_bedtime(current, config)
            if event_id:
                event_ids.append(event_id)
        if config.get("deadline", {}).get("enabled", True):
            event_ids.extend(self._evaluate_deadlines(current, config))
        return event_ids

    def process_vip(self, sender: str, message: str, now: datetime | None = None) -> int | None:
        current = now or self.clock()
        config = load_alert_config(self.config_path).get("vip", {})
        if not config.get("enabled", True):
            return None
        senders = {str(item).casefold() for item in config.get("senders", [])}
        keywords = [str(item).casefold() for item in config.get("keywords", [])]
        if senders and sender.casefold() not in senders:
            return None
        if not any(keyword in message.casefold() for keyword in keywords):
            return None
        return self._emit(
            rule_type="vip",
            dedupe_key=f"vip:{sender}:{message}",
            title=f"VIP message จาก {sender}",
            message=message,
            level=NotificationLevel.CRITICAL,
            now=current,
            interval_minutes=int(config.get("interval_minutes", 15)),
            daily_max=int(config.get("daily_max", 20)),
            bypass_quiet=True,
        )

    def _evaluate_bedtime(self, now: datetime, config: dict[str, Any]) -> int | None:
        bedtime = config["bedtime"]
        hour, minute = _parse_time(str(bedtime.get("time", "22:15")))
        if now.hour * 60 + now.minute < hour * 60 + minute:
            return None
        if get_alert_setting("vacation_mode", self.db_path) == "on":
            return None
        if get_alert_setting("skip_bedtime", self.db_path) == now.date().isoformat():
            return None
        return self._emit(
            "bedtime",
            f"bedtime:{now.date().isoformat()}",
            "Bedtime reminder",
            "ถึงเวลาพักผ่อนแล้ว",
            NotificationLevel.NORMAL,
            now,
            int(bedtime.get("interval_minutes", 15)),
            int(bedtime.get("max_repeats", 3)),
            bypass_quiet=False,
        )

    def _evaluate_deadlines(self, now: datetime, config: dict[str, Any]) -> list[int]:
        deadline = config["deadline"]
        result: list[int] = []
        for task in fetch_all(
            "SELECT id, description, due_at FROM tasks WHERE status NOT IN ('completed', 'done') AND due_at IS NOT NULL",
            db_path=self.db_path,
        ):
            try:
                due_at = datetime.fromisoformat(task["due_at"])
            except ValueError:
                LOGGER.warning("ข้าม task due_at ไม่ถูกต้อง: %s", task["id"])
                continue
            remaining = due_at - now
            hours = remaining.total_seconds() / 3600
            normal_hours = float(deadline.get("normal_hours", 24))
            if hours > normal_hours or hours < 0:
                continue
            critical_minutes = float(deadline.get("critical_minutes", 30))
            level = NotificationLevel.CRITICAL if hours * 60 <= critical_minutes else (
                NotificationLevel.WARNING if hours <= float(deadline.get("warning_hours", 2)) else NotificationLevel.NORMAL
            )
            event_id = self._emit(
                "deadline",
                f"deadline:{task['id']}",
                "Task deadline warning",
                f"{task['description']} เหลือเวลา {max(0, int(remaining.total_seconds() // 60))} นาที",
                level,
                now,
                int(deadline.get("interval_minutes", 15)),
                int(deadline.get("daily_max", 20)),
                bypass_quiet=level == NotificationLevel.CRITICAL,
            )
            if event_id:
                result.append(event_id)
        return result

    def _emit(
        self,
        rule_type: str,
        dedupe_key: str,
        title: str,
        message: str,
        level: NotificationLevel,
        now: datetime,
        interval_minutes: int,
        daily_max: int,
        bypass_quiet: bool,
    ) -> int | None:
        rule_id = self._ensure_rule(rule_type, daily_max)
        event = fetch_one(
            "SELECT * FROM alert_events WHERE dedupe_key = ? AND event_date = ? ORDER BY id DESC LIMIT 1",
            (dedupe_key, now.date().isoformat()),
            self.db_path,
        )
        if event and event["status"] == "acknowledged":
            return None
        if event and event["snoozed_until"] and datetime.fromisoformat(event["snoozed_until"]) > now:
            return None
        if not bypass_quiet and _within_quiet_hours(now, load_alert_config(self.config_path)):
            return None
        if (
            event
            and event["cooldown_until"]
            and datetime.fromisoformat(event["cooldown_until"]) > now
            and event["level"] == level.value
        ):
            return None
        if event and event["repeat_count"] >= daily_max > 0:
            return None
        if (
            event
            and event["level"] == level.value
            and event["last_sent"]
            and datetime.fromisoformat(event["last_sent"]) + timedelta(minutes=interval_minutes) > now
        ):
            return None
        event_id = event["id"] if event else execute(
            """
            INSERT INTO alert_events
                (rule_id, dedupe_key, level, title, message, status, first_seen, event_date)
            VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (rule_id, dedupe_key, level.value, title, message, _iso(now), now.date().isoformat()),
            self.db_path,
        )
        try:
            self.notifier(title, message, level, self.db_path)
            if level == NotificationLevel.CRITICAL:
                self._critical_extras(title, message)
        except (ImportError, OSError, RuntimeError, ValueError) as error:
            LOGGER.error("alert notifier failed: %s", error)
        execute(
            """
            UPDATE alert_events
            SET level = ?, title = ?, message = ?, last_sent = ?, repeat_count = repeat_count + 1,
                cooldown_until = ?
            WHERE id = ?
            """,
            (level.value, title, message, _iso(now), _iso(now + timedelta(minutes=interval_minutes)), event_id),
            self.db_path,
        )
        return event_id

    @staticmethod
    def _critical_extras(title: str, message: str) -> None:
        if platform.system() != "Windows":
            return
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except (ImportError, RuntimeError, OSError):
            LOGGER.warning("เล่นเสียง critical ไม่สำเร็จ")
        try:
            import threading
            import tkinter
            from tkinter import messagebox

            def show_popup() -> None:
                root = tkinter.Tk()
                root.withdraw()
                messagebox.showwarning(title, message, parent=root)
                root.destroy()

            threading.Thread(target=show_popup, daemon=True).start()
        except (ImportError, RuntimeError, OSError):
            LOGGER.warning("แสดง critical popup ไม่สำเร็จ")

    def _ensure_rule(self, rule_type: str, daily_max: int) -> int:
        name = f"default:{rule_type}"
        row = fetch_one("SELECT id FROM alert_rules WHERE name = ?", (name,), self.db_path)
        if row:
            return row["id"]
        return execute(
            """
            INSERT INTO alert_rules (rule_type, name, config_json, daily_max)
            VALUES (?, ?, ?, ?)
            """,
            (rule_type, name, json.dumps({"source": "config"}), daily_max),
            self.db_path,
        )

    def acknowledge(self, event_id: int) -> None:
        execute(
            "UPDATE alert_events SET status = 'acknowledged', acknowledged_at = ? WHERE id = ?",
            (_iso(self.clock()), event_id),
            self.db_path,
        )

    def snooze(self, event_id: int, minutes: int) -> None:
        if minutes not in {15, 30, 60}:
            raise ValueError("snooze ได้เฉพาะ 15, 30 หรือ 60 นาที")
        execute(
            "UPDATE alert_events SET snoozed_until = ?, status = 'active' WHERE id = ?",
            (_iso(self.clock() + timedelta(minutes=minutes)), event_id),
            self.db_path,
        )

    def active_events(self) -> list[Any]:
        return fetch_all(
            "SELECT * FROM alert_events WHERE status = 'active' ORDER BY first_seen DESC",
            db_path=self.db_path,
        )

    def history(self, limit: int = 50) -> list[Any]:
        return fetch_all(
            "SELECT * FROM alert_events ORDER BY id DESC LIMIT ?",
            (limit,),
            self.db_path,
        )


def acknowledge_alert(event_id: int, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    AlertEngine(db_path).acknowledge(event_id)


def snooze_alert(event_id: int, minutes: int, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    AlertEngine(db_path).snooze(event_id, minutes)
