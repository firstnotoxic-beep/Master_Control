# MasterControl

**MasterControl** คือระบบควบคุมและผู้ช่วยส่วนตัวบน Windows 11 และเป็นศูนย์ควบคุมหลักของ **The Grid** ออกแบบให้ Core เป็นผู้กำกับการทำงาน ไม่ปล่อยให้ AI หรือ Agent สั่งเครื่องได้โดยตรง

## How it works

- **AI proposes:** เมื่อ AI Provider ถูกพัฒนาใน Phase 5 แล้ว AI จะส่ง structured proposal ไม่ใช่คำสั่งระบบอิสระ
- **Core governs:** Core ตรวจ schema และ permission, ขอ approval เมื่อจำเป็น, ส่งให้ executor ทำงาน, ตรวจผลจริง และบันทึก action log
- **Skills extend locally:** Skills เป็น Python code ใน process เดียวกับ MasterControl ไม่ใช่ OS sandbox; capability tags เป็น metadata ไม่ใช่การแยกสิทธิ์ของระบบปฏิบัติการ
- **Agent Runtime is conditional:** OpenClaw เป็นเพียงตัวเลือก Runtime ที่ต้องผ่าน Security Decision Gate; Discord เป็นช่องทางสื่อสารและ approval แยกต่างหาก

ลำดับบังคับคือ **validate → permission → approval (when required) → execute → verify → log** โดย MEDIUM และ HIGH ต้องมี approval; CRITICAL ถูกปฏิเสธ

## Current status

- **Phases 1–3:** เสร็จใน mock tests; ยัง **UNVERIFIED on Windows เครื่องเจ้าของ**
- **Phase 4 — Skill Framework:** code complete และ CI verified; Windows verification ยัง pending ตาม [Issue #11](https://github.com/firstnotoxic-beep/Master_Control/issues/11)
- **Phases 4.5–10:** ยังเป็นแผนหรือกำลังรอ PR ตามสถานะใน [docs/STATUS.md](docs/STATUS.md)
- **CI:** GitHub-hosted Windows runner, Python 3.12, Ruff และ pytest; tests ใช้ mocks เท่านั้น ไม่ใช่การทดสอบบนเครื่อง Windows ของเจ้าของ
- **Skills:** `quick_note`, `task_list`, `brain_dump`, `daily_report`; opt-in และปิดไว้โดยค่าเริ่มต้น

เริ่มใช้งานด้วย [Windows Quickstart](docs/QUICKSTART.md) (เอกสารนี้เพิ่มใน PR แยก) และตรวจสถานะจริงจาก [STATUS](docs/STATUS.md) ก่อนใช้งาน

## Roadmap

| Phase | Scope | Status |
|---|---|---|
| 1 | Foundation: SQLite, permissions, approvals, keyword commands, notifications, Streamlit dashboard | Done — mock verified; Windows verification pending |
| 2 | Telemetry, top-process listing, Gaming/Focus Mode Engine, allowlisted process planning and restore sessions | Done — mock verified; Windows verification pending |
| 3 | Alert Engine: bedtime/deadline rules, VIP rule hook, snooze/acknowledge, vacation/quiet hours, scheduler, Notification Center history | Done — mock verified; Windows verification pending |
| 4 | Skill Framework: opt-in loader, manifest validation, capability risk floors, command routing, approval dispatch, four example Skills | Code complete — CI verified; Windows verification pending |
| 4.5 | Reliability & Security: diagnostics, action preview, audit timeline, configuration backup/recovery, failure handling | Planned |
| 5 | AI Provider & Intelligence: provider interface, Budget Manager, L0–L3 routing, AI Debate, privacy/redaction | Planned |
| 6 | Agent Manager & Runtime Gate: scoped Agents/Sub-Agents; conditional OpenClaw integration after Decision Gate | Planned |
| 7 | Discord Integration: owner-verified commands, reports, and approval channel (not Agent Runtime) | Planned |
| 8 | Proactive Intelligence: Task Engine, Morning SITREP, event/rule-based monitoring | Planned |
| 9 | The Grid Desktop Experience: tray, hotkey/overlay, privacy controls, file intelligence | Planned |
| 10 | Ecosystem & Maintenance: versioning, compatibility, extension review, backup and recovery | Planned |

### Milestones

| Milestone | Phases | Goal |
|---|---|---|
| A — Secure Foundation | 4 + 4.5 | Reliable, observable Skill execution and recovery |
| B — Intelligent Assistant | 5 + 6 | Controlled AI proposals and scoped Agent runtime |
| C — Connected & Proactive | 7 + 8 | Discord communication and proactive productivity |
| D — Complete Ecosystem | 9 + 10 | Desktop experience and maintainable extensions |

### Definition of done

- `ruff check .` and `pytest -q` pass on the GitHub Windows runner.
- Relevant success and failure paths have automated tests using mocks; tests make no live network calls or real process changes.
- Permission floors, MEDIUM+ approval, fail-closed logging, and opt-in defaults are not weakened.
- `docs/STATUS.md` records the real implementation state and separates CI/mock verification from owner-device verification.
- New functionality is reported as **CI verified, Windows verification pending** until it is tested on the actual target PC.

## Project documents

- [Windows Quickstart](docs/QUICKSTART.md)
- [Implementation status and real-PC checklist](docs/STATUS.md)
- [The Grid unified master plan](docs/THE_GRID_MASTER_PLAN.md)
- [Skill Framework guide](docs/SKILLS.md)
- [Skill security notes](docs/SECURITY.md)
- [Issues and verification work](https://github.com/firstnotoxic-beep/Master_Control/issues)
