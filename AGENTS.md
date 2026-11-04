# AGENTS.md - MasterControl rules (read before every task)

## Project
Personal PC control system on Windows 11 (MSI Katana A15: Ryzen 7 8845HS, RTX 4050 6GB VRAM, 16GB RAM).
Owner is a beginner who mostly directs AI to write code. Explain simply. Chat with the owner in Thai; code, comments in English, with a short Thai header comment on each new file.

## Read first
1. docs/STATUS.md - current phase, what is VERIFIED vs UNVERIFIED, pending real-machine checks.
2. docs/BLUEPRINT.md - vision and feature list (reference only; STATUS.md wins on conflicts).

## Hard rules (never violate)
1. Lightweight: while gaming, MasterControl must use near-zero resources. No local LLM by default.
2. Rule-based first. LLM is used only when rules cannot understand a command, via the AI Provider layer (later phase).
3. An LLM or skill may only PROPOSE an action as validated data (Pydantic). Flow is always: validate -> permission check -> approval (if needed) -> executor -> verify -> log.
4. Never use shell=True, eval, exec, or os.system on any text from a user, LLM, skill, or message. Use argument lists and action allowlists.
5. Risk levels: SAFE / LOW / MEDIUM / HIGH / CRITICAL. MEDIUM+ always needs approval. CRITICAL is never done by the system.
6. Never touch game or anti-cheat processes. Only close exact names on the user's allowlist (config/modes.toml). No wildcards, no substring matching. Protected list always wins.
7. Never control fans or MSI Center. Read temperature only.
8. Secrets only in .env (gitignored, with .env.example). Never hardcode, log, or commit keys or webhook URLs. Never send sensitive data to cloud APIs.
9. Report results honestly. Verify after acting (re-scan, re-read). Never say "success" without verification. Never claim Undo without a real backup.
10. Soft reminders only. Never lock the PC or force the user.
11. Free or near-free services only. No paid API unless the owner explicitly approves.

## Working method
- Before editing: read the existing code, summarize the plan, and wait for the owner's "confirm".
- Change only the files listed in the task. Ask before touching anything else. No new features outside the current phase.
- Small milestones. No dozens of files in one go.
- Every task ships with pytest tests. Tests use mocks and fake clocks; NEVER kill real processes, sleep, or hit real network in tests.
- Before adding a library: state why, and compare with a lighter option. Prefer the standard library.
- Work on a feature branch and open a pull request. Never push directly to main.
- Do not report a feature as done if it was only tested with mocks: label it "UNVERIFIED on Windows" and add the manual check to docs/STATUS.md.
- At the end: list files changed, how to run, how to verify manually, what is NOT done, and update docs/STATUS.md.

## Skills (extension system)
New abilities are added as skills under skills/<name>/ (see docs/SKILLS.md once it exists). A skill can never bypass permissions or approval, never ships disabled-by-default checks off, and is loaded only if the owner enabled it in config/skills.toml.

## Stack
Python 3.11+, SQLite (core/db.py with schema_version migrations), Streamlit dashboard, psutil, pydantic, pytest, ruff. Dark theme with phosphor green, no animation.
