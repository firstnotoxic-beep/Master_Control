# MasterControl - STATUS (single source of truth)

> This file records the repository's implementation and verification status. The roadmap describes intended work; it does not make planned features complete.

## Constraint
Owner cannot test on the target Windows machine for now. All results below are mock/sandbox or CI results unless explicitly marked VERIFIED on the owner's actual machine.

## CI
- Workflow: `.github/workflows/ci.yml`.
- Triggers: pull requests targeting `main`, and pushes to `main`.
- Runner: GitHub-hosted `windows-latest`, Python 3.12.
- Steps: install `requirements.txt`, run `ruff check .`, then `pytest -q`.
- Tests use mocks; CI does not verify behavior on the owner's Windows PC. Target-machine behavior remains UNVERIFIED until the manual checks below are performed.

## Architecture and project decisions
- **The Grid** is the overall personal AI ecosystem. **MasterControl** is its central control plane and security authority; Agent Runtime components are subordinate workers, not authorities.
- All actions must follow: validate -> permission -> approval (when required) -> execute -> verify -> log. LLMs and Agents do not grant permissions or approve actions.
- **Skills** are local Python extensions running in the same process as MasterControl. They are not an OS sandbox; capability declarations are permission metadata, not isolation. Skills remain opt-in.
- **AI Provider Layer, Budget Manager, and AI Debate** are planned MasterControl capabilities for Phase 5. Candidate free providers include Groq, Gemini, and GitHub Models; actual support and quota behavior must be verified when implemented. Local LLM is not the default; any local option remains optional and off during gaming.
- **OpenClaw** is a conditional Agent Runtime candidate for Phase 6, not the security authority and not a required dependency. Integration is blocked until the OpenClaw Decision Gate in the master plan is passed. Read-only evaluation does not authorize action tools.
- **Discord** is a communication and approval channel planned separately in Phase 7; it is not the Agent Runtime. Existing notification checks in Phase 1 do not mean the planned command/approval bot is complete.
- BIOS-based Auto-Boot was dropped. Morning SITREP belongs to the planned Proactive Intelligence work in Phase 8; it is not recorded here as a completed feature.
- Gaming Lock, Gaming Mode 2.0, and Auto-Wingman were consolidated into the existing Mode Engine. Do not add any control of fans/MSI Center or interaction with game/anti-cheat processes.
- The Skill Framework (Phase 4) allows reviewed, explicitly enabled extensions without rewriting the core.

## Phase status

| Phase | Scope | Status |
|---|---|---|
| 1 | Foundation: database, permissions, approval, commands, notifications, dashboard | Done in mocks; UNVERIFIED on the owner's Windows machine (including real Windows toast and existing Discord notification path) |
| 2 | Telemetry, Process Monitor, Gaming/Focus Mode Engine, mode sessions (schema v2) | Done in mocks; UNVERIFIED on the owner's Windows machine |
| 3 | Alert Engine: bedtime/deadline, VIP, snooze, vacation, scheduler, Notification Center (schema v3; task due_at and sender fields) | Done in mocks (21 tests); UNVERIFIED on the owner's Windows machine |
| 4 | Skill Framework: opt-in loader, manifest validation, capability risk floors, command routing, approval dispatch, quick_note, task_list, brain_dump, daily_report | Code complete and CI verified; Windows verification pending (see Issue #11 and checklist below) |
| 4.5 | Reliability & Security | Planned next priority; no completion or Windows verification is claimed |
| 5 | AI Provider & Intelligence: Provider Layer, Budget Manager, L0-L3 routing, AI Debate | Planned |
| 6 | Agent Manager & Runtime Gate: Agent/Sub-Agent lifecycle and conditional OpenClaw Decision Gate | Planned |
| 7 | Discord Integration: owner-verified commands, reports, and approval channel | Planned |
| 8 | Proactive Intelligence: Task Engine, Morning SITREP, event/rule-based monitoring | Planned |
| 9 | The Grid Desktop Experience: tray, hotkey/overlay, Notification Center, privacy/provider/budget/agent controls, file intelligence | Planned |
| 10 | Ecosystem & Maintenance: versioning, compatibility, extension review, backup, recovery, and maintenance | Planned |

The next development priority is Phase 4.5, in the order described by `docs/THE_GRID_MASTER_PLAN.md`. Phase 5 and later work must not be represented as implemented until their code and verification evidence exist.

## Pending real-machine checks (do when back at the PC)

### Phase 1
- [ ] Run `pytest -q`; confirm the dashboard opens.
- [ ] Confirm notifications arrive as a Windows toast and through the existing Discord notification path.
- [ ] Confirm any health endpoint binds to `127.0.0.1` only, or is removed.
- [ ] Confirm `.env` is gitignored and no webhook URL is present in the repository.

### Phase 2
- [ ] Compare dashboard CPU/RAM/VRAM/GPU temperature values with Task Manager and `nvidia-smi`.
- [ ] Confirm "gaming mode" initially performs dry-run only and leaves Notepad open.
- [ ] After approval, confirm Notepad closes, is verified gone, and is logged in `action_log` and `mode_sessions`.
- [ ] Confirm "restore mode" relaunches Notepad; entries without `restore_path` must be reported honestly.
- [ ] Confirm adding Discord.exe or an anti-cheat process to the closeable list is rejected.

### Phase 3
- [ ] Verify migration v1->v2->v3 on an existing database with data.
- [ ] Set bedtime two minutes ahead and confirm toast + Discord notification.
- [ ] Set a task due in one hour and confirm Warning behavior repeats until acknowledged.
- [ ] Confirm snooze works and vacation mode silences bedtime reminders.
- [ ] Confirm only one scheduler instance runs and idle CPU use is near zero.

### Phase 4
- [ ] Run `pytest -q` and `ruff check .` on Python 3.11+ with the existing dependencies.
- [ ] Verify schema migration v3->v4 preserves existing tasks, approvals, and action_log rows.
- [ ] Confirm no Skill loads unless listed in `config/skills.toml`; malformed manifests are skipped.
- [ ] Review each Skill source before enabling; confirm capability floors are raised and logged.
- [ ] Confirm MEDIUM+ Skill actions remain pending until explicit approval and are logged after verification.
- [ ] Confirm quick_note rejects traversal and writes only within `data/notes/`.
- [ ] Confirm brain_dump captures append-only timestamped notes only within `data/brain_dump/` and rejects symlink/junction/reparse escapes.
- [ ] Confirm brain_dump list/search behavior, input limits, empty-search rejection, and fail-closed action-log behavior.
- [ ] Confirm daily_report reads tasks, date-matched brain_dump notes, and action_log without modifying source data; missing/empty sources show no data.
- [ ] Confirm daily_report date validation, one-report-per-date overwrite behavior, path/reparse protection, and fail-closed action-log behavior.
- [ ] Verify the dashboard lists installed/enabled Skills, capability/risk summaries, last errors, and enable/disable controls.
- [ ] Test enable/disable persistence across dashboard restart.
- [ ] Confirm Python Skill code is treated as trusted local code, not an OS sandbox.

## Open questions / prerequisites
- Before any OpenClaw integration decision: inspect the actual installed version, configuration, enabled tools/plugins/hooks, and all routes that could bypass MasterControl. No integration is authorized by this status document.
- Confirm the Python version on the target machine (the project baseline is Python 3.11+).
