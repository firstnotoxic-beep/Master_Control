# สาธิต Skill Framework ใน workspace ชั่วคราวโดยไม่แตะข้อมูลผู้ใช้
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILLS = {
    "quick_note": (
        "save",
        {
            "filename": "demo-note.md",
            "title": "MasterControl demo",
            "body": "This note was written inside a temporary demo workspace.",
        },
    ),
    "task_list": ("add", {"description": "Review the MasterControl demo"}),
    "brain_dump": ("capture", {"text": "A demo thought stored only in the temporary workspace."}),
    "daily_report": ("generate", {}),
}


def _run_worker() -> str:
    repository_root = Path(__file__).resolve().parents[1]
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))

    for skill_name in SKILLS:
        source = repository_root / "skills" / skill_name
        target = Path("skills") / skill_name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)

    from core import skills as skills_module
    from core.permissions import unregister_skill_actions

    old_failure_log = skills_module.DEFAULT_FAILURE_LOG_PATH
    database = Path("data/mastercontrol.db")

    transcript = [
        "MasterControl — isolated Skill Framework demo",
        "Workspace: temporary directory (removed after worker process exits)",
        "Database: temporary data/mastercontrol.db",
    ]
    try:
        skills_module.DEFAULT_FAILURE_LOG_PATH = Path("data/logs/skill-failures.log")

        from core.commands import handle_command

        for skill_name, (action_id, parameters) in SKILLS.items():
            preview = handle_command(f"skill enable {skill_name}", database)
            if not preview.get("ok") or not preview.get("confirmation_required"):
                raise RuntimeError(
                    f"Could not preview {skill_name}: {preview.get('message', 'unknown error')}"
                )
            enabled = handle_command(
                f"skill enable {skill_name} confirm", database
            )
            if not enabled.get("ok"):
                raise RuntimeError(
                    f"Could not enable {skill_name}: {enabled.get('message', 'unknown error')}"
                )

            request = (
                f"run {skill_name}.{action_id} "
                f"{json.dumps(parameters, ensure_ascii=False)}"
            )
            result = handle_command(request, database)
            if not result.get("ok") or result.get("approval_id"):
                raise RuntimeError(
                    f"{skill_name}.{action_id} did not complete through the "
                    f"configured SAFE/LOW path: {result.get('message', 'approval required')}"
                )
            if not result.get("verified"):
                raise RuntimeError(
                    f"{skill_name}.{action_id} did not pass Skill verification"
                )
            transcript.append(
                f"[PASS] {skill_name}.{action_id}: {result.get('message', '')} "
                f"(risk={preview['preview']['actions'][0]['final_risk']}, "
                "approval=not required, verified=True)"
            )

        transcript.append(
            "Approval note: all four built-in demo actions are SAFE/LOW by their "
            "manifests, so policy correctly does not request approval. MEDIUM+ "
            "actions remain approval-gated in the dashboard."
        )
        transcript.append("Isolation check: all demo data stayed under the temporary workspace.")
        return "\n".join(transcript)
    finally:
        skills_module.DEFAULT_FAILURE_LOG_PATH = old_failure_log
        unregister_skill_actions("skill.")


def run_demo() -> str:
    repository_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    existing_pythonpath = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        str(repository_root)
        if not existing_pythonpath
        else str(repository_root) + os.pathsep + existing_pythonpath
    )

    # The worker process owns all SQLite connections. Exiting it closes Windows
    # file handles before the parent TemporaryDirectory removes the database.
    with tempfile.TemporaryDirectory(prefix="mastercontrol-demo-") as temporary:
        result = subprocess.run(
            [sys.executable, "-m", "scripts.demo", "--worker"],
            cwd=temporary,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"isolated demo worker failed: {detail}")
        return result.stdout.strip()


def main() -> int:
    try:
        transcript = _run_worker() if "--worker" in sys.argv[1:] else run_demo()
        print(transcript)
    except Exception as error:
        print(f"DEMO FAILED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
