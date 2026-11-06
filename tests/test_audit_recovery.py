# ทดสอบ Audit Timeline, config recovery และ failure handling
from __future__ import annotations

from pathlib import Path

import pytest

from core.approval import approve, create_approval, pending
from core.audit import query_action_log
from core.config_backup import (
    create_config_backup,
    execute_approved_config_restore,
    request_config_restore,
)
from core.db import execute, fetch_one, init_db
from core.skills import SkillRegistry


def _write_skill(root: Path, name: str, source: str) -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "skill.toml").write_text(
        f"""
name = "{name}"
version = "1.0.0"
description = "Recovery test Skill"
enabled-by-default = false

[[actions]]
id = "run"
description = "Run a controlled test action."
risk = "SAFE"
capabilities = ["file_write"]

[actions.params]
value = "str"
""".lstrip(),
        encoding="utf-8",
    )
    (folder / "skill.py").write_text(source, encoding="utf-8")
    return folder


def _write_enabled(path: Path, name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'enabled = ["{name}"]\n', encoding="utf-8")


def test_audit_filters_by_date_skill_and_result(tmp_path):
    database = tmp_path / "audit.db"
    init_db(database)
    execute(
        """
        INSERT INTO action_log (action, details, risk_level, status, actor, created_at)
        VALUES (?, '', 'LOW', ?, 'skill', ?)
        """,
        ("skill.alpha.capture", "completed", "2026-11-01 10:00:00"),
        database,
    )
    execute(
        """
        INSERT INTO action_log (action, details, risk_level, status, actor, created_at)
        VALUES (?, '', 'LOW', ?, 'skill', ?)
        """,
        ("skill.beta.capture", "failed", "2026-11-02 10:00:00"),
        database,
    )
    execute(
        """
        INSERT INTO action_log (action, details, risk_level, status, actor, created_at)
        VALUES (?, '', 'LOW', ?, 'skill', ?)
        """,
        ("skill.alpha.capture", "failed", "2026-11-03 10:00:00"),
        database,
    )

    rows = query_action_log(
        database,
        date_from="2026-11-01",
        date_to="2026-11-03",
        skill="alpha",
        result="completed",
    )

    assert len(rows) == 1
    assert rows[0]["action"] == "skill.alpha.capture"
    assert rows[0]["status"] == "completed"


def test_audit_rejects_invalid_date_skill_and_unbounded_limit(tmp_path):
    database = tmp_path / "audit.db"
    init_db(database)

    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        query_action_log(database, date_from="yesterday")
    with pytest.raises(ValueError, match="Skill name"):
        query_action_log(database, skill="../unsafe")
    with pytest.raises(ValueError, match="limit"):
        query_action_log(database, limit=10_000)


def test_config_backup_restore_requires_high_approval_and_saves_rollback(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "skills.toml").write_text(
        'enabled = ["quick_note"]\n', encoding="utf-8"
    )
    database = tmp_path / "mastercontrol.db"
    backup_dir = tmp_path / "data" / "backups"

    backup = create_config_backup(config_dir, backup_dir)
    (config_dir / "skills.toml").write_text("enabled = []\n", encoding="utf-8")
    approval_id = request_config_restore(backup.name, database, backup_dir)

    blocked = execute_approved_config_restore(
        approval_id, database, config_dir, backup_dir
    )
    assert blocked["ok"] is False
    assert (config_dir / "skills.toml").read_text(encoding="utf-8") == "enabled = []\n"

    approve(approval_id, db_path=database)
    restored = execute_approved_config_restore(
        approval_id, database, config_dir, backup_dir
    )

    assert restored["ok"] is True
    assert (config_dir / "skills.toml").read_text(encoding="utf-8") == 'enabled = ["quick_note"]\n'
    rollback = backup_dir / restored["rollback_backup"]
    assert rollback.is_file()
    assert 'enabled = []' in rollback.read_text(encoding="utf-8")


def test_config_restore_rejects_corrupt_backup_before_requesting_approval(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "modes.toml").write_text("closeable = []\n", encoding="utf-8")
    backup_dir = tmp_path / "data" / "backups"
    backup = create_config_backup(config_dir, backup_dir)
    backup.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ValueError, match="valid JSON"):
        request_config_restore(backup.name, tmp_path / "db.sqlite", backup_dir)


