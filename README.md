# MasterControl

MasterControl คือระบบควบคุมและผู้ช่วยส่วนตัวสำหรับ **Windows 11** ที่ออกแบบให้ Core เป็นผู้ควบคุมการกระทำของระบบ ไม่ใช่ให้ AI สั่งเครื่องโดยตรง

## What is MasterControl?

- **AI proposes:** AI Provider (Phase 5, planned) จะเสนอ action ในรูปแบบข้อมูลที่มีโครงสร้างและตรวจสอบด้วย Pydantic เท่านั้น
- **Core controls:** Core ตรวจ schema และ permission, ขอ approval เมื่อจำเป็น, ส่งให้ executor ทำงาน, ตรวจผลจริง และบันทึก action log
- **Skills:** Skill เป็น Python code ที่ทำงานใน process เดียวกับ MasterControl ไม่ใช่ OS sandbox จึงต้องตรวจ source และเปิดใช้เฉพาะ Skill ที่เชื่อถือได้

ลำดับความปลอดภัยคือ **validate → permission → approval (when required) → execute → verify → log** โดย action ระดับ MEDIUM ขึ้นไปต้องได้รับอนุมัติ และ CRITICAL ไม่สามารถทำงานได้

## Current status

- **Phase 4 — Skill Framework:** code complete; GitHub Actions CI verified บน hosted Windows runner โดยใช้ mock tests เท่านั้น
- **Windows verification:** ยัง pending ตาม [Issue #11](https://github.com/firstnotoxic-beep/Master_Control/issues/11) การผ่าน CI ไม่ได้ยืนยันการทำงานบนเครื่อง Windows 11 ของเจ้าของ
- **Installed Skills:** `quick_note`, `task_list`, `brain_dump`, `daily_report` — ทุกตัวเป็น opt-in และปิดไว้โดยค่าเริ่มต้น ไม่มี Skill โหลดจนกว่าจะเปิดใน `config/skills.toml`

## Getting started

Quickstart coming soon. ดู dependencies และสถานะการพัฒนาจากไฟล์ที่ลิงก์ไว้ด้านล่างก่อนใช้งาน

## Roadmap

| Phase | Name | Key items | Status |
|---|---|---|---|
| 1 | Foundation | SQLite, permissions, approval, keyword commands, Windows Toast/Discord notifications, Streamlit dashboard | Done — mock verified; Windows checks pending |
| 2 | System Intelligence | Read-only telemetry, top-process listing, Gaming/Focus Mode Engine, allowlisted process planning, approval-gated actions and restore sessions | Done — mock verified; Windows checks pending |
| 3 | Alert Engine | Bedtime/deadline alerts, VIP rule hook, snooze/acknowledge, vacation/quiet hours, polling scheduler, Notification Center history | Done — mock verified; Windows checks pending |
| 4 | Skill Framework | Opt-in loader, manifest validation, capability risk floors, command routing, approval dispatch, four example Skills | Code complete — Windows pending |
| 4.5 | Reliability & Security | Self-diagnostic, action preview, audit timeline, config/error recovery, failure tests | Planned |
| 5 | AI Provider Layer | Groq primary; Gemini/GitHub Models fallback; Pydantic action proposals; no private data sent to cloud without consent | Planned |
| 6 | Discord Integration | Status/task commands, approve/cancel buttons, owner ID check | Planned |
| 7 | Personal Productivity | Task engine, morning SITREP, voice via faster-whisper, knowledge search | Planned |
| 8 | Gaming Assistant | Game profiles and session analytics; no game/anti-cheat interaction, process killing, or fan control | Planned |
| 9 | Desktop Experience | Command palette, quick actions, system tray, privacy center | Planned |
| 10 | Ecosystem | Local Skill marketplace, versioning, compatibility checks, config export/import | Planned |

### Milestones

| Milestone | Phases | Goal |
|---|---|---|
| A — Secure Foundation | 4 + 4.5 | Trusted, observable Skill execution and recovery |
| B — Intelligent Assistant | 5 + 6 | AI proposals and controlled Discord interaction |
| C — Personal Intelligence | 7 + 8 | Productivity and gaming context |
| D — Complete Ecosystem | 9 + 10 | Desktop experience and extensible Skills |

### Definition of done (each phase)

- `ruff check .` and `pytest -q` pass.
- Failure-path tests cover relevant execution and recovery behavior.
- No permission or approval requirement is weakened.
- `docs/STATUS.md` is updated.
- Mock/CI verification and real Windows-device verification are reported separately; mock results are never presented as Windows-verified.

## Links

- [Project status](docs/STATUS.md)
- [Skill security notes](docs/SECURITY.md)
- [Issues and verification work](https://github.com/firstnotoxic-beep/Master_Control/issues)
