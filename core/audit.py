# ค้นหา Action Log ตามช่วงเวลา Skill และผลลัพธ์
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from core.db import DEFAULT_DB_PATH, fetch_all

_SKILL_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
_MAX_ROWS = 500


def _date_bound(value: str | date | None, *, end: bool = False) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = date.fromisoformat(value)
        except ValueError as error:
            raise ValueError("date filters must use YYYY-MM-DD") from error
    else:
        raise TypeError("date filters must be dates or YYYY-MM-DD strings")
    if end:
        parsed += timedelta(days=1)
    return datetime.combine(parsed, time.min).strftime("%Y-%m-%d %H:%M:%S")


def query_action_log(
    db_path: str | Path = DEFAULT_DB_PATH,
    *,
    date_from: str | date | None = None,
    date_to: str | date | None = None,
    skill: str | None = None,
    result: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return recent audit rows with parameterized filters and a hard row cap."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= _MAX_ROWS:
        raise ValueError(f"limit must be between 1 and {_MAX_ROWS}")

    start = _date_bound(date_from)
    end = _date_bound(date_to, end=True)
    if start is not None and end is not None and start >= end:
        raise ValueError("date_from must be on or before date_to")

    skill_pattern = None
    if skill:
        if not isinstance(skill, str) or not _SKILL_PATTERN.fullmatch(skill):
            raise ValueError("skill filter must be a valid Skill name")
        skill_pattern = f"skill.{skill}.%"

    result_filter = None
    if result:
        if not isinstance(result, str) or len(result) > 40 or any(
            ord(character) < 32 or ord(character) == 127 for character in result
        ):
            raise ValueError("result filter must be a short status value")
        result_filter = result

    rows = fetch_all(
        """
        SELECT id, action, details, risk_level, status, actor, created_at
        FROM action_log
        WHERE (? IS NULL OR created_at >= ?)
          AND (? IS NULL OR created_at < ?)
          AND (? IS NULL OR action LIKE ?)
          AND (? IS NULL OR status = ?)
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (
            start, start,
            end, end,
            skill_pattern, skill_pattern,
            result_filter, result_filter,
            limit,
        ),
        db_path,
    )
    return [dict(row) for row in rows]
