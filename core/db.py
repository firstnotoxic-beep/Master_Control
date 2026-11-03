# จัดการฐานข้อมูล SQLite และ schema พื้นฐานของ MasterControl
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 3
DEFAULT_DB_PATH = Path("data/mastercontrol.db")


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with get_connection(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('schema_version', '3');

            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_text TEXT NOT NULL,
                action TEXT NOT NULL,
                arguments TEXT NOT NULL DEFAULT '',
                risk_level TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS action_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                risk_level TEXT NOT NULL,
                status TEXT NOT NULL,
                actor TEXT NOT NULL DEFAULT 'system',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_log_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                requested_by TEXT NOT NULL DEFAULT 'user',
                decided_by TEXT,
                decided_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (action_log_id) REFERENCES action_log(id)
            );
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel TEXT NOT NULL,
                level TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                due_at TEXT,
                sender TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS alert_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_type TEXT NOT NULL,
                name TEXT NOT NULL UNIQUE,
                enabled INTEGER NOT NULL DEFAULT 1,
                config_json TEXT NOT NULL DEFAULT '{}',
                daily_max INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS alert_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id INTEGER,
                dedupe_key TEXT NOT NULL,
                level TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                first_seen TEXT NOT NULL,
                last_sent TEXT,
                repeat_count INTEGER NOT NULL DEFAULT 0,
                acknowledged_at TEXT,
                snoozed_until TEXT,
                cooldown_until TEXT,
                event_date TEXT NOT NULL,
                FOREIGN KEY (rule_id) REFERENCES alert_rules(id)
            );
            CREATE TABLE IF NOT EXISTS ai_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                tokens INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        current_version = int(
            connection.execute(
                "SELECT value FROM settings WHERE key = 'schema_version'"
            ).fetchone()["value"]
        )
        if current_version < 2:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS mode_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode_name TEXT NOT NULL,
                    closed_processes TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "UPDATE settings SET value = '2' WHERE key = 'schema_version'"
            )
        if current_version < 3:
            task_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(tasks)").fetchall()
            }
            if "due_at" not in task_columns:
                connection.execute("ALTER TABLE tasks ADD COLUMN due_at TEXT")
            if "sender" not in task_columns:
                connection.execute("ALTER TABLE tasks ADD COLUMN sender TEXT")
            connection.execute(
                "UPDATE settings SET value = '3' WHERE key = 'schema_version'"
            )
        else:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS mode_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode_name TEXT NOT NULL,
                    closed_processes TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL
                )
                """
            )


def execute(
    query: str,
    parameters: tuple[Any, ...] = (),
    db_path: str | Path = DEFAULT_DB_PATH,
) -> int:
    with get_connection(db_path) as connection:
        cursor = connection.execute(query, parameters)
        return cursor.lastrowid or 0


def fetch_all(
    query: str,
    parameters: tuple[Any, ...] = (),
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[sqlite3.Row]:
    with get_connection(db_path) as connection:
        return list(connection.execute(query, parameters).fetchall())


def fetch_one(
    query: str,
    parameters: tuple[Any, ...] = (),
    db_path: str | Path = DEFAULT_DB_PATH,
) -> sqlite3.Row | None:
    with get_connection(db_path) as connection:
        return connection.execute(query, parameters).fetchone()
