# ประมวลผลคำสั่ง keyword ที่กำหนดไว้ตายตัว โดยไม่รันคำสั่งระบบ
from __future__ import annotations

import json
from pathlib import Path

from core.approval import create_approval
from core.db import DEFAULT_DB_PATH, execute, fetch_all, init_db
from core.modes import ModeConfigError, plan_mode
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
        result["message"] = (
            "status, help, add task <รายละเอียด>, list tasks, gaming mode, "
            "focus mode, mode status, restore mode [session_id], top processes"
        )
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
    elif lowered in {"gaming mode", "focus mode"}:
        mode_name = lowered.split()[0]
        action = f"{mode_name}_mode"
        try:
            plan = plan_mode(mode_name)
        except ModeConfigError as error:
            return {"ok": False, "action": action, "message": str(error)}
        details = json.dumps(plan, ensure_ascii=False)
        approval_id = create_approval(action, details, risk_for_action(action).value, db_path)
        plan["approval_id"] = approval_id
        execute(
            "UPDATE action_log SET details = ? WHERE id = (SELECT action_log_id FROM approvals WHERE id = ?)",
            (json.dumps(plan, ensure_ascii=False), approval_id),
            db_path,
        )
        result.update(
            action=action,
            approval_id=approval_id,
            plan=plan,
            message="สร้าง dry-run plan และคำขออนุมัติแล้ว",
        )
        return result
    elif lowered == "mode status":
        action, details = "mode_status", "แสดง mode sessions"
        sessions = fetch_all(
            "SELECT id, mode_name, closed_processes, created_at, status FROM mode_sessions ORDER BY id DESC",
            db_path=db_path,
        )
        result["sessions"] = [dict(session) for session in sessions]
        result["message"] = f"มี mode session {len(sessions)} รายการ"
    elif lowered == "restore mode" or lowered.startswith("restore mode "):
        session_text = raw[len("restore mode") :].strip()
        if session_text:
            try:
                session_id = int(session_text)
            except ValueError:
                return {"ok": False, "action": "restore_mode", "message": "session_id ต้องเป็นตัวเลข"}
        else:
            latest = fetch_all("SELECT id FROM mode_sessions ORDER BY id DESC LIMIT 1", db_path=db_path)
            if not latest:
                return {"ok": False, "action": "restore_mode", "message": "ยังไม่มี mode session ให้ restore"}
            session_id = latest[0]["id"]
        action, details = "restore_mode", json.dumps({"session_id": session_id})
        approval_id = create_approval(action, details, risk_for_action(action).value, db_path)
        result.update(
            approval_id=approval_id,
            session_id=session_id,
            message="สร้างคำขออนุมัติสำหรับ restore แล้ว",
        )
        return result
    elif lowered == "top processes":
        from core.telemetry import top_processes

        action, details = "top_processes", "แสดงโปรเซสที่ใช้ RAM สูงสุด"
        result["processes"] = top_processes()
        result["message"] = "แสดงโปรเซสที่ใช้ RAM สูงสุดแล้ว"
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
