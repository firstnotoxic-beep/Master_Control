# MasterControl - STATUS (single source of truth)

> This file records the repository's implementation and verification status. The roadmap describes intended work; it does not make planned features complete.

## Verification policy
The owner can now run manual checks on the target Windows 11 machine. This does not make every feature VERIFIED: only checks explicitly listed in the Windows verification log below are owner-PC verified. Mock/CI evidence remains separate.

## Owner-PC Windows verification log — 2026-11-07
Environment: Windows 11 PowerShell, Python 3.12.10, project `.venv`.

Confirmed on the owner's PC:
- `python -m pip install -r requirements.txt` completed successfully.
- `ruff check .` passed; output: `All checks passed!`.
- `pytest -q` passed: 81 passed, 4 skipped.
- `python -c "from core.db import init_db; init_db()"` completed; subsequent diagnostics verified a reachable SQLite database, schema v4, and a readable/writable `action_log` probe.
- `python -m core.diagnostics check` returned `WARN` (not FAIL). Database, schema_version (4), the transactional `action_log` write probe, `data/`, and all four Skill manifests passed. `data/notes/`, `data/tasks/`, `data/brain_dump/`, `data/reports/`, and `data/logs/` were WARN because the directories do not exist yet; diagnostics intentionally did not create them. Output reported `read_only=true` and `persistent_changes=false`.
- The Streamlit dashboard launched using `streamlit run app/dashboard.py` and opened at `http://localhost:8501`.
- Dashboard command smoke checks: `help` returned supported commands; `status` returned `ระบบพร้อมทำงาน`; `skills` returned `Skill registry loaded`. The owner confirmed the dashboard lists all four built-in Skills as installed and disabled by default.
- Core task smoke check: `list tasks` returned 0 initially; `add task ทดสอบระบบ MasterControl` created Task ID 1; the dashboard displayed it as `pending`.
- The `task_list` Skill enable review displayed its action capability/risk metadata. Enable was not confirmed and Skill actions were not run. Attempting `run task_list.done` while disabled was rejected with `skill is not enabled or did not load: task_list`; Task ID 1 remains pending.

Not verified by this session: Windows toast/Discord notification delivery, telemetry accuracy against Task Manager/NVIDIA tools, process close/restore, alert scheduler and reminders, gaming/focus modes, existing-database v3→v4 data preservation, full Skill enable/run/disable behavior, file-path/reparse protections, MEDIUM+ approval behavior, audit filters, config backup/restore, and failure recovery. Do not mark the relevant phases fully VERIFIED from this partial pass.

## CI
- Workflow: `.github/workflows/ci.yml`.
- Triggers: pull requests targeting `main`, and pushes to `main`.
- Runner: GitHub-hosted `windows-latest`, Python 3.12.
- Steps: install `requirements.txt`, run the isolated demo (`python -m scripts.demo`), then `ruff check .` and `pytest -q`.
- Tests use mocks; CI does not verify behavior on the owner's Windows PC. Target-machine behavior remains UNVERIFIED until the manual checks below are performed.

