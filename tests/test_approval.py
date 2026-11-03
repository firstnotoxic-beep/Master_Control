# ทดสอบวงจรคำขออนุมัติและการบันทึกผู้ตัดสินใจ
from core.approval import approve, cancel, create_approval, pending
from core.db import fetch_one


def test_approve_updates_action_log(tmp_path):
    db_path = tmp_path / "test.db"
    approval_id = create_approval("test_medium", "stub", "MEDIUM", db_path)
    assert len(pending(db_path)) == 1
    approve(approval_id, decided_by="tester", db_path=db_path)
    assert not pending(db_path)
    row = fetch_one("SELECT status, actor FROM action_log", db_path=db_path)
    assert row["status"] == "approved"
    assert row["actor"] == "tester"


def test_cancel_updates_request(tmp_path):
    db_path = tmp_path / "test.db"
    approval_id = create_approval("test_medium", "stub", "MEDIUM", db_path)
    cancel(approval_id, db_path=db_path)
    assert fetch_one("SELECT status FROM approvals", db_path=db_path)["status"] == "cancelled"
