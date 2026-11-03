# สร้าง อนุมัติ และยกเลิกคำขอ พร้อมบันทึกผู้ตัดสินใจ
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from core.db import DEFAULT_DB_PATH, fetch_all, get_connection, init_db


def create_approval(
    action: str,
    details: str,
    risk_level: str,
    db_path: str | Path = DEFAULT_DB_PATH,
    requested_by: str = "user",
) -> int:
    init_db(db_path)
    with get_connection(db_path) as connection:
        action_log_id = connection.execute(
            """
            INSERT INTO action_log (action, details, risk_level, status, actor)
            VALUES (?, ?, ?, 'pending_approval', ?)
            """,
            (action, details, risk_level, requested_by),
        ).lastrowid
        approval_id = connection.execute(
            """
            INSERT INTO approvals (action_log_id, requested_by)
            VALUES (?, ?)
            """,
            (action_log_id, requested_by),
        ).lastrowid
        return approval_id or 0


def _decide(
    approval_id: int,
    status: str,
    decided_by: str,
    db_path: str | Path,
) -> None:
    decided_at = datetime.now(UTC).isoformat()
    with get_connection(db_path) as connection:
        approval = connection.execute(
            "SELECT action_log_id, status FROM approvals WHERE id = ?",
            (approval_id,),
        ).fetchone()
        if approval is None:
            raise ValueError("ไม่พบคำขออนุมัติ")
        if approval["status"] != "pending":
            raise ValueError("คำขอนี้ถูกตัดสินใจไปแล้ว")
        connection.execute(
            """
            UPDATE approvals
            SET status = ?, decided_by = ?, decided_at = ?
            WHERE id = ?
            """,
            (status, decided_by, decided_at, approval_id),
        )
        connection.execute(
            "UPDATE action_log SET status = ?, actor = ? WHERE id = ?",
            (status, decided_by, approval["action_log_id"]),
        )


def approve(
    approval_id: int,
    decided_by: str = "user",
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    _decide(approval_id, "approved", decided_by, db_path)


def cancel(
    approval_id: int,
    decided_by: str = "user",
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    _decide(approval_id, "cancelled", decided_by, db_path)


def pending(db_path: str | Path = DEFAULT_DB_PATH) -> list:
    return fetch_all(
        """
        SELECT approvals.id, approvals.status, approvals.requested_by,
               approvals.created_at, action_log.action, action_log.details,
               action_log.risk_level
        FROM approvals
        JOIN action_log ON action_log.id = approvals.action_log_id
        WHERE approvals.status = 'pending'
        ORDER BY approvals.id DESC
        """,
        db_path=db_path,
    )
