# สร้าง อนุมัติ ยกเลิก และหมดอายุคำขออนุมัติ
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sqlite3

from core.db import DEFAULT_DB_PATH, fetch_all, get_connection, init_db

APPROVAL_TTL_HOURS = 24


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


def _expire_stale_approvals(connection: sqlite3.Connection) -> int:
    """Expire requests older than the fixed TTL without a schema migration."""
    expired_at = datetime.now(UTC).isoformat()
    rows = connection.execute(
        """
        SELECT id, action_log_id
        FROM approvals
        WHERE status = 'pending'
          AND datetime(created_at) <= datetime('now', ?)
        """,
        (f"-{APPROVAL_TTL_HOURS} hours",),
    ).fetchall()
    for row in rows:
        connection.execute(
            """
            UPDATE approvals
            SET status = 'expired', decided_by = 'system', decided_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (expired_at, row["id"]),
        )
        connection.execute(
            "UPDATE action_log SET status = 'expired', actor = 'system' WHERE id = ?",
            (row["action_log_id"],),
        )
    return len(rows)


def _decide(
    approval_id: int,
    status: str,
    decided_by: str,
    db_path: str | Path,
) -> None:
    decided_at = datetime.now(UTC).isoformat()
    expired = False
    with get_connection(db_path) as connection:
        _expire_stale_approvals(connection)
        approval = connection.execute(
            "SELECT action_log_id, status FROM approvals WHERE id = ?",
            (approval_id,),
        ).fetchone()
        if approval is None:
            raise ValueError("ไม่พบคำขออนุมัติ")
        if approval["status"] == "expired":
            expired = True
        elif approval["status"] != "pending":
            raise ValueError("คำขอนี้ถูกตัดสินใจไปแล้ว")
        else:
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
    if expired:
        raise ValueError("คำขออนุมัติหมดอายุแล้ว กรุณาสร้างคำขอใหม่")


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
    with get_connection(db_path) as connection:
        _expire_stale_approvals(connection)
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
