# Skill permission registry and capability risk floors.
from enum import StrEnum


class RiskLevel(StrEnum):
    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

ACTION_RISK: dict[str, RiskLevel] = {
    "status": RiskLevel.SAFE, "help": RiskLevel.SAFE,
    "add_task": RiskLevel.LOW, "list_tasks": RiskLevel.SAFE,
    "test_medium": RiskLevel.MEDIUM, "gaming_mode": RiskLevel.MEDIUM,
    "focus_mode": RiskLevel.MEDIUM, "restore_mode": RiskLevel.MEDIUM,
    "mode_status": RiskLevel.SAFE, "top_processes": RiskLevel.SAFE,
}
_ORDER = {RiskLevel.SAFE: 0, RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2, RiskLevel.HIGH: 3, RiskLevel.CRITICAL: 4}
CAPABILITY_MINIMUM_RISK = {
    "file_read": RiskLevel.LOW, "file_write": RiskLevel.SAFE,
    "file_delete": RiskLevel.HIGH, "process_control": RiskLevel.MEDIUM,
    "network": RiskLevel.LOW, "notify": RiskLevel.SAFE,
    "system_setting": RiskLevel.HIGH,
}
_SKILL_ACTIONS: set[str] = set()

def minimum_risk_for_capabilities(capabilities, declared_risk):
    risk = declared_risk
    for capability in capabilities:
        minimum = CAPABILITY_MINIMUM_RISK.get(capability)
        if minimum is None:
            raise ValueError(f"unknown capability: {capability}")
        if _ORDER[minimum] > _ORDER[risk]:
            risk = minimum
    return risk

def register_skill_action(action: str, risk: RiskLevel) -> None:
    if not action.startswith("skill.") or action.count(".") != 2:
        raise ValueError("invalid Skill action key")
    ACTION_RISK[action] = risk
    _SKILL_ACTIONS.add(action)

def unregister_skill_actions(prefix: str) -> None:
    for action in tuple(_SKILL_ACTIONS):
        if action.startswith(prefix):
            ACTION_RISK.pop(action, None)
            _SKILL_ACTIONS.discard(action)

def risk_for_action(action: str) -> RiskLevel:
    return ACTION_RISK.get(action, RiskLevel.HIGH)

def requires_approval(action: str) -> bool:
    return risk_for_action(action) in {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}