## Architecture and project decisions
- **The Grid** is the overall personal AI ecosystem. **MasterControl** is its central control plane and security authority; Agent Runtime components are subordinate workers, not authorities.
- All actions must follow: validate -> permission -> approval (when required) -> execute -> verify -> log. LLMs and Agents do not grant permissions or approve actions.
- **Skills (current implementation):** Skills are local Python extensions running in the same process as MasterControl. They are not an OS sandbox; capability declarations are permission metadata, not isolation. Skills remain opt-in. The Hybrid model (Markdown-only Instruction Skills and Markdown + TOML + Python Action Skills) is planned for Phase 4.6; it is not implemented yet. SKILL.md must never grant permissions or bypass the existing Security Core.
- **Phase 5 AI groundwork (PR #33 merged; CI verified):** the repository now has an AI Provider protocol, deterministic MockProvider, configuration-only stubs for Groq/Gemini/GitHub Models, ProviderRouter, strict Pydantic ActionProposal validation, Core-owned Skill proposal submission, and default private-field redaction. The provider stubs do not make API/network requests. Live provider clients, Budget Manager, completed L0–L3 routing, and AI Debate remain unimplemented. Provider terms, support, and quotas must be checked when implementation begins. Local LLM is not the default; any local option remains optional and off during gaming.
- **OpenClaw** is a conditional Agent Runtime candidate for Phase 6, not the security authority and not a required dependency. Integration is blocked until the OpenClaw Decision Gate in the master plan is passed. Read-only evaluation does not authorize action tools.
- **Discord** is a communication and approval channel planned separately in Phase 7; it is not the Agent Runtime. Existing notification checks in Phase 1 do not mean the planned command/approval bot is complete.
- BIOS-based Auto-Boot was dropped. Morning SITREP belongs to the planned Proactive Intelligence work in Phase 8; it is not recorded here as a completed feature.
- Gaming Lock, Gaming Mode 2.0, and Auto-Wingman were consolidated into the existing Mode Engine. Do not add any control of fans/MSI Center or interaction with game/anti-cheat processes.
- The Skill Framework (Phase 4) allows reviewed, explicitly enabled extensions without rewriting the core.

## Phase status

| Phase | Scope | Status |
|---|---|---|
| 1 | Foundation: database, permissions, approval, commands, notifications, dashboard | Partially verified on owner Windows PC (2026-11-07): Python environment, DB v4, dashboard launch, help/status/skills, and core task list/add; Windows toast and Discord delivery remain UNVERIFIED and other checks remain pending |
| 2 | Telemetry, Process Monitor, Gaming/Focus Mode Engine, mode sessions (schema v2) | Done in mocks; UNVERIFIED on the owner's Windows machine |
| 3 | Alert Engine: bedtime/deadline, VIP, snooze, vacation, scheduler, Notification Center (schema v3; task due_at and sender fields) | Partially verified on owner Windows PC (2026-11-07): basic core task listing/creation only; reminders, alert delivery, scheduler, snooze/ack, and vacation behavior remain UNVERIFIED |
| 4 | Skill Framework: opt-in loader, manifest validation, capability risk floors, command routing, approval dispatch, quick_note, task_list, brain_dump, daily_report | Code complete and CI verified; partially verified on owner Windows PC (2026-11-07): Ruff/pytest, registry load, and dashboard Skill visibility; full enable/run/disable, migration retention, filesystem protections, and approval/failure paths remain unverified |
| 4.5 | Reliability & Security | Implementation from PR #31/#32 is merged to main and CI verified; partially verified on owner Windows PC (2026-11-07): diagnostics only; action preview, audit, config recovery, and failure-path checks remain pending |
| 5 | AI Provider & Intelligence: Provider Layer, Budget Manager, L0-L3 routing, AI Debate | Foundation merged in PR #33 and CI verified; live Provider clients, Budget Manager, full routing and AI Debate remain planned |
| 6 | Agent Manager & Runtime Gate: Agent/Sub-Agent lifecycle and conditional OpenClaw Decision Gate | Planned |
| 7 | Discord Integration: owner-verified commands, reports, and approval channel | Planned |
| 8 | Proactive Intelligence: Task Engine, Morning SITREP, event/rule-based monitoring | Planned |
| 9 | The Grid Desktop Experience: tray, hotkey/overlay, Notification Center, privacy/provider/budget/agent controls, file intelligence | Planned |
| 10 | Ecosystem & Maintenance: versioning, compatibility, extension review, backup, recovery, and maintenance | Planned |

The immediate priority remains completing the pending owner-PC security/reliability checks for Phase 4.5 and the relevant Phase 1–4 checks below. After that, the next feature milestone is Phase 4.6 (Hybrid Skill Engine). Phase 5 has only the groundwork described above; live Provider clients, Budget Manager, full L0–L3 routing, and AI Debate must not be reported as implemented until their code and verification evidence exist.

## Remaining real-machine checks

### Phase 1
- [x] Run `pytest -q`; confirm the dashboard opens. On 2026-11-07: 81 passed, 4 skipped; `app/dashboard.py` launched successfully on the owner's Windows PC.
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

### Phase 4.5 (CI verified; partial Windows verification)

Implementation landed in [PR #31 — diagnostics and action preview](https://github.com/firstnotoxic-beep/Master_Control/pull/31) and [PR #32 — audit timeline and config recovery](https://github.com/firstnotoxic-beep/Master_Control/pull/32); both PRs are merged to main and their Windows CI runs passed. The checks below still require owner-PC verification.

- [x] Run `python -m core.diagnostics check` on 2026-11-07. Result: WARN (database, schema v4, action_log probe, data/, and four manifests PASS; five optional Skill data directories WARN because they do not exist). Output reports `read_only=true` and `persistent_changes=false`; temporary probes are removed and the action-log probe is rolled back.
- [ ] Preview an enabled Skill action; confirm capability, effective risk, target paths, and approval requirement are displayed, and that preview does not execute the Skill.
- [ ] Use the dashboard audit filters for date range, Skill, and result; confirm returned rows and the row limit are correct.
- [ ] Create a config backup, then request and approve a HIGH-risk restore; confirm the current config is backed up before replacement, rollback is available, corrupt backups are rejected, and `.env` is never included.
- [ ] Verify expired approvals cannot be approved, a Skill crash is left failed and disabled, action-log write failure blocks Skill execution, and the fallback log refuses writes beyond its size limit without truncating prior evidence.

### Phase 4
- [x] Run `pytest -q` and `ruff check .` on Python 3.12.10 with the existing dependencies on 2026-11-07: 81 passed, 4 skipped; Ruff reported all checks passed.
- [ ] Verify schema migration v3->v4 preserves existing tasks, approvals, and action_log rows.
- [ ] Confirm no Skill loads unless listed in `config/skills.toml`; malformed manifests are skipped.
- [ ] Review each Skill source before enabling; confirm capability floors are raised and logged.
- [ ] Confirm MEDIUM+ Skill actions remain pending until explicit approval and are logged after verification.
- [ ] Confirm quick_note rejects traversal and writes only within `data/notes/`.
- [ ] Confirm brain_dump captures append-only timestamped notes only within `data/brain_dump/` and rejects symlink/junction/reparse escapes.
- [ ] Confirm brain_dump list/search behavior, input limits, empty-search rejection, and fail-closed action-log behavior.
- [ ] Confirm daily_report reads tasks, date-matched brain_dump notes, and action_log without modifying source data; missing/empty sources show no data.
- [ ] Confirm daily_report date validation, one-report-per-date overwrite behavior, path/reparse protection, and fail-closed action-log behavior.
- [ ] Verify the dashboard lists capability/risk summaries, last errors, and enable/disable controls. Partial check only: the owner confirmed all four built-in Skills appear installed and disabled by default; full controls and error-state behavior remain unverified.
- [ ] Test enable/disable persistence across dashboard restart.
- [ ] Confirm Python Skill code is treated as trusted local code, not an OS sandbox.


### Phase 5 (AI Provider groundwork merged; feature work incomplete)

- [x] PR #33 merged to main: Provider protocol, deterministic MockProvider, configuration-only provider stubs, ProviderRouter, strict ActionProposal schema, Core-owned Skill proposal routing, and default private-field redaction.
- [x] PR #33 reports successful Windows CI run #61 (Ruff + pytest); tests use MockProvider and do not make live API requests.
- [ ] Implement and test a real Provider client only after checking the current API terms, free quota, privacy policy, timeout behavior, and secret handling.
- [ ] Implement Provider usage tracking and Budget Manager with per-provider limits, concurrency reservation, and hard stop.
- [ ] Complete Core-owned L0-L3 routing and bounded AI Debate; neither may approve or execute around the Security Core.
- [ ] Verify live API behavior separately from mock/CI tests. Do not put real API keys in repository files or test fixtures.

## Open questions / prerequisites
- Before any OpenClaw integration decision: inspect the actual installed version, configuration, enabled tools/plugins/hooks, and all routes that could bypass MasterControl. No integration is authorized by this status document.
- Confirm the Python version on the target machine (the project baseline is Python 3.11+).
