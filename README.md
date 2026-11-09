# MasterControl

**MasterControl** คือระบบควบคุมและผู้ช่วยส่วนตัวบน Windows 11 และเป็นศูนย์ควบคุมหลักของ **The Grid** ออกแบบให้ Core เป็นผู้กำกับการทำงาน ไม่ปล่อยให้ AI หรือ Agent สั่งเครื่องได้โดยตรง

## How it works

- **AI proposes:** เมื่อ live AI Provider พร้อมใช้งาน AI จะส่ง structured proposal ไม่ใช่คำสั่งระบบอิสระ
- **Core governs:** Core ตรวจ schema และ permission, ขอ approval เมื่อจำเป็น, ส่งให้ executor ทำงาน, ตรวจผลจริง และบันทึก action log
- **Skills extend locally:** Skills เป็น Python code ใน process เดียวกับ MasterControl ไม่ใช่ OS sandbox; capability tags เป็น metadata ไม่ใช่การแยกสิทธิ์ของระบบปฏิบัติการ
- **Agent Runtime is conditional:** OpenClaw เป็นเพียงตัวเลือก Runtime ที่ต้องผ่าน Security Decision Gate; Discord เป็นช่องทางสื่อสารและ approval แยกต่างหาก

ลำดับบังคับคือ **validate → permission → approval (when required) → execute → verify → log** โดย MEDIUM และ HIGH ต้องมี approval; CRITICAL ถูกปฏิเสธ

## Current status

- **Phases 1–3:** มี mock/CI evidence และผ่านการตรวจบน Windows บางส่วนแล้ว; รายการที่ยังไม่ผ่านให้ยึด [STATUS](docs/STATUS.md)
- **Phase 4 — Skill Framework:** code complete และ CI verified; ผ่านการตรวจบน Windows บางส่วน แต่ enable/run/disable และ security paths ยัง pending
- **Phase 4.5 — Reliability & Security:** PR #31/#32 merged และ CI verified; manual security/recovery checks บนเครื่องเจ้าของยัง pending
- **Phase 5 — AI groundwork:** PR #33 merged; มี Provider protocol, MockProvider, disabled stubs, ActionProposal และ privacy redaction แต่ยังไม่มี live API clients, Budget Manager หรือ AI Debate
- **Phases 4.6–4.7 และ 6–10:** เป็นงานตาม Roadmap; ยังไม่ถือว่า implement แล้ว
- **CI:** GitHub-hosted Windows runner, Python 3.12; รัน isolated demo, Ruff และ pytest โดย tests ใช้ mocks ไม่ใช่การทดสอบบนเครื่อง Windows ของเจ้าของ
- **Skills:** quick_note, task_list, brain_dump และ daily_report; opt-in และปิดไว้โดยค่าเริ่มต้น

เริ่มใช้งานด้วย [Windows Quickstart](docs/QUICKSTART.md) และตรวจสถานะจริงจาก [STATUS](docs/STATUS.md) ก่อนใช้งาน

## Roadmap

ใช้ [The Grid — Unified Hybrid Architecture & Roadmap](docs/THE_GRID_MASTER_PLAN.md) เป็น Roadmap หลักเพียงฉบับเดียว เอกสารนี้กำหนดสถาปัตยกรรม Hybrid Skills, AI/Agent boundaries, Security Core และลำดับ Milestone/Phase อย่างละเอียด

ลำดับพัฒนาถัดไปคือปิด Windows security checks ของ Phase 4.5 → Phase 4.6 Hybrid Skill Engine → Phase 4.7 Skill Manager/Local Library → ทำ Phase 5 ให้สมบูรณ์ (live Provider, Budget, routing, AI Debate) → Agent orchestration และส่วนต่อยอด The Grid

สถานะ implementation และผลการ verify ให้ยึด [docs/STATUS.md](docs/STATUS.md) เสมอ README และ Roadmap นี้ไม่ใช้แทนหลักฐานจาก code, CI หรือการทดสอบบนเครื่องเจ้าของ

### Definition of done

- `ruff check .` and `pytest -q` pass on the GitHub Windows runner.
- Relevant success and failure paths have automated tests using mocks; tests make no live network calls or real process changes.
- Permission floors, MEDIUM+ approval, fail-closed logging, and opt-in defaults are not weakened.
- `docs/STATUS.md` records the real implementation state and separates CI/mock verification from owner-device verification.
- New functionality is reported as **CI verified, Windows verification pending** until it is tested on the actual target PC.

## Project documents

- [Windows Quickstart](docs/QUICKSTART.md)
- [Implementation status and real-PC checklist](docs/STATUS.md)
- [The Grid unified hybrid architecture and roadmap](docs/THE_GRID_MASTER_PLAN.md)
- [Skill Framework guide](docs/SKILLS.md)
- [Skill security notes](docs/SECURITY.md)
- [Issues and verification work](https://github.com/firstnotoxic-beep/Master_Control/issues)
