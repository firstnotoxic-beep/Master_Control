# ทดสอบ CLI wrapper โดยใช้ฐานข้อมูลชั่วคราว
import json

from core.cli import main


def test_cli_runs_command_against_requested_database(tmp_path, capsys):
    database = tmp_path / "data" / "cli-test.db"

    exit_code = main(["--db", str(database), "status"])

    output = capsys.readouterr()
    result = json.loads(output.out)
    assert exit_code == 0
    assert result["ok"] is True
    assert result["message"] == "ระบบพร้อมทำงาน"
    assert database.is_file()


def test_cli_rejects_missing_command(capsys):
    exit_code = main([])

    output = capsys.readouterr()
    assert exit_code == 2
    assert "usage:" in output.err.lower()


def test_cli_returns_nonzero_for_unknown_command(tmp_path, capsys):
    exit_code = main(["--db", str(tmp_path / "test.db"), "not a command"])

    output = capsys.readouterr()
    result = json.loads(output.out)
    assert exit_code == 1
    assert result["ok"] is False
