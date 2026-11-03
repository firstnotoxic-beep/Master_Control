# วางแผน ปิด และกู้คืนโปรเซสตาม allowlist โดยตรวจสอบผลจริงทุกครั้ง
from __future__ import annotations

import fnmatch
import getpass
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

import psutil

from core.db import DEFAULT_DB_PATH, execute, fetch_one, init_db

LOGGER = logging.getLogger(__name__)
DEFAULT_CONFIG_PATH = Path("config/modes.toml")
PROTECTED_DEFAULTS = [
    "RobloxPlayerBeta.exe",
    "RobloxPlayerLauncher.exe",
    "EasyAntiCheat*",
    "BEService*",
    "vgc.exe",
    "explorer.exe",
    "csrss.exe",
    "winlogon.exe",
    "dwm.exe",
    "svchost.exe",
    "MsMpEng.exe",
    "Discord.exe",
    "nvidia*",
    "nv*",
    "amd*",
    "MSI Center*",
    "Dragon Center*",
]


class ModeConfigError(ValueError):
    """Raised when a modes TOML file is unsafe or malformed."""


def _load_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    import tomllib

    path = Path(config_path)
    if not path.exists():
        raise ModeConfigError(f"ไม่พบไฟล์ config: {path}")
    try:
        with path.open("rb") as config_file:
            config = tomllib.load(config_file)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ModeConfigError(f"config ไม่ถูกต้อง: {error}") from error
    configured_protected = [
        str(item) for item in config.get("protected", {}).get("processes", [])
    ]
    protected = list(dict.fromkeys(PROTECTED_DEFAULTS + configured_protected))
    modes = config.get("modes")
    if not isinstance(modes, dict):
        raise ModeConfigError("ต้องมี [modes.gaming] และ [modes.focus]")
    for mode_name in ("gaming", "focus"):
        mode = modes.get(mode_name)
        if not isinstance(mode, dict):
            raise ModeConfigError(f"ไม่มี modes.{mode_name}")
        closeable = mode.get("closeable", [])
        keep = mode.get("keep", [])
        if not isinstance(closeable, list) or not isinstance(keep, list):
            raise ModeConfigError(f"modes.{mode_name} ต้องเป็นรายการ")
        for item in closeable:
            if not isinstance(item, str):
                raise ModeConfigError("closeable ต้องเป็นชื่อโปรเซสแบบข้อความ")
            if "*" in item or "?" in item or item != Path(item).name or not item.lower().endswith(".exe"):
                raise ModeConfigError(f"closeable ต้องเป็นชื่อ .exe แบบ exact: {item}")
            if isinstance(mode.get("restore_path", {}), dict) and item in mode.get("restore_path", {}):
                restore_path = mode["restore_path"][item]
                if not Path(restore_path).is_absolute():
                    raise ModeConfigError(f"restore_path ต้องเป็น absolute path: {item}")
        for item in keep:
            if not isinstance(item, str) or "*" in item or "?" in item:
                raise ModeConfigError(f"keep ต้องเป็นชื่อแบบ exact: {item}")
        for item in closeable:
            if any(fnmatch.fnmatchcase(item.lower(), pattern.lower()) for pattern in protected):
                LOGGER.warning("protected wins over closeable: %s", item)
    config["protected"] = protected
    return config


def _restore_path(mode: dict[str, Any], process_name: str) -> str | None:
    paths = mode.get("restore_path", {})
    if not isinstance(paths, dict):
        return None
    for name, path in paths.items():
        if name.lower() == process_name.lower():
            return str(path)
    return None


def _is_protected(name: str, protected: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(name.lower(), pattern.lower()) for pattern in protected)


