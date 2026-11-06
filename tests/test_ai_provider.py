# ทดสอบ AI Provider fallback, privacy redaction และ proposal security
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from ai.models import ActionProposal
from ai.privacy import redact_private_data
from ai.providers import MockProvider, ProviderError
from ai.router import NoProviderAvailable, ProviderRouter
from core.ai_proposals import submit_action_proposal
from core.approval import approve, pending
from core.db import fetch_one
from core.permissions import RiskLevel, risk_for_action
from core.skills import SkillRegistry, execute_approved_skill


def _write_medium_skill(root):
    folder = root / "medium_worker"
    folder.mkdir(parents=True)
    (folder / "skill.toml").write_text(
        """
name = "medium_worker"
version = "1.0.0"
description = "Proposal approval test"
enabled-by-default = false

[[actions]]
id = "run"
description = "Run only after the Core approval flow."
risk = "SAFE"
capabilities = ["process_control"]

[actions.params]
value = "str"
""".lstrip(),
        encoding="utf-8",
    )
    (folder / "skill.py").write_text(
        """
from pathlib import Path

def run(action_id, params):
    Path("proposal-ran.txt").write_text(params["value"], encoding="utf-8")
    return {"ok": True, "message": "proposal action ran"}

def verify(action_id, params, result):
    return result.get("ok") is True
""",
        encoding="utf-8",
    )


def test_provider_router_falls_back_after_provider_error():
    groq = MockProvider("groq", error="temporary provider failure")
    gemini = MockProvider("gemini", response='{"action":"skill.notes.save"}')
    router = ProviderRouter(
        {"groq": groq, "gemini": gemini},
        environment={},
    )

    result = router.generate("Return a structured proposal", {"topic": "test"})

    assert result.provider == "gemini"
    assert result.attempted == ("groq", "gemini")
    assert result.content == '{"action":"skill.notes.save"}'
    assert len(groq.calls) == 1
    assert len(gemini.calls) == 1


def test_unconfigured_or_stubbed_providers_never_make_a_live_request():
    router_without_keys = ProviderRouter(environment={})
    with pytest.raises(NoProviderAvailable):
        router_without_keys.generate("test")

    router_with_key = ProviderRouter(environment={"GROQ_API_KEY": "test-only"})
    with pytest.raises(NoProviderAvailable):
        router_with_key.generate("test")


def test_private_context_is_redacted_unless_consent_is_explicit():
    context = {
        "task": "summarize",
        "email": "private@example.invalid",
        "nested": {"api_key": "not-a-real-key", "note": "ordinary context"},
    }

    redacted = redact_private_data(context)
    consented = redact_private_data(context, consent=True)

    assert redacted["email"] == "[REDACTED]"
    assert redacted["nested"]["api_key"] == "[REDACTED]"
    assert redacted["nested"]["note"] == "ordinary context"
    assert consented == context
    assert redacted is not context


def test_provider_router_redacts_context_before_provider_receives_it():
    provider = MockProvider("groq", response="safe response")
    router = ProviderRouter({"groq": provider}, environment={})

    router.generate(
        "Summarize",
        {"email": "private@example.invalid", "topic": "school"},
    )

    assert provider.calls[0][1]["email"] == "[REDACTED]"
    assert provider.calls[0][1]["topic"] == "school"


def test_action_proposal_rejects_invalid_json_and_extra_fields():
    with pytest.raises(ValidationError):
        ActionProposal.model_validate_json("{not json")

    with pytest.raises(ValidationError):
        ActionProposal.model_validate_json(
            json.dumps(
                {
                    "action": "skill.medium_worker.run",
                    "parameters": {"value": "hello"},
                    "rationale": "test",
                    "execute_now": True,
                }
            )
        )

    with pytest.raises(ValidationError):
        ActionProposal.model_validate_json(
            json.dumps(
                {
                    "action": "shell.run",
                    "parameters": {},
                    "rationale": "not an allowed Skill action",
                }
            )
        )


def test_medium_ai_proposal_creates_approval_and_never_executes_directly(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / "skills"
    _write_medium_skill(skills_dir)
    config = tmp_path / "config" / "skills.toml"
    config.parent.mkdir(parents=True)
    config.write_text('enabled = ["medium_worker"]\n', encoding="utf-8")
    database = tmp_path / "data" / "mastercontrol.db"
    marker = tmp_path / "proposal-ran.txt"
    registry = SkillRegistry(skills_dir, config, database)

    proposal = json.dumps(
        {
            "action": "skill.medium_worker.run",
            "parameters": {"value": "approved"},
            "rationale": "Complete the requested local action.",
        }
    )
    result = submit_action_proposal(
        proposal,
        registry=registry,
        db_path=database,
    )

    assert result["status"] == "pending_approval"
    assert result["executed"] is False
    assert result["preview"]["risk"] == RiskLevel.MEDIUM.value
    assert result["preview"]["approval_required"] is True
    assert not marker.exists()
    assert len(pending(database)) == 1
    assert risk_for_action("skill.medium_worker.run") == RiskLevel.MEDIUM

    approve(result["approval_id"], db_path=database)
    log = fetch_one(
        "SELECT status FROM action_log WHERE action = 'skill.medium_worker.run'",
        db_path=database,
    )
    assert log["status"] == "approved"
    executed = execute_approved_skill(result["approval_id"], database)

    assert executed["ok"] is True
    assert marker.read_text(encoding="utf-8") == "approved"
