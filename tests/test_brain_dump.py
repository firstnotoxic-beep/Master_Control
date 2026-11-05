# ทดสอบ Brain Dump Skill ด้วยไฟล์และฐานข้อมูลจำลอง
import sys
from pathlib import Path

import pytest

from core.permissions import RiskLevel
from core.skills import SkillRegistry


def write_config(path: Path, enabled: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = ", ".join(f'"{name}"' for name in enabled)
    path.write_text(f"enabled = [{names}]\n", encoding="utf-8")


def make_registry(tmp_path: Path, monkeypatch, *, enabled=True):
    config = tmp_path / "config" / "skills.toml"
    write_config(config, ["brain_dump"] if enabled else [])
    registry = SkillRegistry(
        skills_dir=Path("skills"),
        config_path=config,
        db_path=tmp_path / "db.sqlite",
    )
    module = sys.modules.get("mastercontrol_skill_brain_dump")
    if enabled:
        assert module is not None
        data_root = tmp_path / "data"
        monkeypatch.setattr(module, "DATA_ROOT", data_root)
        monkeypatch.setattr(module, "BRAIN_DUMP_ROOT", data_root / "brain_dump")
    return registry, module, config


def run_action(registry, action_id, params):
    prepared = registry.prepare_action("brain_dump", action_id, params)
    return registry.execute_action(prepared)


def test_brain_dump_is_opt_in_by_default(tmp_path, monkeypatch):
    registry, _module, _config = make_registry(tmp_path, monkeypatch, enabled=False)

    brain_dump = next(
        item for item in registry.list_skills() if item["name"] == "brain_dump"
    )

    assert brain_dump["enabled"] is False
    assert brain_dump["actions"]
    assert "brain_dump" not in registry._loaded


def test_brain_dump_uses_only_low_risk_capabilities(tmp_path, monkeypatch):
    registry, _module, _config = make_registry(tmp_path, monkeypatch)

    assert registry.prepare_action(
        "brain_dump", "capture", {"text": "A thought"}
    ).risk == RiskLevel.SAFE
    assert registry.prepare_action(
        "brain_dump", "list", {"limit": 5}
    ).risk == RiskLevel.LOW
    assert registry.prepare_action(
        "brain_dump", "search", {"keyword": "thought"}
    ).risk == RiskLevel.LOW
    preview = registry.preview("brain_dump")
    assert all(
        set(action["requested_capabilities"]) <= {"file_read", "file_write"}
        for action in preview["actions"]
    )


def test_brain_dump_capture_is_append_only_and_list_returns_latest_n(
    tmp_path, monkeypatch
):
    registry, module, _config = make_registry(tmp_path, monkeypatch)

    first = run_action(registry, "capture", {"text": "First thought"})
    second = run_action(registry, "capture", {"text": "Second idea"})

    assert first["ok"] is True
    assert second["ok"] is True
    files = sorted((module.BRAIN_DUMP_ROOT).glob("*.md"))
    assert len(files) == 2
    assert all("T" in path.name and path.name.endswith(".md") for path in files)

    latest = run_action(registry, "list", {"limit": 1})
    assert latest["ok"] is True
    assert "Second idea" in latest["message"]
    assert "First thought" not in latest["message"]
    assert len(list(module.BRAIN_DUMP_ROOT.glob("*.md"))) == 2


def test_brain_dump_search_is_case_insensitive(tmp_path, monkeypatch):
    registry, _module, _config = make_registry(tmp_path, monkeypatch)

    captured = run_action(
        registry, "capture", {"text": "Remember the BLUE notebook"}
    )
    searched = run_action(registry, "search", {"keyword": "blue NOTE"})

    assert captured["ok"] is True
    assert searched["ok"] is True
    assert "BLUE notebook" in searched["message"]


def test_brain_dump_rejects_directory_and_file_symlinks(tmp_path, monkeypatch):
    registry, module, _config = make_registry(tmp_path, monkeypatch)
    outside = tmp_path / "outside"
    outside.mkdir()
    module.DATA_ROOT.mkdir(parents=True)

    try:
        module.BRAIN_DUMP_ROOT.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlink creation is unavailable on this runner")

    with pytest.raises(ValueError, match="symlink or reparse point"):
        module._safe_root(create=True)

    module.BRAIN_DUMP_ROOT.unlink()
    module.BRAIN_DUMP_ROOT.mkdir()
    outside_note = outside / "outside.md"
    outside_note.write_text("must remain untouched", encoding="utf-8")
    link_name = "20261105T120000000000Z-" + "a" * 32 + ".md"
    try:
        (module.BRAIN_DUMP_ROOT / link_name).symlink_to(outside_note)
    except (OSError, NotImplementedError):
        pytest.skip("file symlink creation is unavailable on this runner")

    with pytest.raises(ValueError, match="symlinks or reparse points"):
        module._note_files()
    assert outside_note.read_text(encoding="utf-8") == "must remain untouched"
    assert registry is not None


def test_brain_dump_rejects_reparse_point_directory(tmp_path, monkeypatch):
    _registry, module, _config = make_registry(tmp_path, monkeypatch)
    module.DATA_ROOT.mkdir(parents=True)

    if not hasattr(Path, "is_junction"):
        pytest.skip("junction detection is unavailable on this Python version")
    original_is_junction = Path.is_junction
    monkeypatch.setattr(
        Path,
        "is_junction",
        lambda path: path == module.BRAIN_DUMP_ROOT or original_is_junction(path),
    )

    with pytest.raises(ValueError, match="symlink or reparse point"):
        module._safe_root(create=True)


def test_brain_dump_rejects_traversal_filename(tmp_path, monkeypatch):
    _registry, module, _config = make_registry(tmp_path, monkeypatch)
    root = tmp_path / "data" / "brain_dump"
    root.mkdir(parents=True)

    with pytest.raises(ValueError, match="invalid brain dump filename"):
        module._safe_note_path("../outside.md", root)


def test_brain_dump_rejects_invalid_and_oversized_capture(tmp_path, monkeypatch):
    registry, module, _config = make_registry(tmp_path, monkeypatch)

    empty = run_action(registry, "capture", {"text": "  "})
    oversized = run_action(
        registry, "capture", {"text": "x" * (module._MAX_TEXT_LENGTH + 1)}
    )
    control = run_action(registry, "capture", {"text": "invalid\x00text"})

    assert empty["ok"] is False
    assert oversized["ok"] is False
    assert control["ok"] is False
    assert not module.BRAIN_DUMP_ROOT.exists()


def test_brain_dump_rejects_empty_search_and_invalid_list_limit(
    tmp_path, monkeypatch
):
    registry, module, _config = make_registry(tmp_path, monkeypatch)

    empty_search = run_action(registry, "search", {"keyword": "  "})
    invalid_limit = run_action(registry, "list", {"limit": 0})

    assert empty_search["ok"] is False
    assert invalid_limit["ok"] is False
    assert not module.BRAIN_DUMP_ROOT.exists()


def test_brain_dump_action_log_failure_blocks_capture(tmp_path, monkeypatch):
    from core import skills

    registry, module, config = make_registry(tmp_path, monkeypatch)
    fallback = tmp_path / "skill-failures.log"
    monkeypatch.setattr(skills, "DEFAULT_FAILURE_LOG_PATH", fallback)

    def fail_log(*args, **kwargs):
        raise OSError("simulated action log failure")

    monkeypatch.setattr(registry, "_write_run_log", fail_log)
    result = run_action(registry, "capture", {"text": "Must not be captured"})

    assert result["ok"] is False
    assert not module.BRAIN_DUMP_ROOT.exists()
    assert "brain_dump" not in registry._loaded
    assert "brain_dump" not in config.read_text(encoding="utf-8")
    assert fallback.exists()
    assert "Execution blocked before Skill code ran" in fallback.read_text(
        encoding="utf-8"
    )