def plan_mode(
    name: str,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    process_iter: Any = psutil.process_iter,
) -> dict[str, Any]:
    config = _load_config(config_path)
    mode = config["modes"].get(name.lower())
    if mode is None:
        raise ModeConfigError(f"ไม่รู้จัก mode: {name}")
    closeable = {item.lower() for item in mode["closeable"]}
    keep = {item.lower() for item in mode["keep"]}
    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for process in process_iter(["pid", "name", "memory_info", "username"]):
        try:
            process_name = process.info.get("name") or ""
            if process_name.lower() not in closeable:
                continue
            reason = None
            if _is_protected(process_name, config["protected"]):
                reason = "protected"
            elif process_name.lower() in keep:
                reason = "keep"
            elif process.info.get("username") != getpass.getuser():
                reason = "different_user_or_elevated"
            if reason:
                skipped.append({"name": process_name, "pid": process.info["pid"], "reason": reason})
                continue
            candidates.append(
                {
                    "name": process_name,
                    "pid": process.info["pid"],
                    "ram_mb": round(process.info["memory_info"].rss / (1024 * 1024), 2),
                    "restore_path": _restore_path(mode, process_name),
                }
            )
        except (psutil.Error, AttributeError, KeyError):
            skipped.append({"pid": getattr(process, "pid", None), "reason": "access_denied"})
    return {
        "mode": name.lower(),
        "protected": config["protected"],
        "close": candidates,
        "skipped": skipped,
        "estimated_ram_freed_mb": round(sum(item["ram_mb"] for item in candidates), 2),
        "dry_run": True,
    }


def _approval_is_valid(plan: dict[str, Any], db_path: str | Path) -> bool:
    approval_id = plan.get("approval_id")
    if not approval_id:
        return False
    row = fetch_one("SELECT status FROM approvals WHERE id = ?", (approval_id,), db_path)
    return row is not None and row["status"] == "approved"


def apply_mode(plan: dict[str, Any], db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    init_db(db_path)
    if not _approval_is_valid(plan, db_path):
        execute(
            "INSERT INTO action_log (action, details, risk_level, status) VALUES (?, ?, ?, ?)",
            ("apply_mode", json.dumps(plan), "MEDIUM", "refused"),
            db_path,
        )
        return {"ok": False, "message": "ต้องมี approval ที่อนุมัติแล้วก่อน apply mode", "results": []}
    results: list[dict[str, Any]] = []
    for item in plan.get("close", []):
        result = {"name": item["name"], "pid": item["pid"], "status": "access denied"}
        try:
            process = psutil.Process(item["pid"])
            if process.name().lower() != item["name"].lower():
                result["status"] = "still running"
            elif _is_protected(item["name"], plan.get("protected", PROTECTED_DEFAULTS)):
                result["status"] = "skipped protected"
            else:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except psutil.TimeoutExpired:
                    pass
                survivor = psutil.Process(item["pid"])
                if survivor.is_running() and survivor.name().lower() == item["name"].lower():
                    result["status"] = "still running"
                else:
                    result["status"] = "closed"
        except psutil.AccessDenied:
            result["status"] = "access denied"
        except psutil.NoSuchProcess:
            result["status"] = "closed"
        except psutil.Error:
            result["status"] = "access denied"
        results.append(result)
    closed = [
        {"name": item["name"], "pid": item["pid"], "restore_path": item.get("restore_path")}
        for item, result in zip(plan.get("close", []), results)
        if result["status"] == "closed"
    ]
    session_id = execute(
        "INSERT INTO mode_sessions (mode_name, closed_processes, status) VALUES (?, ?, ?)",
        (plan["mode"], json.dumps(closed), "completed"),
        db_path,
    )
    execute(
        "INSERT INTO action_log (action, details, risk_level, status) VALUES (?, ?, ?, ?)",
        ("apply_mode", json.dumps({"session_id": session_id, "results": results}), "MEDIUM", "completed"),
        db_path,
    )
    return {"ok": True, "session_id": session_id, "results": results}


def restore_mode(session_id: int, db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    init_db(db_path)
    row = fetch_one("SELECT * FROM mode_sessions WHERE id = ?", (session_id,), db_path)
    if row is None:
        return {"ok": False, "message": "ไม่พบ mode session", "results": []}
    results = []
    for item in json.loads(row["closed_processes"]):
        path = item.get("restore_path")
        result = {"name": item["name"], "status": "not restored", "reason": ""}
        if not path:
            result["reason"] = "ไม่มี restore_path"
        elif not Path(path).exists():
            result["reason"] = "ไม่พบไฟล์ restore_path"
        else:
            try:
                subprocess.Popen([path], shell=False)
                result["status"] = "launched"
            except OSError as error:
                result["reason"] = str(error)
        results.append(result)
    execute(
        "INSERT INTO action_log (action, details, risk_level, status) VALUES (?, ?, ?, ?)",
        ("restore_mode", json.dumps({"session_id": session_id, "results": results}), "MEDIUM", "completed"),
        db_path,
    )
    return {"ok": True, "session_id": session_id, "results": results}
