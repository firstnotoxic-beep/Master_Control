# ทดสอบการสร้าง schema และการบันทึกข้อมูลใน SQLite
from core.db import execute, fetch_one, init_db


def test_schema_and_settings(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    execute("INSERT INTO tasks (description) VALUES (?)", ("อ่านหนังสือ",), db_path)
    assert fetch_one(
        "SELECT value FROM settings WHERE key = 'schema_version'", db_path=db_path
    )["value"] == "2"
    assert fetch_one("SELECT description FROM tasks", db_path=db_path)["description"] == "อ่านหนังสือ"
