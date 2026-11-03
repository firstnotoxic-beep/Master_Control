# ทดสอบการกำหนดความเสี่ยงและ approval gate
from core.permissions import RiskLevel, requires_approval, risk_for_action


def test_medium_and_above_require_approval():
    assert requires_approval("test_medium")
    assert risk_for_action("test_medium") == RiskLevel.MEDIUM
    assert not requires_approval("status")


def test_unknown_actions_are_high_risk():
    assert risk_for_action("unknown") == RiskLevel.HIGH
