# ทดสอบ diagnostics แบบไม่แก้ไขข้อมูลถาวร
import json

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
