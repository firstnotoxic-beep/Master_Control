# ทดสอบ Skill Framework ด้วยฐานข้อมูลและไฟล์จำลอง
import json
import sys
from pathlib import Path

import pytest

from core.approval import approve, create_approval
from core.db import execute, fetch_one
from core.permissions import RiskLevel, minimum_risk_for_capabilities
from core.skills import SkillRegistry


def make_skill(root: Path, name: str, *, risk="SAFE", capabilities=None, body=None):
    folder = root / name
    folder.mkdir(parents=True)
    caps = capabilities if capabilities is not None else ["notify"]
    manifest = f"""
name = "{name}"
version = "1.0.0"
description = "Test skill"
enabled-by-default = false

[[actions]]
id = "go"
description = "Test action"
risk = "{risk}"
capabilities = {json.dumps(caps)}

[actions.params]
value = "str"
"""
    (folder / "skill.toml").write_text(manifest, encoding="utf-8")
    source = body or """
def run(action_id, params):
    return {"ok": True, "message": params.value, "verified": False}

def verify(action_id, params, result):
    return result["message"] == params.value
"""
    (folder / "skill.py").write_text(source, encoding="utf-8")
    return folder


def write_config(path: Path, names):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("enabled = " + json.dumps(names) + "\n", encoding="utf-8")


def test_disabled_skill_never_loads(tmp_path):
    root = tmp_path / "skills"
    folder = make_skill(root, "quiet")
    (folder / "skill.py").write_text("raise RuntimeError('must not import')", encoding="utf-8")
    registry = SkillRegistry(root, tmp_path / "config" / "skills.toml", tmp_path / "db.sqlite")
    assert "quiet" not in registry._loaded
    assert "mastercontrol_skill_quiet" not in sys.modules
    assert not registry.list_skills()[0]["enabled"]


def test_broken_manifest_is_skipped(tmp_path):
    root = tmp_path / "skills"
    folder = root / "broken"
    folder.mkdir(parents=True)
    (folder / "skill.toml").write_text("this is not valid = [", encoding="utf-8")
    config = tmp_path / "skills.toml"
    write_config(config, ["broken"])
    registry = SkillRegistry(root, config, tmp_path / "db.sqlite")
    assert "broken" not in registry._loaded
    assert "broken" in registry._errors


def test_capability_risk_cannot_be_lowered():
    assert minimum_risk_for_capabilities(["file_delete"], RiskLevel.SAFE) == RiskLevel.HIGH
    assert minimum_risk_for_capabilities(["process_control"], RiskLevel.LOW) == RiskLevel.MEDIUM


def test_medium_skill_requires_approval(tmp_path):
    root = tmp_path / "skills"
    make_skill(root, "moderate", risk="MEDIUM", capabilities=["process_control"])
    config = tmp_path / "skills.toml"
    write_config(config, ["moderate"])
    db = tmp_path / "db.sqlite"
    registry = SkillRegistry(root, config, db)
    prepared = registry.prepare_action("moderate", "go", {"value": "ok"})
    result = registry.execute_action(prepared)
    assert result["approval_required"] is True
    approval_id = create_approval(prepared.action_key, prepared.approval_details(), prepared.risk.value, db)
    approve(approval_id, db_path=db)
    result = registry.execute_action(prepared, approval_id)
    assert result == {"ok": True, "message": "ok", "verified": True}



def test_execute_revalidates_prepared_action_and_stored_approval(tmp_path):
    root = tmp_path / "skills"
    source = """
def run(action_id, params):
    raise AssertionError("untrusted action must not execute")

def verify(action_id, params, result):
    return False
"""
    make_skill(root, "secure", risk="MEDIUM", capabilities=["process_control"], body=source)
    config = tmp_path / "skills.toml"
    write_config(config, ["secure"])
    db = tmp_path / "db.sqlite"
    registry = SkillRegistry(root, config, db)
    prepared = registry.prepare_action("secure", "go", {"value": "safe"})

    forged = prepared.__class__(
        skill_name=prepared.skill_name,
        action_id=prepared.action_id,
        action_key=prepared.action_key,
        params=prepared.params,
        risk=RiskLevel.SAFE,
        capabilities=prepared.capabilities,
    )
    rejected = registry.execute_action(forged)
    assert rejected["ok"] is False
    assert "Prepared action rejected" in rejected["message"]

    approval_id = create_approval(
        prepared.action_key, prepared.approval_details(), prepared.risk.value, db
    )
    approve(approval_id, db_path=db)
    execute(
        "UPDATE action_log SET details = ? WHERE id = "
        "(SELECT action_log_id FROM approvals WHERE id = ?)",
        ('{"skill_name":"secure","action_id":"go","params":{"value":"tampered"}}',
         approval_id),
        db,
    )
    rejected = registry.execute_action(prepared, approval_id)
    assert rejected["ok"] is False
    assert "Approved parameters do not match" in rejected["message"]

def test_skill_exception_is_caught_and_logged(tmp_path):
    root = tmp_path / "skills"
    source = """
def run(action_id, params):
    raise RuntimeError("expected test exception")

def verify(action_id, params, result):
    return False
"""
    make_skill(root, "broken_run", body=source)
    config = tmp_path / "skills.toml"
    write_config(config, ["broken_run"])
    db = tmp_path / "db.sqlite"
    registry = SkillRegistry(root, config, db)
    prepared = registry.prepare_action("broken_run", "go", {"value": "x"})
    result = registry.execute_action(prepared)
    assert result["ok"] is False
    assert fetch_one("SELECT status FROM action_log ORDER BY id DESC", db_path=db)["status"] == "failed"


def test_quick_note_rejects_path_traversal(tmp_path, monkeypatch):
    from skills.quick_note import skill

    monkeypatch.setattr(skill, "NOTES_ROOT", tmp_path / "notes")
    with pytest.raises(ValueError):
        skill._path("../outside.md")
    with pytest.raises(ValueError):
        skill._path("folder/note.md")


def test_enable_persists_in_skill_state(tmp_path):
    root = tmp_path / "skills"
    make_skill(root, "enable_me")
    config = tmp_path / "config" / "skills.toml"
    db = tmp_path / "db.sqlite"
    registry = SkillRegistry(root, config, db)
    preview = registry.preview("enable_me")
    assert preview["actions"][0]["final_risk"] == "SAFE"
    result = registry.enable("enable_me")
    assert result["ok"] is True
    row = fetch_one("SELECT enabled, version FROM skill_state WHERE name = 'enable_me'", db_path=db)
    assert row["enabled"] == 1
    assert row["version"] == "1.0.0"
