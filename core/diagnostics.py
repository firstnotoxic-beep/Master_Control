# ตรวจสอบสถานะระบบและแสดง action preview โดยไม่ execute action
from __future__ import annotations

import argparse
import json
import sqlite3
import stat
import sys
import tempfile
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from core.db import DEFAULT_DB_PATH, SCHEMA_VERSION
from core.skills import DEFAULT_SKILLS_DIR, SkillRegistry


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


def _probe_directory_writable(directory: Path) -> None:
    with tempfile.TemporaryFile(mode="w+b", dir=directory) as probe:
        probe.write(b"mastercontrol-diagnostic-probe")
        probe.flush()


def _probe_action_log_writable(db_path: Path) -> None:
    connection = sqlite3.connect(db_path, timeout=0.25)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("SAVEPOINT diagnostic_write_probe")
        connection.execute(
            """
            INSERT INTO action_log (action, details, risk_level, status, actor)
            VALUES ('__diagnostic_probe__', '', 'LOW', 'diagnostic_probe', 'diagnostics')
            """
        )
        connection.execute("ROLLBACK TO SAVEPOINT diagnostic_write_probe")
        connection.execute("RELEASE SAVEPOINT diagnostic_write_probe")
        connection.rollback()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _append_check(
    checks: list[dict[str, str]], name: str, status: str, message: str
) -> None:
    checks.append({"name": name, "status": status, "message": message})


