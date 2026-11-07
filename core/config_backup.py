# สำรองและกู้คืนไฟล์ config ที่อนุญาต พร้อมใช้ approval ก่อน restore
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import stat
import sys
import tempfile
import tomllib
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.approval import create_approval
from core.db import DEFAULT_DB_PATH, execute, fetch_one

CONFIG_ROOT = Path("config")
BACKUP_ROOT = Path("data/backups")
ALLOWED_CONFIG_FILES = frozenset({"skills.toml", "modes.toml"})
FORMAT_VERSION = 1
MAX_BACKUP_BYTES = 1_000_000
_BACKUP_NAME = re.compile(
    r"^config-v1-\d{8}T\d{6}Z-[a-f0-9]{12}\.json$"
)
_SKILL_NAME = re.compile(r"^[a-z][a-z0-9_]{0,47}$")


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


def _safe_directory(path: Path, *, parent: Path | None = None) -> Path:
    if _is_link_or_reparse(path):
        raise ValueError(f"directory cannot be a symlink or reparse point: {path}")
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir() or _is_link_or_reparse(path):
        raise ValueError(f"directory is not safe: {path}")
    resolved = path.resolve(strict=True)
    if parent is not None and resolved.parent != parent.resolve(strict=True):
        raise ValueError(f"directory must remain directly inside {parent}")
    return resolved


def _safe_config_path(name: str, config_dir: Path) -> Path:
    if name not in ALLOWED_CONFIG_FILES:
        raise ValueError("config file is not on the backup allowlist")
    if _is_link_or_reparse(config_dir) or _is_link_or_reparse(config_dir.parent):
        raise ValueError("config directory path cannot contain a symlink or reparse point")
    root = config_dir.resolve(strict=False)
    if root.parent != config_dir.parent.resolve(strict=False):
        raise ValueError("config directory must remain inside the repository root")
    target = root / name
    if _is_link_or_reparse(target):
        raise ValueError(f"config file cannot be a symlink or reparse point: {name}")
    resolved = target.resolve(strict=False)
    if resolved.parent != root:
        raise ValueError("config file path must remain inside config/")
    return resolved


def _validate_config_content(name: str, content: str) -> dict[str, Any]:
    try:
        parsed = tomllib.loads(content)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"{name} is not valid TOML: {error}") from error
    if name == "skills.toml":
        enabled = parsed.get("enabled", [])
        if not isinstance(enabled, list) or any(
            not isinstance(item, str) or not _SKILL_NAME.fullmatch(item)
            for item in enabled
        ):
            raise ValueError("skills.toml must contain enabled = [valid Skill names]")
        if len(enabled) != len(set(enabled)):
            raise ValueError("skills.toml contains duplicate Skill names")
    return parsed


def _ensure_backup_root(backup_dir: Path) -> Path:
    data_root = _safe_directory(backup_dir.parent)
    return _safe_directory(backup_dir, parent=data_root)


def _snapshot_payload(
    config_dir: Path,
    *,
    allow_empty: bool,
) -> dict[str, Any]:
    files: dict[str, dict[str, str]] = {}
    for name in sorted(ALLOWED_CONFIG_FILES):
        target = _safe_config_path(name, config_dir)
        if not target.exists():
            continue
        if not target.is_file():
            raise ValueError(f"config path must be a regular file: {name}")
        content = target.read_text(encoding="utf-8")
        _validate_config_content(name, content)
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        files[name] = {"content": content, "sha256": digest}

    if not files and not allow_empty:
        raise ValueError("no allowlisted config files exist to back up")

    return {
        "format_version": FORMAT_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "files": files,
    }


def _write_backup_payload(
    payload: dict[str, Any],
    backup_dir: Path,
) -> Path:
    backup_root = _ensure_backup_root(backup_dir)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    filename = f"config-v1-{timestamp}-{uuid.uuid4().hex[:12]}.json"
    target = backup_root / filename
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if len(encoded.encode("utf-8")) > MAX_BACKUP_BYTES:
        raise ValueError("config backup exceeds the maximum supported size")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=backup_root,
            prefix=".config-backup-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(encoded)
            temporary.flush()
            os.fsync(temporary.fileno())
        if _is_link_or_reparse(target) or target.parent.resolve(strict=True) != backup_root:
            raise ValueError("backup target is not a safe file path")
        os.replace(temporary_path, target)
        temporary_path = None
        if _is_link_or_reparse(target) or target.resolve(strict=True).parent != backup_root:
            raise ValueError("final backup path is not safe")
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return target


