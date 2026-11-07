# ทดสอบ demo แบบแยก process เพื่อไม่รบกวน Skill registry ของชุดทดสอบ
import subprocess
import sys
from pathlib import Path


def test_demo_runs_with_temporary_data_and_verifies_all_skills():
    repository_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [sys.executable, "-m", "scripts.demo"],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[PASS] quick_note.save" in result.stdout
    assert "[PASS] task_list.add" in result.stdout
    assert "[PASS] brain_dump.capture" in result.stdout
    assert "[PASS] daily_report.generate" in result.stdout
    assert "verified=True" in result.stdout
    assert "temporary workspace" in result.stdout