def _check_database(db_path: Path, checks: list[dict[str, str]]) -> None:
    if not db_path.is_file():
        _append_check(checks, "database", "FAIL", f"Database file not found: {db_path}")
        _append_check(checks, "schema_version", "FAIL", "Cannot read schema without a database")
        _append_check(checks, "action_log_writable", "FAIL", "Cannot probe action_log without a database")
        return

    connection = None
    try:
        connection = sqlite3.connect(db_path, timeout=0.25)
        connection.execute("PRAGMA query_only = ON")
        integrity = connection.execute("PRAGMA quick_check").fetchone()
        if integrity is None or integrity[0] != "ok":
            _append_check(checks, "database", "FAIL", "SQLite quick_check did not return ok")
            return
        connection.execute("SELECT 1 FROM action_log LIMIT 1").fetchone()
        _append_check(checks, "database", "PASS", "SQLite database is reachable and action_log is readable")
        row = connection.execute(
            "SELECT value FROM settings WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            _append_check(checks, "schema_version", "FAIL", "schema_version setting is missing")
        elif str(row[0]) == str(SCHEMA_VERSION):
            _append_check(checks, "schema_version", "PASS", f"Schema version {row[0]}")
        else:
            _append_check(
                checks,
                "schema_version",
                "WARN",
                f"Database schema is {row[0]}; code expects {SCHEMA_VERSION}. Run the normal application migration path after backing up the DB.",
            )
    except (OSError, sqlite3.Error) as error:
        _append_check(checks, "database", "FAIL", f"Database check failed: {error}")
        _append_check(checks, "schema_version", "FAIL", "Schema version could not be read")
    finally:
        if connection is not None:
            connection.close()

    try:
        _probe_action_log_writable(db_path)
        _append_check(
            checks,
            "action_log_writable",
            "PASS",
            "A transactional write probe succeeded and was rolled back; no action row was retained",
        )
    except (OSError, sqlite3.Error) as error:
        _append_check(checks, "action_log_writable", "FAIL", f"Action log write probe failed: {error}")


def _check_data_directories(
    data_root: Path, checks: list[dict[str, str]]
) -> None:
    directories = [
        data_root,
        data_root / "notes",
        data_root / "tasks",
        data_root / "brain_dump",
        data_root / "reports",
        data_root / "logs",
    ]
    for directory in directories:
        name = f"data_dir:{directory.name or 'data'}"
        if _is_link_or_reparse(directory):
            _append_check(checks, name, "FAIL", "Directory is a symlink or reparse point")
        elif not directory.exists():
            _append_check(checks, name, "WARN", "Directory does not exist yet; diagnostics did not create it")
        elif not directory.is_dir():
            _append_check(checks, name, "FAIL", "Path exists but is not a directory")
        else:
            try:
                _probe_directory_writable(directory)
                _append_check(
                    checks,
                    name,
                    "PASS",
                    "Temporary write probe succeeded and its file was removed",
                )
            except OSError as error:
                _append_check(checks, name, "WARN", f"Directory is not writable: {error}")


def _check_skill_manifests(
    skills_dir: Path, checks: list[dict[str, str]]
) -> None:
    registry = object.__new__(SkillRegistry)
    registry.skills_dir = skills_dir
    if not skills_dir.is_dir():
        _append_check(checks, "skill_manifests", "WARN", f"Skills directory not found: {skills_dir}")
        return
    folders = registry._skill_folders()
    if not folders:
        _append_check(checks, "skill_manifests", "WARN", "No installed Skill folders found")
        return

    for name, folder in sorted(folders.items()):
        try:
            manifest = registry._read_manifest(name, folder)
        except (OSError, TypeError, ValueError, tomllib.TOMLDecodeError) as error:
            _append_check(checks, f"skill_manifest:{name}", "WARN", f"Invalid manifest: {error}")
        else:
            _append_check(
                checks,
                f"skill_manifest:{name}",
                "PASS",
                f"Manifest {manifest.version} is valid; enabled-by-default is false",
            )


def run_diagnostics(
    db_path: str | Path = DEFAULT_DB_PATH,
    skills_dir: str | Path = DEFAULT_SKILLS_DIR,
    data_dir: str | Path = Path("data"),
) -> dict[str, Any]:
    """Inspect local health without migrations or persistent data changes.

    Directory and SQLite write probes are temporary; files are removed and the
    SQLite transaction is rolled back before returning.
    """
    checks: list[dict[str, str]] = []
    _check_database(Path(db_path), checks)
    _check_data_directories(Path(data_dir), checks)
    _check_skill_manifests(Path(skills_dir), checks)

    statuses = {item["status"] for item in checks}
    overall = "FAIL" if "FAIL" in statuses else "WARN" if "WARN" in statuses else "PASS"
    return {
        "status": overall,
        "read_only": True,
        "persistent_changes": False,
        "checks": checks,
        "notes": "Temporary directory probes are removed; the SQLite action_log probe is rolled back.",
    }


def _run_action_preview(
    action: str, arguments: str, db_path: Path
) -> dict[str, Any]:
    if action.count(".") != 1:
        raise ValueError("Use preview <skill>.<action> [JSON object]")
    skill_name, action_id = action.split(".", 1)
    payload = json.loads(arguments) if arguments.strip() else {}
    if not isinstance(payload, dict):
        raise TypeError("Preview arguments must be a JSON object")
    registry = SkillRegistry(db_path=db_path)
    return registry.preview_action(skill_name, action_id, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only MasterControl diagnostics and Skill action preview"
    )
    subparsers = parser.add_subparsers(dest="command")
    check = subparsers.add_parser("check", help="Run system diagnostics without persistent changes")
    check.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    check.add_argument("--skills-dir", type=Path, default=DEFAULT_SKILLS_DIR)
    check.add_argument("--data-dir", type=Path, default=Path("data"))

    preview = subparsers.add_parser("preview", help="Preview a loaded Skill action without executing it")
    preview.add_argument("action", help="Skill action key, e.g. quick_note.save")
    preview.add_argument("arguments", nargs="?", default="{}")
    preview.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        arguments = ["check"]
    parser = build_parser()
    args = parser.parse_args(arguments)

    try:
        if args.command == "preview":
            result = _run_action_preview(args.action, args.arguments, args.db)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "check":
            result = run_diagnostics(args.db, args.skills_dir, args.data_dir)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 1 if result["status"] == "FAIL" else 0
        parser.print_help()
        return 2
    except (OSError, RuntimeError, TypeError, ValueError, sqlite3.Error) as error:
        print(f"Diagnostics failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