def create_config_backup(
    config_dir: str | Path = CONFIG_ROOT,
    backup_dir: str | Path = BACKUP_ROOT,
) -> Path:
    payload = _snapshot_payload(Path(config_dir), allow_empty=False)
    return _write_backup_payload(payload, Path(backup_dir))


def list_config_backups(
    backup_dir: str | Path = BACKUP_ROOT,
) -> list[Path]:
    root = Path(backup_dir)
    if _is_link_or_reparse(root):
        raise ValueError("backup directory cannot be a symlink or reparse point")
    if not root.exists():
        return []
    if _is_link_or_reparse(root.parent):
        raise ValueError("backup parent cannot be a symlink or reparse point")
    resolved = root.resolve(strict=True)
    if resolved.parent != root.parent.resolve(strict=True):
        raise ValueError("backup directory must remain inside its expected parent")
    files: list[Path] = []
    for entry in resolved.iterdir():
        if not _BACKUP_NAME.fullmatch(entry.name):
            continue
        if _is_link_or_reparse(entry) or not entry.is_file():
            continue
        files.append(entry)
    return sorted(files, key=lambda item: item.name, reverse=True)


def _load_validated_backup(
    backup_name: str,
    backup_dir: Path,
) -> dict[str, Any]:
    if not isinstance(backup_name, str) or not _BACKUP_NAME.fullmatch(backup_name):
        raise ValueError("invalid config backup filename")
    if _is_link_or_reparse(backup_dir) or _is_link_or_reparse(backup_dir.parent):
        raise ValueError("backup directory path cannot contain a symlink or reparse point")
    if not backup_dir.is_dir():
        raise ValueError("backup directory does not exist")
    root = backup_dir.resolve(strict=True)
    if root.parent != backup_dir.parent.resolve(strict=True):
        raise ValueError("backup directory must remain inside its expected parent")
    target = root / backup_name
    if _is_link_or_reparse(target):
        raise ValueError("backup file cannot be a symlink or reparse point")
    resolved = target.resolve(strict=True)
    if resolved.parent != root or not resolved.is_file():
        raise ValueError("backup file must remain inside data/backups")
    raw = resolved.read_bytes()
    if len(raw) > MAX_BACKUP_BYTES:
        raise ValueError("config backup exceeds the maximum supported size")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"backup is not valid JSON: {error}") from error
    if not isinstance(payload, dict) or set(payload) != {
        "format_version", "created_at", "files"
    }:
        raise ValueError("backup structure is invalid")
    if payload["format_version"] != FORMAT_VERSION:
        raise ValueError("unsupported config backup format version")
    if not isinstance(payload["created_at"], str):
        raise TypeError("backup timestamp must be a string")
    try:
        datetime.fromisoformat(payload["created_at"])
    except ValueError as error:
        raise ValueError("backup timestamp is invalid") from error
    files = payload["files"]
    if not isinstance(files, dict) or not files:
        raise ValueError("backup contains no configuration files")
    if not set(files).issubset(ALLOWED_CONFIG_FILES):
        raise ValueError("backup contains a config file outside the allowlist")

    for name, entry in files.items():
        if not isinstance(entry, dict) or set(entry) != {"content", "sha256"}:
            raise ValueError(f"backup entry is invalid: {name}")
        content = entry["content"]
        digest = entry["sha256"]
        if not isinstance(content, str) or not isinstance(digest, str):
            raise TypeError(f"backup entry fields must be strings: {name}")
        actual_digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(actual_digest, digest):
            raise ValueError(f"backup checksum mismatch: {name}")
        _validate_config_content(name, content)
    return payload


def _atomic_write_config(target: Path, content: str, config_root: Path) -> None:
    if _is_link_or_reparse(target):
        raise ValueError(f"config target cannot be a symlink or reparse point: {target.name}")
    if target.resolve(strict=False).parent != config_root:
        raise ValueError("config target must remain inside config/")
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=config_root,
            prefix=f".{target.stem}-restore-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        if _is_link_or_reparse(target):
            raise ValueError("config target changed to a link or reparse point")
        os.replace(temporary_path, target)
        temporary_path = None
        if _is_link_or_reparse(target) or target.resolve(strict=True).parent != config_root:
            raise ValueError("restored config path failed final safety check")
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _apply_validated_payload(
    payload: dict[str, Any],
    config_dir: Path,
) -> None:
    config_root = _safe_directory(config_dir)
    for name, entry in payload["files"].items():
        _atomic_write_config(
            _safe_config_path(name, config_root),
            entry["content"],
            config_root,
        )


