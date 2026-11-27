# ทดสอบ diagnostics แบบไม่แก้ไขข้อมูลถาวร
import json
import shutil
from pathlib import Path

import pytest

from core import diagnostics
from core.db import fetch_one, init_db


def test_diagnostics_fails_when_database_is_unreachable(tmp_path):
    result = diagnostics.run_diagnostics(
        db_path=tmp_path / "missing.db",
        skills_dir=tmp_path / "skills",
        data_dir=tmp_path / "data",
    )

    assert result["status"] == "FAIL"
    assert result["read_only"] is True
    assert result["persistent_changes"] is False
    database_check = next(item for item in result["checks"] if item["name"] == "database")
    assert database_check["status"] == "FAIL"


def test_diagnostics_warns_for_invalid_skill_manifest(tmp_path):
    database = tmp_path / "data" / "mastercontrol.db"
    init_db(database)
    broken = tmp_path / "skills" / "broken"
    broken.mkdir(parents=True)
    (broken / "skill.toml").write_text("not valid = [", encoding="utf-8")

    result = diagnostics.run_diagnostics(
        db_path=database,
        skills_dir=tmp_path / "skills",
        data_dir=tmp_path / "data",
    )

    manifest_check = next(
        item for item in result["checks"] if item["name"] == "skill_manifest:broken"
    )
    assert result["status"] in {"WARN", "FAIL"}
    assert manifest_check["status"] == "WARN"
    assert "Invalid manifest" in manifest_check["message"]


def test_diagnostics_reports_read_only_data_folder(tmp_path, monkeypatch):
    database = tmp_path / "data" / "mastercontrol.db"
    init_db(database)
    tasks_directory = tmp_path / "data" / "tasks"
    tasks_directory.mkdir(parents=True)
    original_probe = diagnostics._probe_directory_writable

    def probe(directory):
        if directory == tasks_directory:
            raise PermissionError("simulated read-only folder")
        original_probe(directory)

    monkeypatch.setattr(diagnostics, "_probe_directory_writable", probe)
    result = diagnostics.run_diagnostics(
        db_path=database,
        skills_dir=tmp_path / "skills",
        data_dir=tmp_path / "data",
    )

    tasks_check = next(
        item for item in result["checks"] if item["name"] == "data_dir:tasks"
    )
    assert tasks_check["status"] == "WARN"
    assert "not writable" in tasks_check["message"]
    assert result["persistent_changes"] is False


def test_diagnostics_action_log_probe_is_rolled_back(tmp_path):
    database = tmp_path / "data" / "mastercontrol.db"
    init_db(database)

    result = diagnostics.run_diagnostics(
        db_path=database,
        skills_dir=tmp_path / "skills",
        data_dir=tmp_path / "data",
    )

    count = fetch_one(
        "SELECT COUNT(*) AS count FROM action_log WHERE action = '__diagnostic_probe__'",
        db_path=database,
    )
    assert count["count"] == 0
    write_check = next(
        item for item in result["checks"] if item["name"] == "action_log_writable"
    )
    assert write_check["status"] == "PASS"


def test_diagnostics_cli_returns_json_without_migrating_database(tmp_path, capsys):
    database = tmp_path / "data" / "mastercontrol.db"
    init_db(database)

    exit_code = diagnostics.main(
        ["check", "--db", str(database), "--skills-dir", str(tmp_path / "skills"),
         "--data-dir", str(tmp_path / "data")]
    )

    output = capsys.readouterr()
    result = json.loads(output.out)
    assert exit_code == 0
    assert result["read_only"] is True
    assert result["persistent_changes"] is False


@pytest.mark.parametrize(
    ("capability", "risk", "approval_required"),
    [("file_write", "SAFE", False), ("system_setting", "HIGH", True)],
)
def test_diagnostics_cli_previews_without_importing_skills_or_writing_db(
    tmp_path, monkeypatch, capsys, capability, risk, approval_required,
):
    source = Path(__file__).resolve().parents[1] / "skills" / "quick_note"
    monkeypatch.chdir(tmp_path)
    shutil.copytree(source, Path("skills/quick_note"))
    Path("config").mkdir()
    Path("config/skills.toml").write_text('enabled = ["quick_note"]\n', encoding="utf-8")
    manifest_path = Path("skills/quick_note/skill.toml")
    manifest = manifest_path.read_text(encoding="utf-8")
    manifest_path.write_text(manifest.replace('"file_write"', f'"{capability}"'), encoding="utf-8")
    module_path = Path("skills/quick_note/skill.py")
    with module_path.open("a", encoding="utf-8") as module:
        module.write('\nPath("imported.txt").touch()\n')
    database = tmp_path / "data" / "mastercontrol.db"
    arguments = json.dumps({"filename": "preview.md", "title": "Preview", "body": "Test"})

    exit_code = diagnostics.main(["preview", "quick_note.save", arguments, "--db", str(database)])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {
        "action": "skill.quick_note.save",
        "capabilities": [capability],
        "risk": risk,
        "target_paths": ["data/notes/{filename}"],
        "approval_required": approval_required,
    }
    assert not Path("data/notes/preview.md").exists()
    assert not Path("imported.txt").exists()
    assert not database.parent.exists()


@pytest.mark.parametrize(
    ("config", "payload", "error"),
    [
        ('enabled = []\n', '{}', "skill is not enabled"),
        ('enabled = ["task_list"]\n', '{"extra": true}', "invalid action parameters"),
    ],
)
def test_diagnostics_cli_rejects_disabled_skills_and_invalid_arguments(
    tmp_path, monkeypatch, capsys, config, payload, error,
):
    source = Path(__file__).resolve().parents[1] / "skills" / "task_list"
    monkeypatch.chdir(tmp_path)
    shutil.copytree(source, Path("skills/task_list"))
    Path("config").mkdir()
    Path("config/skills.toml").write_text(config, encoding="utf-8")

    assert diagnostics.main(["preview", "task_list.list", payload]) == 1
    assert error in capsys.readouterr().err
    assert not Path("data").exists()
