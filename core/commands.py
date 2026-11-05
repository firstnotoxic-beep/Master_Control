# ประมวลผลคำสั่ง keyword ที่กำหนดไว้ตายตัว โดยไม่รันคำสั่งระบบ
from __future__ import annotations

import json
from pathlib import Path

from core.alerts import AlertEngine, set_alert_setting
from core.approval import create_approval
from core.db import DEFAULT_DB_PATH, execute, fetch_all, init_db
from core.modes import ModeConfigError, plan_mode
from core.permissions import requires_approval, risk_for_action


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
    elif lowered == "alerts status":
        action, details = "alerts_status", "แสดง alert ที่ยัง active"
        alerts = [dict(item) for item in AlertEngine(db_path).active_events()]
        result["alerts"] = alerts
        result["message"] = f"มี alert ที่ยัง active {len(alerts)} รายการ"
    elif lowered.startswith("snooze "):
        parts = lowered.split()
        if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
            return {"ok": False, "action": "snooze_alert", "message": "ใช้ snooze <alert_id> <15|30|60>"}
        try:
            AlertEngine(db_path).snooze(int(parts[1]), int(parts[2]))
        except ValueError as error:
            return {"ok": False, "action": "snooze_alert", "message": str(error)}
        action, details = "snooze_alert", f"alert_id={parts[1]}, minutes={parts[2]}"
        result["message"] = "เลื่อนการแจ้งเตือนแล้ว"
    elif lowered.startswith("ack "):
        alert_id = lowered[4:].strip()
        if not alert_id.isdigit():
            return {"ok": False, "action": "ack_alert", "message": "ใช้ ack <alert_id>"}
        AlertEngine(db_path).acknowledge(int(alert_id))
        action, details = "ack_alert", f"alert_id={alert_id}"
        result["message"] = "รับทราบการแจ้งเตือนแล้ว"
    elif lowered in {"vacation on", "vacation off"}:
        value = "on" if lowered.endswith("on") else "off"
        set_alert_setting("vacation_mode", value, db_path)
        action, details = "vacation_mode", value
        result["message"] = f"Vacation Mode: {value}"
    elif lowered == "skip bedtime":
        from datetime import date

        set_alert_setting("skip_bedtime", date.today().isoformat(), db_path)
        action, details = "skip_bedtime", date.today().isoformat()
        result["message"] = "ข้าม bedtime ของวันนี้แล้ว"
    elif lowered == "help":
        action, details = "help", "แสดงคำสั่งที่รองรับ"
        result["message"] = (
            "status, alerts status, snooze <alert_id> <15|30|60>, ack <alert_id>, "
            "vacation on/off, skip bedtime, add task <รายละเอียด>, list tasks, gaming mode, "
            "focus mode, mode status, restore mode [session_id], top processes, skills, "
            "skill enable NAME, run task_list.add {\"description\":\"...\}"}, "
            "run task_list.list {}, run task_list.done {\"task_id\":1}, "
            "run task_list.remove {\"task_id\":1}"
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
    elif lowered.startswith("skill enable "):
        from core.skills import SkillRegistry

        skill_parts = raw.split()
        skill_name = skill_parts[2].lower() if len(skill_parts) >= 3 else ""
        registry = SkillRegistry(db_path=db_path)
        if len(skill_parts) == 4 and skill_parts[3].lower() == "confirm":
            enabled = registry.enable(skill_name)
            return {"ok": enabled["ok"], "action": "skill_enable", "message": enabled["message"]}
        try:
            preview = registry.preview(skill_name)
        except (FileNotFoundError, TypeError, ValueError) as error:
            return {"ok": False, "action": "skill_enable", "message": str(error)}
        summaries = [
            f"{item['id']}: capabilities={','.join(item['requested_capabilities']) or 'none'}, "
            f"risk={item['final_risk']}"
            for item in preview["actions"]
        ]
        return {
            "ok": True,
            "action": "skill_enable_preview",
            "preview": preview,
            "message": "Review before enabling: " + " | ".join(summaries),
            "confirmation_required": True,
        }
    elif lowered.startswith("skill disable "):
        from core.skills import SkillRegistry

        skill_name = raw[len("skill disable "):].strip().lower()
        disabled = SkillRegistry.disable_without_loading(skill_name, db_path=db_path)
        return {"ok": disabled["ok"], "action": "skill_disable", "message": disabled["message"]}
    elif lowered.startswith("run "):
        from core.skills import SkillRegistry

        request = raw[4:].strip()
        head, separator, argument_text = request.partition(" ")
        if head.count(".") != 1:
            return {"ok": False, "action": "skill_run", "message": "Use run <skill>.<action> [JSON args]"}
        skill_name, skill_action = head.split(".", 1)
        try:
            arguments = json.loads(argument_text) if separator and argument_text.strip() else {}
            if not isinstance(arguments, dict):
                raise TypeError("args must be a JSON object")
            registry = SkillRegistry(db_path=db_path)
            prepared = registry.prepare_action(skill_name, skill_action, arguments)
            if requires_approval(prepared.action_key):
                approval_id = create_approval(
                    prepared.action_key,
                    prepared.approval_details(),
                    prepared.risk.value,
                    db_path,
                )
                return {
                    "ok": True,
                    "action": prepared.action_key,
                    "approval_id": approval_id,
                    "message": f"Skill action awaits approval (#{approval_id})",
                }
            return {"action": prepared.action_key, **registry.execute_action(prepared)}
        except (TypeError, ValueError, PermissionError, json.JSONDecodeError) as error:
            return {"ok": False, "action": "skill_run", "message": str(error)}
    elif lowered == "skills":
        from core.skills import SkillRegistry
        registry = SkillRegistry(db_path=db_path)
        return {"ok": True, "action": "skills", "skills": registry.list_skills(), "message": "Skill registry loaded"}
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
