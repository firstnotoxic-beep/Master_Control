# สร้างรายงานประจำวันจากข้อมูลในเครื่องโดยไม่แก้ไขข้อมูลต้นทาง
from __future__ import annotations

import os
import re
import sqlite3
import stat
import tempfile
from datetime import UTC, date, datetime, time
from pathlib import Path

DATA_ROOT = Path("data")
TASKS_ROOT = DATA_ROOT / "tasks"
BRAIN_DUMP_ROOT = DATA_ROOT / "brain_dump"
ACTION_LOG_DB = DATA_ROOT / "mastercontrol.db"
REPORTS_ROOT = DATA_ROOT / "reports"

_TASK_LINE = re.compile(r"^- \[( |x)\] #(\d+) (.+)$")
_NOTE_FILENAME = re.compile(r"^(\d{8}T\d{12}Z)-([a-f0-9]{32})\.md$")
_DATE_FORMAT = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MAX_ACTION_ROWS = 50
_MAX_BRAIN_DUMP_NOTES = 100


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction) and is_junction():
        return True
    try:
        attributes = path.lstat().st_file_attributes
    except (AttributeError, FileNotFoundError):
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _data_root_if_present() -> Path | None:
    if _is_link_or_reparse(DATA_ROOT):
        raise ValueError("data directory cannot be a symlink or reparse point")
    if not DATA_ROOT.exists():
        return None
    if not DATA_ROOT.is_dir():
        raise ValueError("data path must be a directory")
    root = DATA_ROOT.resolve(strict=True)
    if _is_link_or_reparse(root):
        raise ValueError("data directory cannot be a symlink or reparse point")
    return root


def _safe_source_root(path: Path) -> Path | None:
    data_root = _data_root_if_present()
    if data_root is None:
        return None
    if path.parent.resolve(strict=True) != data_root:
        raise ValueError("source directory must be directly inside data/")
    if _is_link_or_reparse(path):
        raise ValueError("source directory cannot be a symlink or reparse point")
    if not path.exists():
        return None
    if not path.is_dir():
        raise ValueError("source path must be a directory")
    root = path.resolve(strict=True)
    if root.parent != data_root or _is_link_or_reparse(root):
        raise ValueError("source directory must remain inside data/")
    return root


def _safe_source_file(path: Path, root: Path) -> Path:
    if _is_link_or_reparse(path):
        raise ValueError("source files cannot be symlinks or reparse points")
    resolved = path.resolve(strict=True)
    if resolved.parent != root or not resolved.is_relative_to(root):
        raise ValueError("source file must remain inside its data directory")
    file_stat = resolved.stat()
    if not stat.S_ISREG(file_stat.st_mode):
        raise ValueError("source entry must be a regular file")
    return resolved


def _read_task_snapshot() -> list[dict[str, object]] | None:
    root = _safe_source_root(TASKS_ROOT)
    if root is None:
        return None
    source = root / "tasks.md"
    if not source.exists():
        return None
    target = _safe_source_file(source, root)
    content = target.read_text(encoding="utf-8")
    if not content.strip():
        return None

    tasks: list[dict[str, object]] = []
    seen_ids: set[int] = set()
    for line in content.splitlines():
        if not line:
            continue
        match = _TASK_LINE.fullmatch(line)
        if match is None:
            raise ValueError("tasks.md contains an invalid task entry")
        task_id = int(match.group(2))
        if task_id < 1 or task_id in seen_ids:
            raise ValueError("tasks.md contains an invalid or duplicate task ID")
        seen_ids.add(task_id)
        tasks.append(
            {
                "id": task_id,
                "done": match.group(1) == "x",
                "description": match.group(3),
            }
        )
    return tasks or None


def _read_brain_dump_for_date(report_date: date) -> list[tuple[datetime, str]] | None:
    root = _safe_source_root(BRAIN_DUMP_ROOT)
    if root is None:
        return None

    notes: list[tuple[datetime, str]] = []
    for entry in root.iterdir():
        if entry.suffix.lower() != ".md":
            continue
        match = _NOTE_FILENAME.fullmatch(entry.name)
        if match is None:
            raise ValueError("brain_dump contains an invalid Markdown filename")
        target = _safe_source_file(entry, root)
        stamp = datetime.strptime(match.group(1), "%Y%m%dT%H%M%S%fZ").replace(
            tzinfo=UTC
        )
        if stamp.astimezone().date() != report_date:
            continue
        content = target.read_text(encoding="utf-8").strip()
        if content:
            notes.append((stamp.astimezone(), content))

    if not notes:
        return None
    notes.sort(key=lambda item: item[0], reverse=True)
    return notes[:_MAX_BRAIN_DUMP_NOTES]


