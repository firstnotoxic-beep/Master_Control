# ทดสอบ Daily Report Skill ด้วยไฟล์และฐานข้อมูลจำลอง
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from core.db import execute, init_db
from core.permissions import RiskLevel
from core.skills import SkillRegistry


def write_config(path: Path, enabled: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = ", ".join(f'"{name}"' for name in enabled)
    path.write_text(f"enabled = [{names}]\n", encoding="utf-8")


def make_registry(tmp_path: Path, monkeypatch, *, enabled=True):
    config = tmp_path / "config" / "skills.toml"
    write_config(config, ["daily_report"] if enabled else [])
    registry = SkillRegistry(
        skills_dir=Path("skills"),
        config_path=config,
        db_path=tmp_path / "registry.sqlite",
    )
    module = sys.modules.get("mastercontrol_skill_daily_report")
    if enabled:
        assert module is not None
        data_root = tmp_path / "data"
        monkeypatch.setattr(module, "DATA_ROOT", data_root)
        monkeypatch.setattr(module, "TASKS_ROOT", data_root / "tasks")
        monkeypatch.setattr(module, "BRAIN_DUMP_ROOT", data_root / "brain_dump")
        monkeypatch.setattr(module, "ACTION_LOG_DB", data_root / "mastercontrol.db")
        monkeypatch.setattr(module, "REPORTS_ROOT", data_root / "reports")
    return registry, module, config


def run_action(registry, action_id, params=None):
    prepared = registry.prepare_action("daily_report", action_id, params or {})
    return registry.execute_action(prepared)


def test_daily_report_is_opt_in_and_uses_read_write_capabilities(
    tmp_path, monkeypatch
):
    registry, _module, _config = make_registry(
        tmp_path, monkeypatch, enabled=False
    )

    skill = next(
        item for item in registry.list_skills() if item["name"] == "daily_report"
    )

    assert skill["enabled"] is False
    assert "daily_report" not in registry._loaded

    enabled_registry, _module, _config = make_registry(tmp_path / "enabled", monkeypatch)
    preview = enabled_registry.preview("daily_report")
    assert {item["id"] for item in preview["actions"]} == {
        "generate",
        "generate_for_date",
    }
    assert all(item["final_risk"] == RiskLevel.LOW.value for item in preview["actions"])
    assert all(
        set(item["requested_capabilities"]) == {"file_read", "file_write"}
        for item in preview["actions"]
    )


def test_daily_report_defaults_to_today_and_overwrites_same_date(
    tmp_path, monkeypatch
):
    registry, module, _config = make_registry(tmp_path, monkeypatch)
    report_day = date(2026, 11, 5)
    monkeypatch.setattr(module, "_today", lambda: report_day)

    first = run_action(registry, "generate")
    report_path = module.REPORTS_ROOT / f"{report_day.isoformat()}.md"
    assert first["ok"] is True
    assert report_path.is_file()
    assert len(list(module.REPORTS_ROOT.glob("*.md"))) == 1

    module.TASKS_ROOT.mkdir(parents=True)
    (module.TASKS_ROOT / "tasks.md").write_text(
        "- [ ] #1 Updated task\n", encoding="utf-8"
    )
    second = run_action(registry, "generate")

    assert second["ok"] is True
    assert len(list(module.REPORTS_ROOT.glob("*.md"))) == 1
    assert "Updated task" in report_path.read_text(encoding="utf-8")


def test_daily_report_for_date_summarizes_existing_local_sources(
    tmp_path, monkeypatch
):
    registry, module, _config = make_registry(tmp_path, monkeypatch)
    timestamp = datetime(2026, 11, 5, 12, 30, tzinfo=UTC)
    report_day = timestamp.astimezone().date()

    module.TASKS_ROOT.mkdir(parents=True)
    (module.TASKS_ROOT / "tasks.md").write_text(
        "- [ ] #1 Pending homework\n- [x] #2 Finished task\n",
        encoding="utf-8",
    )

    module.BRAIN_DUMP_ROOT.mkdir(parents=True)
    stamp = timestamp.strftime("%Y%m%dT%H%M%S%fZ")
    note_name = f"{stamp}-{'a' * 32}.md"
    (module.BRAIN_DUMP_ROOT / note_name).write_text(
        f"# {timestamp.isoformat()}\n\nRemember the science project\n",
        encoding="utf-8",
    )
    other_day = datetime(2026, 11, 4, 12, 30, tzinfo=UTC)
    other_name = f"{other_day.strftime('%Y%m%dT%H%M%S%fZ')}-{'b' * 32}.md"
    (module.BRAIN_DUMP_ROOT / other_name).write_text(
        "Yesterday's note\n", encoding="utf-8"
    )

    init_db(module.ACTION_LOG_DB)
    execute(
        """
        INSERT INTO action_log (action, details, risk_level, status, actor, created_at)
        VALUES (?, '', 'LOW', 'success', 'test', ?)
        """,
        ("task_list.list", timestamp.strftime("%Y-%m-%d %H:%M:%S")),
        module.ACTION_LOG_DB,
    )

    generated = run_action(
        registry, "generate_for_date", {"date": report_day.isoformat()}
    )
    report_path = module.REPORTS_ROOT / f"{report_day.isoformat()}.md"
    content = report_path.read_text(encoding="utf-8")

    assert generated["ok"] is True
    assert "Pending homework" in content
    assert "Finished task" in content
    assert "Remember the science project" in content
    assert "Yesterday's note" not in content
    assert "task_list.list" in content
    assert "current state at report time" in content


def test_daily_report_marks_missing_and_empty_sources_as_no_data(
    tmp_path, monkeypatch
):
    registry, module, _config = make_registry(tmp_path, monkeypatch)
    module.TASKS_ROOT.mkdir(parents=True)
    (module.TASKS_ROOT / "tasks.md").write_text("", encoding="utf-8")
    module.BRAIN_DUMP_ROOT.mkdir(parents=True)
    init_db(module.ACTION_LOG_DB)

    result = run_action(
        registry, "generate_for_date", {"date": "2026-11-05"}
    )
    content = (
        module.REPORTS_ROOT / "2026-11-05.md"
    ).read_text(encoding="utf-8")

    assert result["ok"] is True
    assert content.count("ไม่มีข้อมูล (no data)") == 3


def test_daily_report_rejects_invalid_calendar_date_without_writing(
    tmp_path, monkeypatch
):
    registry, module, _config = make_registry(tmp_path, monkeypatch)

    result = run_action(
        registry, "generate_for_date", {"date": "2026-02-30"}
    )

    assert result["ok"] is False
    assert "valid calendar date" in result["message"]
    assert not module.REPORTS_ROOT.exists()
    assert "daily_report" in registry._loaded


def test_daily_report_rejects_source_and_output_path_escape(
    tmp_path, monkeypatch
):
    _registry, module, _config = make_registry(tmp_path, monkeypatch)
    module.DATA_ROOT.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()

    monkeypatch.setattr(module, "TASKS_ROOT", outside / "tasks")
    with pytest.raises(ValueError, match="directly inside data"):
        module._safe_source_root(module.TASKS_ROOT)

    monkeypatch.setattr(module, "REPORTS_ROOT", outside / "reports")
    with pytest.raises(ValueError, match="directly inside data"):
        module._reports_root(create=True)


def test_daily_report_action_log_failure_blocks_report_creation(
    tmp_path, monkeypatch
):
    from core import skills

    registry, module, config = make_registry(tmp_path, monkeypatch)
    fallback = tmp_path / "skill-failures.log"
    monkeypatch.setattr(skills, "DEFAULT_FAILURE_LOG_PATH", fallback)

    def fail_log(*args, **kwargs):
        raise OSError("simulated action log failure")

    monkeypatch.setattr(registry, "_write_run_log", fail_log)
    result = run_action(registry, "generate")

    assert result["ok"] is False
    assert not module.REPORTS_ROOT.exists()
    assert "daily_report" not in registry._loaded
    assert "daily_report" not in config.read_text(encoding="utf-8")
    assert fallback.exists()
    assert "Execution blocked before Skill code ran" in fallback.read_text(
        encoding="utf-8"
    )
