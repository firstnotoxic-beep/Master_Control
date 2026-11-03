# ทดสอบ command handler แบบ keyword
from core.commands import handle_command
from core.db import fetch_one


def test_add_and_list_task(tmp_path):
    db_path = tmp_path / "test.db"
    result = handle_command("add task ส่งฟิสิกส์ พรุ่งนี้", db_path)
    assert result["ok"]
    listed = handle_command("list tasks", db_path)
    assert listed["tasks"][0]["description"] == "ส่งฟิสิกส์ พรุ่งนี้"
    assert fetch_one("SELECT action FROM action_log", db_path=db_path)["action"] == "add_task"


def test_medium_command_creates_approval(tmp_path):
    result = handle_command("test medium", tmp_path / "test.db")
    assert result["ok"]
    assert result["approval_id"] > 0