def _utc_bound(day: date) -> str:
    local_midnight = datetime.combine(day, time.min).astimezone()
    utc_midnight = local_midnight.astimezone(UTC).replace(tzinfo=None)
    return utc_midnight.strftime("%Y-%m-%d %H:%M:%S")


def _action_log_database() -> Path | None:
    data_root = _data_root_if_present()
    if data_root is None:
        return None
    if ACTION_LOG_DB.parent.resolve(strict=True) != data_root:
        raise ValueError("action log database must be directly inside data/")
    if _is_link_or_reparse(ACTION_LOG_DB):
        raise ValueError("action log database cannot be a symlink or reparse point")
    if not ACTION_LOG_DB.exists():
        return None
    target = ACTION_LOG_DB.resolve(strict=True)
    if target.parent != data_root or not stat.S_ISREG(target.stat().st_mode):
        raise ValueError("action log database must remain inside data/")
    return target


def _read_action_log_for_date(
    report_date: date,
) -> tuple[dict[str, int], list[dict[str, str]]] | None:
    database = _action_log_database()
    if database is None:
        return None

    connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True, timeout=2)
    connection.row_factory = sqlite3.Row
    try:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'action_log'"
        ).fetchone()
        if table is None:
            return None

        start = _utc_bound(report_date)
        end = _utc_bound(date.fromordinal(report_date.toordinal() + 1))
        summary_rows = connection.execute(
            """
            SELECT status, COUNT(*) AS total
            FROM action_log
            WHERE created_at >= ? AND created_at < ?
            GROUP BY status
            ORDER BY status
            """,
            (start, end),
        ).fetchall()
        if not summary_rows:
            return None

        summary = {str(row["status"]): int(row["total"]) for row in summary_rows}
        entries = connection.execute(
            """
            SELECT action, status, risk_level, created_at
            FROM action_log
            WHERE created_at >= ? AND created_at < ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (start, end, _MAX_ACTION_ROWS),
        ).fetchall()
        return summary, [
            {
                "action": str(row["action"]),
                "status": str(row["status"]),
                "risk": str(row["risk_level"]),
                "created_at": str(row["created_at"]),
            }
            for row in entries
        ]
    finally:
        connection.close()


def _validate_date(value: str) -> date:
    if not isinstance(value, str) or not _DATE_FORMAT.fullmatch(value):
        raise ValueError("date must use YYYY-MM-DD format")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("date is not a valid calendar date") from error
    if parsed.isoformat() != value:
        raise ValueError("date must use YYYY-MM-DD format")
    return parsed


def _today() -> date:
    return date.today()


def _reports_root(*, create: bool = False) -> Path:
    if _is_link_or_reparse(DATA_ROOT):
        raise ValueError("data directory cannot be a symlink or reparse point")
    if create:
        DATA_ROOT.mkdir(parents=True, exist_ok=True)
    if not DATA_ROOT.is_dir():
        raise ValueError("data directory does not exist")
    data_root = DATA_ROOT.resolve(strict=True)

    if REPORTS_ROOT.parent.resolve(strict=True) != data_root:
        raise ValueError("reports directory must be directly inside data/")
    if _is_link_or_reparse(REPORTS_ROOT):
        raise ValueError("reports directory cannot be a symlink or reparse point")
    if create:
        REPORTS_ROOT.mkdir(exist_ok=True)
    if not REPORTS_ROOT.is_dir():
        raise ValueError("reports directory does not exist")
    root = REPORTS_ROOT.resolve(strict=True)
    if root.parent != data_root or _is_link_or_reparse(root):
        raise ValueError("reports directory must remain inside data/reports")
    return root


def _safe_report_path(report_date: date, root: Path) -> Path:
    target = root / f"{report_date.isoformat()}.md"
    if _is_link_or_reparse(target):
        raise ValueError("report file cannot be a symlink or reparse point")
    resolved = target.resolve(strict=False)
    if resolved.parent != root or not resolved.is_relative_to(root):
        raise ValueError("report file must remain inside data/reports")
    if target.exists() and not stat.S_ISREG(target.lstat().st_mode):
        raise ValueError("report target must be a regular file")
    return resolved


def _render_report(
    report_date: date,
    tasks: list[dict[str, object]] | None,
    notes: list[tuple[datetime, str]] | None,
    action_log: tuple[dict[str, int], list[dict[str, str]]] | None,
) -> str:
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        f"# Daily Report — {report_date.isoformat()}",
        "",
        f"Generated: {generated_at}",
        "",
        "## Task List — current snapshot",
        "",
        "The task list file has no per-task dates; this is the current state at report time, not historical activity for the selected date.",
        "",
    ]

    if not tasks:
        lines.append("ไม่มีข้อมูล (no data)")
    else:
        completed = sum(bool(item["done"]) for item in tasks)
        pending = len(tasks) - completed
        lines.append(
            f"ทั้งหมด {len(tasks)} งาน: เสร็จแล้ว {completed}, ค้างอยู่ {pending}"
        )
        lines.append("")
        for item in tasks:
            marker = "x" if item["done"] else " "
            lines.append(f"- [{marker}] #{item['id']} {item['description']}")

    lines.extend(["", f"## Brain Dump — {report_date.isoformat()}", ""])
    if not notes:
        lines.append("ไม่มีข้อมูล (no data)")
    else:
        for local_stamp, content in notes:
            lines.extend(
                [
                    f"### {local_stamp.strftime('%H:%M:%S')} (local time)",
                    "",
                    content,
                    "",
                ]
            )
        if len(notes) == _MAX_BRAIN_DUMP_NOTES:
            lines.append(f"_แสดงบันทึกล่าสุดไม่เกิน {_MAX_BRAIN_DUMP_NOTES} รายการ_")

    lines.extend(["", f"## Action Log — {report_date.isoformat()}", ""])
    if not action_log:
        lines.append("ไม่มีข้อมูล (no data)")
    else:
        summary, entries = action_log
        total = sum(summary.values())
        lines.append(f"ทั้งหมด {total} รายการ")
        lines.extend(
            f"- {status}: {count}"
            for status, count in sorted(summary.items())
        )
        lines.append("")
        lines.append(f"รายการล่าสุด (สูงสุด {_MAX_ACTION_ROWS} รายการ):")
        for entry in entries:
            lines.append(
                "- "
                f"{entry['created_at']} UTC | {entry['action']} | "
                f"{entry['status']} | risk={entry['risk']}"
            )

    lines.extend(["", "---", "สร้างจากข้อมูลภายในเครื่องเท่านั้น ไม่มีการเรียกเครือข่าย", ""])
    return "\n".join(lines)


def _write_report(report_date: date, content: str) -> Path:
    root = _reports_root(create=True)
    target = _safe_report_path(report_date, root)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=root,
            prefix=f".{report_date.isoformat()}-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())

        if _reports_root() != root or _is_link_or_reparse(temporary_path):
            raise ValueError("reports directory changed while writing")
        resolved_temporary = temporary_path.resolve(strict=True)
        if resolved_temporary.parent != root or not stat.S_ISREG(
            resolved_temporary.stat().st_mode
        ):
            raise ValueError("temporary report must remain inside data/reports")

        os.replace(temporary_path, target)
        temporary_path = None

        if _reports_root() != root or _is_link_or_reparse(target):
            raise ValueError("final report path cannot be a symlink or reparse point")
        resolved_target = target.resolve(strict=True)
        if (
            resolved_target.parent != root
            or not resolved_target.is_relative_to(root)
            or not stat.S_ISREG(resolved_target.stat().st_mode)
        ):
            raise ValueError("final report path must remain inside data/reports")
        return resolved_target
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _generate(report_date: date) -> str:
    tasks = _read_task_snapshot()
    notes = _read_brain_dump_for_date(report_date)
    action_log = _read_action_log_for_date(report_date)
    content = _render_report(report_date, tasks, notes, action_log)
    _write_report(report_date, content)
    return f"Report saved: data/reports/{report_date.isoformat()}.md"


def run(action_id, params):
    if action_id == "generate":
        message = _generate(_today())
        return {"ok": True, "message": message, "verified": False}

    if action_id == "generate_for_date":
        try:
            report_date = _validate_date(params.date)
        except (TypeError, ValueError) as error:
            return {"ok": False, "message": str(error), "verified": False}
        message = _generate(report_date)
        return {"ok": True, "message": message, "verified": False}

    raise ValueError("unsupported action")


def verify(action_id, params, result):
    if not result.get("ok"):
        return False
    if action_id == "generate":
        report_date = _today()
    elif action_id == "generate_for_date":
        report_date = _validate_date(params.date)
    else:
        return False
    root = _reports_root()
    target = _safe_report_path(report_date, root)
    if not target.is_file():
        return False
    content = target.read_text(encoding="utf-8")
    return content.startswith(f"# Daily Report — {report_date.isoformat()}\n")
