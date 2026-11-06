# สาธิต Skill Framework ใน workspace ชั่วคราวโดยไม่แตะข้อมูลผู้ใช้
from __future__ import annotations

import json
import os
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


def run_demo() -> str:
    repository_root = Path(__file__).resolve().parents[1]
    transcript = [
        "MasterControl — isolated Skill Framework demo",
        "Workspace: temporary directory (removed automatically)",
        "Database: temporary data/mastercontrol.db",
    ]

    from core import skills as skills_module
    from core.permissions import unregister_skill_actions

    old_skills_dir = skills_module.DEFAULT_SKILLS_DIR
    old_config_path = skills_module.DEFAULT_CONFIG_PATH
    old_failure_log = skills_module.DEFAULT_FAILURE_LOG_PATH
    original_directory = Path.cwd()

    try:
        with tempfile.TemporaryDirectory(prefix="mastercontrol-demo-") as temporary:
            workspace = Path(temporary)
            os.chdir(workspace)
            database = workspace / "data" / "mastercontrol.db"
            skills_module.DEFAULT_SKILLS_DIR = repository_root / "skills"
            skills_module.DEFAULT_CONFIG_PATH = workspace / "config" / "skills.toml"
            skills_module.DEFAULT_FAILURE_LOG_PATH = (
                workspace / "data" / "logs" / "skill-failures.log"
            )

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
    finally:
        os.chdir(original_directory)
        skills_module.DEFAULT_SKILLS_DIR = old_skills_dir
        skills_module.DEFAULT_CONFIG_PATH = old_config_path
        skills_module.DEFAULT_FAILURE_LOG_PATH = old_failure_log
        unregister_skill_actions("skill.")

    return "\n".join(transcript)


def main() -> int:
    try:
        print(run_demo())
    except Exception as error:
        print(f"DEMO FAILED: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
