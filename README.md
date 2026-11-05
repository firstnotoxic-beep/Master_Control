# MasterControl

**MasterControl** คือระบบควบคุมและผู้ช่วยส่วนตัวบน Windows 11 และเป็นศูนย์ควบคุมหลักของ **The Grid** เป้าหมายคือให้ Core เป็นผู้กำกับการทำงานของระบบและ Agent แทนการปล่อยให้ AI หรือ Agent สั่งเครื่องได้โดยตรง

## The Grid and MasterControl

- **The Grid** คือระบบนิเวศทั้งหมด รวม MasterControl, Agent Runtime, เครื่องมือ และเครื่อง Windows ที่ได้รับอนุญาต
- **MasterControl** คือ Control Plane และ Security Authority: รับคำสั่ง เลือกวิธีทำงาน กำหนดขอบเขต ตรวจสิทธิ์ และตรวจผลลัพธ์
- **Agent Runtime** เป็นชั้นปฏิบัติงานที่อาจใช้ OpenClaw หรือทางเลือกอื่นได้ แต่ต้องผ่านการประเมินและ Decision Gate ก่อน ไม่ใช่ผู้มีอำนาจด้านความปลอดภัย
- **Discord** เป็นช่องทางสื่อสาร รายงาน และ approval ที่แยกจาก Agent Runtime

## Security model

ทุก action ต้องผ่านลำดับนี้:

`validate → permission → approval (when required) → execute → verify → log`

LLM และ Agent เสนอได้เฉพาะ structured data ที่ตรวจสอบได้ ไม่สามารถอนุมัติ action ให้ตัวเองหรือข้าม Security Core ได้ โดย MEDIUM+ ต้องได้รับ approval และ CRITICAL ถูกปฏิเสธ

**Skill security:** Skills เป็น Python code ที่รันใน process เดียวกับ MasterControl ไม่ใช่ OS sandbox และ capability declarations ไม่ใช่การแยกสิทธิ์ระดับระบบปฏิบัติการ ต้องตรวจ source ก่อนเปิดใช้ และเปิดใช้แบบ opt-in เท่านั้น

## Current repository status

- **Phases 1–3:** ทำเสร็จใน mock tests; ยัง UNVERIFIED บน Windows เครื่องเจ้าของ
- **Phase 4 — Skill Framework:** code complete และ CI verified; การตรวจบน Windows เครื่องเจ้าของยัง pending
- **Phase 4.5:** เป็นลำดับงานถัดไปตามแผน — Reliability & Security
- **Phases 5–10:** เป็นแผน ยังไม่ถือว่า implemented

CI ใช้ GitHub-hosted Windows runner, Python 3.12, Ruff และ pytest โดย tests ใช้ mocks เท่านั้น การผ่าน CI ไม่ได้ยืนยันการทำงานบนเครื่อง Windows 11 จริง ดูรายละเอียดและ checklist ได้ที่ [docs/STATUS.md](docs/STATUS.md)

## Skills

ตัวอย่าง Skills ใน repository:

- `quick_note`
- `task_list`
- `brain_dump`
- `daily_report`

ทั้งหมดเป็น opt-in และปิดไว้โดยค่าเริ่มต้น จะโหลดได้เมื่อเจ้าของเปิดใช้ใน `config/skills.toml` เท่านั้น อ่าน [docs/SKILLS.md](docs/SKILLS.md) และ [docs/SECURITY.md](docs/SECURITY.md) ก่อนเปิดใช้ Skill ใด ๆ

## Unified roadmap

| Phase | Name | Status |
|---|---|---|
| 1–3 | Foundation, Telemetry/Mode Engine, Alert Engine | Done in mocks; Windows verification pending |
| 4 | Skill Framework | Code complete; CI verified; Windows verification pending |
| 4.5 | Reliability & Security | Planned next |
| 5 | AI Provider & Intelligence (Provider, Budget Manager, L0–L3, AI Debate) | Planned |
| 6 | Agent Manager & conditional OpenClaw Runtime Gate | Planned |
| 7 | Discord Integration | Planned |
| 8 | Proactive Intelligence (Task Engine, Morning SITREP, monitoring) | Planned |
| 9 | The Grid Desktop Experience (tray, hotkey/overlay, file intelligence) | Planned |
| 10 | Ecosystem & Maintenance | Planned |

รายละเอียดเป้าหมาย, exit criteria, Budget Manager, AI Debate และ OpenClaw Decision Gate อยู่ใน [docs/THE_GRID_MASTER_PLAN.md](docs/THE_GRID_MASTER_PLAN.md) ส่วนสถานะ implementation ที่มีผลจริงให้ยึด [docs/STATUS.md](docs/STATUS.md) เสมอ

## Development and verification

Project baseline: Python 3.11+ (CI currently uses Python 3.12).

```powershell
python -m pip install -r requirements.txt
ruff check .
pytest -q
```

These commands install the repository dependencies and run the same lint/test checks used by CI. They do not replace the pending manual checks on the owner's Windows machine.

## Project documents

- [Project instructions](AGENTS.md)
- [Implementation status and Windows checklist](docs/STATUS.md)
- [The Grid unified master plan](docs/THE_GRID_MASTER_PLAN.md)
- [Skill Framework guide](docs/SKILLS.md)
- [Skill security notes](docs/SECURITY.md)
- [Open issues and verification work](https://github.com/firstnotoxic-beep/Master_Control/issues)
