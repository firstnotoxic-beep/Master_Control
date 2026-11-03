# ทดสอบ telemetry และ mode engine ด้วยโปรเซสจำลองเท่านั้น ไม่ปิดโปรเซสจริง
from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from core.approval import approve, create_approval
from core.db import execute, init_db
from core.modes import ModeConfigError, apply_mode, plan_mode, restore_mode
from core.telemetry import _gpu_info


def write_config(tmp_path, closeable="Notepad.exe", protected="Discord.exe"):
    config = tmp_path / "modes.toml"
    config.write_text(
        f"""
[protected]
processes = ["{protected}"]

[modes.gaming]
closeable = ["{closeable}"]
keep = []

[modes.focus]
closeable = []
keep = []
""",
        encoding="utf-8",
    )
    return config


def fake_process(name, pid=10, username=None, rss=1024):
    return SimpleNamespace(
        pid=pid,
        info={
            "name": name,
            "pid": pid,
            "username": username or __import__("getpass").getuser(),
            "memory_info": SimpleNamespace(rss=rss),
        },
    )


def test_protected_wins_and_dry_run_does_not_close(tmp_path):
    process = fake_process("Discord.exe")
    plan = plan_mode(
        "gaming",
        write_config(tmp_path, closeable="Discord.exe", protected="Discord.exe"),
        lambda _: [process],
    )
    assert plan["close"] == []
    assert plan["skipped"][0]["reason"] == "protected"
    assert not hasattr(process, "terminate")


@pytest.mark.parametrize("name", ["Discord", "Discord*.exe", "Discord?.exe"])
def test_closeable_must_be_exact_exe_name(tmp_path, name):
    with pytest.raises(ModeConfigError):
        plan_mode("gaming", write_config(tmp_path, closeable=name), lambda _: [])


def test_apply_without_approval_is_refused(tmp_path):
    result = apply_mode({"mode": "gaming", "close": []}, tmp_path / "db.sqlite")
    assert result["ok"] is False


def test_apply_reports_survivor_without_killing_real_process(tmp_path, monkeypatch):
    class FakeProcess:
        def name(self):
            return "Notepad.exe"

        def terminate(self):
            pass

        def wait(self, timeout):
            raise __import__("psutil").TimeoutExpired(timeout)

        def is_running(self):
            return True

    db_path = tmp_path / "db.sqlite"
    approval_id = create_approval("gaming_mode", "plan", "MEDIUM", db_path)
    approve(approval_id, db_path=db_path)
    monkeypatch.setattr("core.modes.psutil.Process", lambda pid: FakeProcess())
    plan = {
        "mode": "gaming",
        "approval_id": approval_id,
        "protected": [],
        "close": [{"name": "Notepad.exe", "pid": 1, "ram_mb": 1}],
    }
    result = apply_mode(plan, db_path)
    assert result["results"][0]["status"] == "still running"


def test_restore_reports_missing_restore_path(tmp_path):
    db_path = tmp_path / "db.sqlite"
    init_db(db_path)
    session_id = execute(
        "INSERT INTO mode_sessions (mode_name, closed_processes, status) VALUES (?, ?, ?)",
        ("gaming", '[{"name": "Notepad.exe", "restore_path": null}]', "completed"),
        db_path,
    )
    result = restore_mode(session_id, db_path)
    assert result["results"][0]["reason"] == "ไม่มี restore_path"


def test_missing_nvidia_smi_returns_none(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", missing)
    assert _gpu_info() == {
        "name": None,
        "vram_used_mb": None,
        "vram_total_mb": None,
        "temperature_c": None,
    }


def test_invalid_config_refuses_mode(tmp_path):
    config = write_config(tmp_path)
    config.write_text("[modes.gaming]\ncloseable = [\n", encoding="utf-8")
    with pytest.raises(ModeConfigError):
        plan_mode("gaming", config, lambda _: [])
