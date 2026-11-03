# ทดสอบ alert engine ด้วย fake clock โดยไม่ใช้การ sleep จริง
from datetime import datetime, timedelta

from core.alerts import AlertEngine
from core.db import execute, fetch_one, init_db


def _config(path, bedtime_time="22:15"):
    path.write_text(
        f"""
[bedtime]
enabled = true
time = "{bedtime_time}"
interval_minutes = 15
max_repeats = 2

[deadline]
enabled = true
normal_hours = 24
warning_hours = 2
critical_minutes = 30
interval_minutes = 15
daily_max = 5

[vip]
enabled = true
keywords = ["urgent", "ด่วน"]
senders = ["boss"]

[quiet_hours]
enabled = false
start = "23:00"
end = "07:00"
""",
        encoding="utf-8",
    )


def test_bedtime_interval_and_max_repeats(tmp_path):
    db_path = tmp_path / "alerts.db"
    config_path = tmp_path / "alerts.toml"
    _config(config_path)
    sent = []
    now = datetime(2026, 11, 3, 22, 15)
    engine = AlertEngine(db_path, config_path, clock=lambda: now, notifier=lambda *args: sent.append(args))

    engine.evaluate(now)
    engine.evaluate(now + timedelta(minutes=5))
    engine.evaluate(now + timedelta(minutes=15))
    engine.evaluate(now + timedelta(minutes=30))

    assert len(sent) == 2
    assert fetch_one("SELECT repeat_count FROM alert_events", db_path=db_path)["repeat_count"] == 2


def test_deadline_escalates_and_ack_stops_repeats(tmp_path):
    db_path = tmp_path / "alerts.db"
    config_path = tmp_path / "alerts.toml"
    _config(config_path)
    init_db(db_path)
    now = datetime(2026, 11, 3, 12, 0)
    execute(
        "INSERT INTO tasks (description, due_at) VALUES (?, ?)",
        ("ส่งงาน", (now + timedelta(hours=1)).isoformat()),
        db_path,
    )
    sent = []
    engine = AlertEngine(db_path, config_path, clock=lambda: now, notifier=lambda *args: sent.append(args))

    engine.evaluate(now)
    engine.evaluate(now + timedelta(minutes=15))
    engine.evaluate(now + timedelta(minutes=31))
    event_id = engine.active_events()[0]["id"]
    engine.acknowledge(event_id)
    engine.evaluate(now + timedelta(minutes=46))

    assert [item[2].value for item in sent] == ["Warning", "Warning", "Critical"]
    assert len(engine.active_events()) == 0


def test_snooze_and_vacation_mode(tmp_path):
    db_path = tmp_path / "alerts.db"
    config_path = tmp_path / "alerts.toml"
    _config(config_path)
    now = datetime(2026, 11, 3, 22, 15)
    sent = []
    engine = AlertEngine(db_path, config_path, clock=lambda: now, notifier=lambda *args: sent.append(args))

    engine.evaluate(now)
    event_id = engine.active_events()[0]["id"]
    engine.snooze(event_id, 15)
    engine.evaluate(now + timedelta(minutes=10))
    engine.evaluate(now + timedelta(minutes=16))
    assert len(sent) == 2

    execute("DELETE FROM alert_events", db_path=db_path)
    execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('vacation_mode', 'on')", db_path=db_path)
    engine.evaluate(now + timedelta(days=1))
    assert len(sent) == 2


def test_failing_notifier_does_not_crash(tmp_path):
    db_path = tmp_path / "alerts.db"
    config_path = tmp_path / "alerts.toml"
    _config(config_path)
    engine = AlertEngine(
        db_path,
        config_path,
        clock=lambda: datetime(2026, 11, 3, 22, 15),
        notifier=lambda *args: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    ids = engine.evaluate()

    assert ids
    assert engine.active_events()[0]["repeat_count"] == 1


def test_vip_keyword_and_sender_allowlist(tmp_path):
    db_path = tmp_path / "alerts.db"
    config_path = tmp_path / "alerts.toml"
    _config(config_path)
    sent = []
    engine = AlertEngine(db_path, config_path, notifier=lambda *args: sent.append(args))

    assert engine.process_vip("unknown", "urgent") is None
    assert engine.process_vip("boss", "ด่วน โปรดโทรกลับ") is not None
    assert len(sent) == 1
