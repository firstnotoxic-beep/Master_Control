# Core-owned validation and permission routing for AI-generated Skill proposals.
from __future__ import annotations

from pathlib import Path
from typing import Any

from ai.models import ActionProposal
from core.approval import create_approval
from core.db import DEFAULT_DB_PATH
from core.permissions import RiskLevel, requires_approval
from core.skills import SkillRegistry


def submit_action_proposal(
    raw_json: str,
    *,
    registry: SkillRegistry | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Validate an AI proposal and route it through the existing Skill security core.

    The provider returns data only. This Core-owned function validates the action
    against the enabled Skill manifest and permission registry. MEDIUM/HIGH actions
    create a stored approval request and are not executed. CRITICAL is refused.
    SAFE/LOW actions may be passed to the existing Skill executor only after all
    validation and permission checks succeed.
    """
    proposal = ActionProposal.model_validate_json(raw_json)
    _prefix, skill_name, action_id = proposal.action.split(".", 2)
    active_registry = registry or SkillRegistry(db_path=db_path)
    prepared = active_registry.prepare_action(
        skill_name,
        action_id,
        proposal.parameters,
    )
    preview = active_registry.preview_action(
        skill_name,
        action_id,
        proposal.parameters,
    )

    if prepared.risk == RiskLevel.CRITICAL:
        return {
            "status": "refused",
            "message": "CRITICAL actions are never executed by MasterControl",
            "preview": preview,
            "executed": False,
        }

    if requires_approval(prepared.action_key):
        approval_id = create_approval(
            prepared.action_key,
            prepared.approval_details(),
            prepared.risk.value,
            db_path,
            requested_by="ai_proposal",
        )
        return {
            "status": "pending_approval",
            "message": "Proposal validated; explicit user approval is required",
            "approval_id": approval_id,
            "preview": preview,
            "executed": False,
        }

    result = active_registry.execute_action(prepared)
    return {
        "status": "completed" if result.get("ok") else "failed",
        "message": result.get("message", ""),
        "preview": preview,
        "result": result,
        "executed": bool(result.get("ok")),
    }
