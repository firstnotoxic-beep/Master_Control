# MasterControl - STATUS (single source of truth)

## Constraint
Owner cannot test on the target Windows machine for now. All results below are mock/sandbox only unless marked VERIFIED.

## CI
- CI workflow exists at `.github/workflows/ci.yml`.
- Runs on a GitHub-hosted Windows runner with Python 3.12 for pull requests targeting `main` and pushes to `main` only.
- Runs dependency installation, Ruff, and pytest. Tests use mocks only; CI does not verify behavior on the owner's Windows PC, which remains UNVERIFIED.

## Architecture changes since the original blueprint
- Cloud-first free APIs (Groq -> Gemini -> GitHub Models) replace Local AI as default. Local AI (Ollama, 3B) is an optional plugin, off during gaming.
- Auto-Boot via BIOS dropped (unsupported on most laptops). Morning SITREP runs at login.
- Gaming Lock, Gaming Mode 2.0, Auto-Wingman merged into one Mode Engine.
- OpenClaw to be replaced by a MasterControl Discord bot (Phase 6); useful skills get migrated.
- New: Skill Framework (Phase 4) so abilities can be added later without rewriting core.

## Phase status
| Phase | Scope | Status |
|---|---|---|
| 1 | Foundation: db, permissions, approval, commands, notify, dashboard | Done, UNVERIFIED on Windows (real toast + Discord) |
| 2 | Telemetry, Process Monitor, Mode Engine (Gaming/Focus), mode_sessions (schema v2) | Done in mocks, UNVERIFIED |
| 3 | Alert Engine: bedtime, deadline, VIP, snooze, vacation, scheduler, Notification Center (schema v3, tasks got due_at + sender) | Done in mocks (21 tests), UNVERIFIED |
| 4 | Skill Framework: opt-in loader, manifest validation, capability risk floors, command routing, approval dispatch, quick_note, task_list, and brain_dump examples | Code complete, CI verified; Windows verification pending (#11); task_list: CI verified, Windows verification pending; brain_dump: CI verification pending |
| 5 | AI Provider Layer (Groq -> Gemini -> GitHub Models), JSON proposals via Pydantic | Planned |
| 6 | Discord bot with approve/cancel buttons (owner User ID only), OpenClaw migration | Planned |
| 7+ | Task Engine, Morning SITREP, Voice (faster-whisper), File/Screenshot intelligence | Planned |

## Pending real-machine checks (do when back at the PC)
Phase 1
- [ ] pytest passes; dashboard opens
- [ ] Test notification arrives as Windows toast AND in Discord
- [ ] Health endpoint (if any) binds to 127.0.0.1 only, or is removed
- [ ] .env is gitignored; no webhook URL in repo
Phase 2
- [ ] Dashboard CPU/RAM/VRAM/GPU temp match Task Manager and nvidia-smi
- [ ] "gaming mode" shows dry-run only; Notepad stays open
- [ ] After approval Notepad closes, verified gone, logged in action_log + mode_sessions
- [ ] "restore mode" relaunches Notepad; honest report for entries without restore_path
- [ ] Adding Discord.exe or anti-cheat to closeable is rejected
Phase 3
- [ ] Migration v1->v2->v3 works on an existing DB with data
- [ ] Bedtime set 2 min ahead -> toast + Discord
- [ ] Task due in 1h -> Warning, repeats until ack
- [ ] Snooze works; vacation mode silences bedtime
- [ ] Only one scheduler instance runs; idle CPU near 0%

Phase 4
- [ ] Run `pytest -q` and `ruff check .` on Python 3.11+ with the existing dependencies
- [ ] Verify schema migration v3->v4 preserves existing tasks, approvals, and action_log rows
- [ ] Confirm no Skill loads unless listed in config/skills.toml; malformed manifests are skipped
- [ ] Review each Skill source before enabling; confirm capability floors are raised and logged
- [ ] Confirm MEDIUM+ Skill actions remain pending until explicit approval and are logged after verification
- [ ] Confirm quick_note rejects traversal and writes only within data/notes/\n- [ ] Confirm brain_dump captures append-only timestamped notes only within data/brain_dump/ and rejects symlink/junction/reparse escapes\n- [ ] Confirm brain_dump list/search behavior, input limits, empty-search rejection, and fail-closed action-log behavior
- [ ] Verify dashboard lists installed/enabled Skills, capability/risk summaries, last errors, and enable/disable controls
- [ ] Test enable/disable persistence across dashboard restart
- [ ] Confirm Python Skill code is treated as trusted local code, not an OS sandbox

## Open questions
- What OpenClaw does today (channel, skills) - needed for Phase 6.
- Python version on the machine (need 3.11+).