def _restore_validated_backup(
    payload: dict[str, Any],
    *,
    config_dir: Path,
    backup_dir: Path,
) -> Path:
    # Preserve the current allowlisted config before replacing any existing file.
    rollback_payload = _snapshot_payload(config_dir, allow_empty=True)
    rollback_path = _write_backup_payload(rollback_payload, backup_dir)
    originally_present = set(rollback_payload["files"])
    try:
        _apply_validated_payload(payload, config_dir)
    except Exception:
        try:
            _apply_validated_payload(rollback_payload, config_dir)
            # Remove only allowlisted files that this restore created; never remove
            # an existing file that was not part of the pre-restore snapshot.
            for name in set(payload["files"]) - originally_present:
                target = _safe_config_path(name, config_dir)
                if target.exists() and target.is_file() and not _is_link_or_reparse(target):
                    target.unlink()
        except Exception as rollback_error:
            raise RuntimeError(
                f"config restore failed and rollback also failed; rollback snapshot: "
                f"{rollback_path.name}; {rollback_error}"
            ) from rollback_error
        raise
    return rollback_path


def request_config_restore(
    backup_name: str,
    db_path: str | Path = DEFAULT_DB_PATH,
    backup_dir: str | Path = BACKUP_ROOT,
) -> int:
    backup_root = Path(backup_dir)
    _load_validated_backup(backup_name, backup_root)
    details = json.dumps({"backup_name": backup_name}, sort_keys=True)
    return create_approval(
        "config_restore",
        details,
        "HIGH",
        db_path,
        requested_by="user",
    )


def execute_approved_config_restore(
    approval_id: int,
    db_path: str | Path = DEFAULT_DB_PATH,
    config_dir: str | Path = CONFIG_ROOT,
    backup_dir: str | Path = BACKUP_ROOT,
) -> dict[str, Any]:
    row = fetch_one(
        """
        SELECT approvals.status, action_log.status AS action_status,
               action_log.action, action_log.details, action_log.risk_level
        FROM approvals
        JOIN action_log ON action_log.id = approvals.action_log_id
        WHERE approvals.id = ?
        """,
        (approval_id,),
        db_path,
    )
    if (
        row is None
        or row["status"] != "approved"
        or row["action_status"] != "approved"
        or row["action"] != "config_restore"
        or row["risk_level"] != "HIGH"
    ):
        return {"ok": False, "message": "Config restore requires a matching HIGH approval"}

    try:
        details = json.loads(row["details"])
        backup_name = details["backup_name"]
        payload = _load_validated_backup(backup_name, Path(backup_dir))
        execute(
            """
            UPDATE action_log SET status = 'started', actor = 'config_restore'
            WHERE id = (SELECT action_log_id FROM approvals WHERE id = ?)
            """,
            (approval_id,),
            db_path,
        )
        rollback_path = _restore_validated_backup(
            payload,
            config_dir=Path(config_dir),
            backup_dir=Path(backup_dir),
        )
        execute(
            """
            UPDATE action_log SET status = 'completed', details = ?
            WHERE id = (SELECT action_log_id FROM approvals WHERE id = ?)
            """,
            (
                json.dumps(
                    {
                        "backup_name": backup_name,
                        "rollback_backup": rollback_path.name,
                        "restored_files": sorted(payload["files"]),
                    },
                    sort_keys=True,
                ),
                approval_id,
            ),
            db_path,
        )
        return {
            "ok": True,
            "message": f"Restored config backup {backup_name}; current config saved as {rollback_path.name}",
            "rollback_backup": rollback_path.name,
        }
    except Exception as error:  # noqa: BLE001 - every restore failure must be logged fail-closed
        message = str(error)[:1000]
        execute(
            """
            UPDATE action_log SET status = 'failed', details = ?
            WHERE id = (SELECT action_log_id FROM approvals WHERE id = ?)
            """,
            (json.dumps({"error": message}), approval_id),
            db_path,
        )
        return {"ok": False, "message": message}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Back up and restore allowlisted MasterControl config")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("backup", help="Create a versioned config backup")
    subparsers.add_parser("list", help="List available config backups")
    restore = subparsers.add_parser("restore", help="Request approval to restore a config backup")
    restore.add_argument("backup_name")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args(argv)
    try:
        if args.command == "backup":
            path = create_config_backup()
            print(json.dumps({"ok": True, "backup": path.name}, ensure_ascii=False))
            return 0
        if args.command == "list":
            print(json.dumps([path.name for path in list_config_backups()], ensure_ascii=False))
            return 0
        approval_id = request_config_restore(args.backup_name, args.db)
        print(json.dumps(
            {
                "ok": True,
                "approval_id": approval_id,
                "message": "Restore request created; approve it in the dashboard Pending Approvals panel.",
            },
            ensure_ascii=False,
        ))
        return 0
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        print(f"Config backup failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