def test_expired_approval_is_marked_and_cannot_be_approved(tmp_path):
    database = tmp_path / "approvals.db"
    approval_id = create_approval("test_medium", "{}", "MEDIUM", database)
    execute(
        """
        UPDATE approvals SET created_at = datetime('now', '-2 days')
        WHERE id = ?
        """,
        (approval_id,),
        database,
    )

    assert pending(database) == []
    approval = fetch_one(
        "SELECT status, decided_by FROM approvals WHERE id = ?",
        (approval_id,),
        database,
    )
    action = fetch_one(
        "SELECT status, actor FROM action_log WHERE id = "
        "(SELECT action_log_id FROM approvals WHERE id = ?)",
        (approval_id,),
        database,
    )
    assert approval["status"] == "expired"
    assert approval["decided_by"] == "system"
    assert action["status"] == "expired"
    assert action["actor"] == "system"
    with pytest.raises(ValueError, match="หมดอายุ"):
        approve(approval_id, db_path=database)


def test_skill_crash_mid_run_disables_skill_and_logs_failure(tmp_path):
    skills_dir = tmp_path / "skills"
    config = tmp_path / "config" / "skills.toml"
    database = tmp_path / "data" / "mastercontrol.db"
    _write_skill(
        skills_dir,
        "crasher",
        """
def run(action_id, params):
    raise RuntimeError("simulated mid-run crash")

def verify(action_id, params, result):
    return False
""",
    )
    _write_enabled(config, "crasher")
    registry = SkillRegistry(skills_dir, config, database)

    prepared = registry.prepare_action("crasher", "run", {"value": "test"})
    result = registry.execute_action(prepared)

    assert result["ok"] is False
    assert "crasher" not in registry._loaded
    assert "crasher" not in config.read_text(encoding="utf-8")
    state = fetch_one(
        "SELECT enabled FROM skill_state WHERE name = 'crasher'",
        db_path=database,
    )
    logged = fetch_one(
        "SELECT status, details FROM action_log WHERE action = ? ORDER BY id DESC",
        (prepared.action_key,),
        database,
    )
    assert state["enabled"] == 0
    assert logged["status"] == "failed"
    assert "simulated mid-run crash" in logged["details"]


def test_action_log_write_failure_blocks_skill_before_run(tmp_path, monkeypatch):
    from core import skills as skills_module

    skills_dir = tmp_path / "skills"
    config = tmp_path / "config" / "skills.toml"
    database = tmp_path / "data" / "mastercontrol.db"
    marker = tmp_path / "ran.txt"
    _write_skill(
        skills_dir,
        "log_guard",
        f"""
from pathlib import Path

def run(action_id, params):
    Path({str(marker)!r}).write_text("ran", encoding="utf-8")
    return {{"ok": True, "message": "ran"}}

def verify(action_id, params, result):
    return True
""",
    )
    _write_enabled(config, "log_guard")
    registry = SkillRegistry(skills_dir, config, database)
    prepared = registry.prepare_action("log_guard", "run", {"value": "test"})
    monkeypatch.setattr(
        skills_module,
        "DEFAULT_FAILURE_LOG_PATH",
        tmp_path / "failure.log",
    )

    def fail_log(*args, **kwargs):
        raise OSError("simulated action_log database failure")

    monkeypatch.setattr(registry, "_write_run_log", fail_log)
    result = registry.execute_action(prepared)

    assert result["ok"] is False
    assert not marker.exists()
    assert "log_guard" not in registry._loaded
    assert (tmp_path / "failure.log").is_file()


def test_fallback_failure_log_stops_at_size_limit_without_truncating(tmp_path, monkeypatch):
    from core import skills as skills_module

    log_path = tmp_path / "failure.log"
    original = "x" * 64
    log_path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(skills_module, "DEFAULT_FAILURE_LOG_PATH", log_path)
    monkeypatch.setattr(skills_module, "MAX_FAILURE_LOG_BYTES", 64)
    registry = object.__new__(SkillRegistry)

    with pytest.raises(OSError, match="1 MiB safety limit"):
        registry._write_plain_failure_log("skill.demo.run", "failure")

    assert log_path.read_text(encoding="utf-8") == original


def test_config_restore_is_registered_as_high_risk():
    from core.permissions import RiskLevel, requires_approval, risk_for_action

    assert risk_for_action("config_restore") == RiskLevel.HIGH
    assert requires_approval("config_restore") is True
