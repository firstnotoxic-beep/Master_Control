# ประมวลผลคำสั่ง keyword ที่กำหนดไว้ตายตัว โดยไม่รันคำสั่งระบบ
from __future__ import annotations

from pathlib import Path

from core.approval import create_approval
from core.db import DEFAULT_DB_PATH, execute, fetch_all, init_db
from core.permissions import risk_for_action


def handle_command(
    text: str,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict:
    init_db(db_path)
    raw = text.strip()
    lowered = raw.lower()
    action = ""
    details = ""
    result: dict = {"ok": True, "action": "", "message": ""}

    if lowered == "status":
        action, details = "status", "อ่านสถานะระบบ"
        result["message"] = "ระบบพร้อมทำงาน"
    elif lowered == "help":
        action, details = "help", "แสดงคำสั่งที่รองรับ"
        result["message"] = "status, help, add task <รายละเอียด>, list tasks, test medium"
    elif lowered.startswith("add task "):
        action, details = "add_task", raw[9:].strip()
        if not details:
            return {"ok": False, "action": action, "message": "กรุณาระบุรายละเอียด task"}
        execute("INSERT INTO tasks (description) VALUES (?)", (details,), db_path)
        result["message"] = f"เพิ่ม task แล้ว: {details}"
    elif lowered == "list tasks":
        action, details = "list_tasks", "แสดงรายการ task"
        tasks = fetch_all(
            "SELECT id, description, status, created_at FROM tasks ORDER BY id DESC",
            db_path=db_path,
        )
        result["tasks"] = [dict(task) for task in tasks]
        result["message"] = f"มี task ทั้งหมด {len(tasks)} รายการ"
    elif lowered in {"test medium", "medium test"}:
        action, details = "test_medium", "stub: จะทำ action ระดับ MEDIUM"
        approval_id = create_approval(
            action, details, risk_for_action(action).value, db_path
        )
        result.update(
            approval_id=approval_id,
            message="สร้างคำขออนุมัติสำหรับ action ระดับ MEDIUM แล้ว",
        )
        return result
    else:
        return {
            "ok": False,
            "action": "",
            "message": "ไม่รู้จักคำสั่ง ลองพิมพ์ help",
        }

    risk = risk_for_action(action)
    execute(
        """
        INSERT INTO commands (raw_text, action, arguments, risk_level, status)
        VALUES (?, ?, ?, ?, 'completed')
        """,
        (raw, action, details, risk.value),
        db_path,
    )
    execute(
        """
        INSERT INTO action_log (action, details, risk_level, status)
        VALUES (?, ?, ?, 'completed')
        """,
        (action, details, risk.value),
        db_path,
    )
    result["action"] = action
    return result
