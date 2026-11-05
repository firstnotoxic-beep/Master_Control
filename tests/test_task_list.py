# ทดสอบ Task List Skill ด้วยไฟล์และฐานข้อมูลจำลอง
import sys
from pathlib import Path

import pytest

from core.skills import SkillRegistry


def write_config(path: Path, enabled: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = ", ".join(f'"{name}"' for name in enabled)
    path.write_text(f"enabled = [{names}]\n", encoding="utf-8")


def make_registry(tmp_path: Path, monkeypatch, *, enabled=True):
    config = tmp_path / "config" / "skills.toml"
    write_config(config, ["task_list"] if enabled else [])
    registry = SkillRegistry(
        skills_dir=Path("skills"),
        config_path=config,
        db_path=tmp_path / "db.sqlite",
    )
    module = sys.modules.get("mastercontrol_skill_task_list")
    if enabled:
        assert module is not None
        monkeypatch.setattr(module, "TASKS_ROOT", tmp_path / "data" / "tasks")
    return registry, module, config


def run_action(registry, action_id, params=None):
    prepared = registry.prepare_action("task_list", action_id, params or {})
    return registry.execute_action(prepared)


def test_task_list_is_opt_in_by_default(tmp_path, monkeypatch):
    registry, _module, _config = make_registry(tmp_path, monkeypatch, enabled=False)

    task_skill = next(item for item in registry.list_skills() if item["name"] == "task_list")

    assert task_skill["enabled"] is False
    assert task_skill["actions"]
    assert "task_list" not in registry._loaded


def test_task_list_add_list_done_and_remove(tmp_path, monkeypatch):
    registry, _module, _config = make_registry(tmp_path, monkeypatch)

    added = run_action(registry, "add", {"description": "Finish physics homework"})
    assert added["ok"] is True
    assert "Added task #1" in added["message"]

    listed = run_action(registry, "list")
    assert listed["ok"] is True
    assert "Finish physics homework" in listed["message"]

    completed = run_action(registry, "done", {"task_id": 1})
    assert completed["ok"] is True
    assert "Completed task #1" in completed["message"]

    tasks_file = _module.TASKS_ROOT / "tasks.md"
    assert "- [x] #1 Finish physics homework" in tasks_file.read_text(encoding="utf-8")

    removed = run_action(registry, "remove", {"task_id": 1})
    assert removed["ok"] is True
    assert tasks_file.read_text(encoding="utf-8") == ""


def test_task_list_rejects_path_escape_and_symlinks(tmp_path, monkeypatch):
    registry, module, _config = make_registry(tmp_path, monkeypatch)
    outside = tmp_path / "outside"
    outside.mkdir()
    tasks_root = tmp_path / "data" / "tasks"

    tasks_root.parent.mkdir(parents=True)
    try:
        tasks_root.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlink creation is unavailable on this runner")

    with pytest.raises(ValueError, match="symlink or reparse point"):
        module._tasks_path()

    tasks_root.unlink()
    tasks_root.mkdir()
    outside_file = outside / "tasks.md"
    outside_file.write_text("keep safe", encoding="utf-8")
    try:
        (tasks_root / "tasks.md").symlink_to(outside_file)
    except (OSError, NotImplementedError):
        pytest.skip("file symlink creation is unavailable on this runner")

    with pytest.raises(ValueError, match="symlink or reparse point"):
        module._tasks_path()
    assert outside_file.read_text(encoding="utf-8") == "keep safe"
    assert registry is not None


def test_task_list_rejects_invalid_description(tmp_path, monkeypatch):
    registry, module, _config = make_registry(tmp_path, monkeypatch)

    invalid_description = run_action(
        registry, "add", {"description": "first line\nsecond line"}
    )

    assert invalid_description["ok"] is False
    assert not (module.TASKS_ROOT / "tasks.md").exists()


def test_task_list_rejects_invalid_task_id(tmp_path, monkeypatch):
    registry, module, _config = make_registry(tmp_path, monkeypatch)

    invalid_id = run_action(registry, "done", {"task_id": 0})

    assert invalid_id["ok"] is False
    assert not (module.TASKS_ROOT / "tasks.md").exists()


def test_task_list_action_log_failure_blocks_file_write(tmp_path, monkeypatch):
    from core import skills

    registry, module, config = make_registry(tmp_path, monkeypatch)
    fallback = tmp_path / "skill-failures.log"
    monkeypatch.setattr(skills, "DEFAULT_FAILURE_LOG_PATH", fallback)

    def fail_log(*args, **kwargs):
        raise OSError("simulated action log failure")

    monkeypatch.setattr(registry, "_write_run_log", fail_log)
    result = run_action(registry, "add", {"description": "Must not be written"})

    assert result["ok"] is False
    assert not (module.TASKS_ROOT / "tasks.md").exists()
    assert "task_list" not in registry._loaded
    assert "task_list" not in config.read_text(encoding="utf-8")
    assert fallback.exists()
    assert "Execution blocked before Skill code ran" in fallback.read_text(encoding="utf-8")
