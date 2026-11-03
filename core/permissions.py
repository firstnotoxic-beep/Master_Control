# กำหนดระดับความเสี่ยงและสิทธิ์ของ action ที่ระบบรู้จัก
from enum import StrEnum


class RiskLevel(StrEnum):
    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


ACTION_RISK: dict[str, RiskLevel] = {
    "status": RiskLevel.SAFE,
    "help": RiskLevel.SAFE,
    "add_task": RiskLevel.LOW,
    "list_tasks": RiskLevel.SAFE,
    "test_medium": RiskLevel.MEDIUM,
    "gaming_mode": RiskLevel.MEDIUM,
    "focus_mode": RiskLevel.MEDIUM,
    "restore_mode": RiskLevel.MEDIUM,
    "mode_status": RiskLevel.SAFE,
    "top_processes": RiskLevel.SAFE,
}


def risk_for_action(action: str) -> RiskLevel:
    return ACTION_RISK.get(action, RiskLevel.HIGH)


def requires_approval(action: str) -> bool:
    return risk_for_action(action) in {
        RiskLevel.MEDIUM,
        RiskLevel.HIGH,
        RiskLevel.CRITICAL,
    }
