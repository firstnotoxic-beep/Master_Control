<!-- แผนแม่บท The Grid และการพัฒนา MasterControl -->

# THE GRID — Unified Master Plan

> **สถานะเอกสาร:** แผนเป้าหมายและข้อกำหนดที่เสนอ ไม่ใช่สถานะการทำงานที่เสร็จแล้ว  
> **Repository:** [firstnotoxic-beep/Master_Control](https://github.com/firstnotoxic-beep/Master_Control)  
> **หลักการสูงสุด:** MasterControl เป็นศูนย์ควบคุมและเจ้าของนโยบายทั้งหมด ส่วน Agent Runtime เป็นเพียงผู้ปฏิบัติงานที่ถูกจำกัดสิทธิ์

---

## 1. วิสัยทัศน์ของ The Grid

**The Grid** คือระบบนิเวศ AI ส่วนตัวบน Windows 11 ที่รวมเครื่องมือ ผู้ช่วย และ Agent หลายบทบาทไว้ภายใต้ศูนย์บัญชาการเดียว เป้าหมายคือระบบที่ช่วยเฝ้าระวัง วิเคราะห์ จัดลำดับงาน มอบหมายงาน และเสนอการดำเนินการได้อย่างต่อเนื่อง โดยไม่แย่งการควบคุมจากเจ้าของเครื่อง

### หลักการออกแบบ

1. **Centralized Control:** MasterControl เป็นผู้รับคำสั่ง ตัดสินใจเรื่อง routing และกำกับ Agent ทุกตัว
2. **Agents Execute, MasterControl Governs:** Agent ทำงานเฉพาะขอบเขต แต่ไม่มีอำนาจกำหนด Permission หรืออนุมัติ action
3. **Security First:** ทุก action ที่กระทบไฟล์หรือระบบต้องผ่าน Security Core
4. **Rule-based First:** งานที่กฎทำได้ไม่เรียก LLM
5. **Privacy by Default:** ไม่ส่งข้อมูลส่วนตัวหรือเนื้อหาไฟล์ไป Cloud โดยไม่มี consent และ policy ที่ชัดเจน
6. **Lightweight:** ขณะ idle และเล่นเกมต้องลดงานเบื้องหลังอย่างจริงจัง
7. **Small, Verifiable Milestones:** พัฒนาเป็นส่วนเล็ก ๆ พร้อม tests และแยก Mock/CI verification ออกจากการทดสอบบนเครื่องจริง

## 2. โครงสร้างระบบเป้าหมาย

```text
THE GRID — Personal AI Ecosystem
|
+-- MASTERCONTROL — Central Control Plane
|   +-- Command Router / Task Manager
|   +-- Context & Proactive Engine
|   +-- AI Provider Layer + Budget Manager
|   +-- Debate / Review Orchestrator
|   +-- Agent Manager
|   +-- Permission / Approval / Security Core
|   +-- Resource & Gaming Mode Manager
|   +-- Desktop UI / Notifications / Discord
|
+-- AGENT RUNTIME — Conditional execution layer
|   +-- Doctor
|   +-- Developer
|   +-- Document Staff
|   +-- Researcher
|   +-- Analyst
|   +-- Reviewer
|   +-- Temporary Sub-Agents
|
+-- THE GRID HOST — Windows 11
    +-- Approved files and folders
    +-- Applications and process telemetry
    +-- Hardware telemetry
    +-- Notifications and user-approved integrations
```

**MasterControl คือผู้บัญชาการ ไม่ใช่ Agent Runtime** ส่วน Runtime จะเป็น OpenClaw หรือระบบอื่นก็ได้ โดยต้องผ่าน Decision Gate ก่อนเสมอ

### ขอบเขตอำนาจ

- MasterControl เป็นผู้เลือกว่าจะใช้กฎ, LLM หรือ Agent ใด
- MasterControl เป็นผู้กำหนด task scope, tool allowlist, budget และเวลาสิ้นสุดของงาน
- Agent ส่งกลับได้เพียงผลลัพธ์หรือ structured proposal
- Agent ไม่มีสิทธิ์อนุมัติ action ให้ตัวเองหรือ Agent อื่น
- Agent ห้ามสร้างหรือเรียก Sub-Agent เองโดยพลการ การสร้าง Sub-Agent ต้องผ่าน Agent Manager ของ MasterControl
- การปิดงานต้องมีผลตรวจสอบ ไม่ใช่เชื่อคำกล่าวอ้างของ Agent

## 3. Security Core — กฎที่ทุกส่วนต้องใช้ร่วมกัน

ทุกการกระทำที่มีผลต่อไฟล์ การตั้งค่า หรือระบบต้องผ่านลำดับนี้:

```text
Agent / LLM proposes structured data
              |
              v
       Schema Validation
              |
              v
       Permission Check
              |
       +------+------+
       |             |
   Approval?       Refuse
       |
       v
  User Approval (when required)
       |
       v
 Controlled Executor
       |
       v
     Verify
       |
       v
    Audit Log
```

### กฎบังคับ

- LLM และ Agent เสนอได้เฉพาะข้อมูลแบบ structured ที่ผ่าน schema validation ไม่ใช่ส่ง shell command อิสระให้ระบบรัน
- MEDIUM และ HIGH ต้องได้รับ approval ตาม policy; CRITICAL ปฏิเสธการดำเนินการโดยระบบ
- ห้ามใช้ `shell=True`, `eval`, `exec` หรือ `os.system` กับข้อความจากผู้ใช้, LLM, Skill, Agent หรือข้อมูลภายนอก
- ใช้ allowlist และ argument list สำหรับเครื่องมือที่จำเป็น
- ห้าม Agent เข้าถึง unrestricted shell, filesystem หรือ process control
- ข้อมูลจากไฟล์ เว็บ และเอกสารเป็น **untrusted data** ไม่ใช่คำสั่งให้ทำตาม (ป้องกัน prompt injection)
- แยก Agent ที่อ่านข้อมูลภายนอกจาก Agent ที่มีสิทธิ์เขียนหรือควบคุมระบบ
- ห้ามส่ง secrets หรือข้อมูลส่วนตัวไปยัง Cloud Provider โดยไม่มี consent ที่เหมาะสม
- ห้ามแตะ game/anti-cheat processes และห้ามควบคุมพัดลม/MSI Center ตามกฎใน AGENTS.md
- หากตรวจสอบสิทธิ์หรือผลลัพธ์ไม่ได้ ให้ fail closed และรายงานว่าไม่สำเร็จ

**ข้อสำคัญ:** Python Skills ที่ทำงานใน process เดียวกับ MasterControl ไม่ใช่ OS sandbox และ capability tags ไม่ใช่การแยกสิทธิ์ระดับระบบปฏิบัติการ

## 4. สถานะฐานของ Repository

ข้อมูลสถานะปัจจุบันต้องยึด `docs/STATUS.md` เป็นหลักเสมอ ไม่ใช้เอกสารแผนนี้แทนสถานะจริง

| ส่วน | สถานะที่บันทึกไว้ |
|---|---|
| Phase 1 — Foundation | ทำแล้วใน mock tests; ยัง UNVERIFIED บน Windows เครื่องเจ้าของ |
| Phase 2 — Telemetry / Process Monitor / Mode Engine | ทำแล้วใน mocks; ยัง UNVERIFIED บน Windows เครื่องเจ้าของ |
| Phase 3 — Alert Engine | ทำแล้วใน mocks; ยัง UNVERIFIED บน Windows เครื่องเจ้าของ |
| Phase 4 — Skill Framework | Code complete และ CI verified; ยังต้องตรวจบน Windows เครื่องเจ้าของ |
| Database | Schema version 4 ตามสถานะของ Skill Framework |
| Example Skills | quick_note, task_list, brain_dump, daily_report; opt-in/off by default |
| AI Provider Layer | ยังเป็นแผน |
| Discord integration | ยังเป็นแผนตาม STATUS ปัจจุบัน |
| OpenClaw integration | ยังไม่มีหลักฐานว่าผ่าน security boundary ของ MasterControl |

CI บน GitHub-hosted Windows runner ไม่เท่ากับการทดสอบบน MSI Katana A15 ของเจ้าของ ทุกผลที่ยังไม่ได้ทดสอบบนเครื่องจริงต้องระบุว่า **UNVERIFIED on Windows** ต่อไป

## 5. Unified Roadmap

ลำดับนี้รวมแผนพัฒนา MasterControl เดิมกับ The Grid โดยให้ความเสถียรและความปลอดภัยมาก่อนการเพิ่ม Agent

| Phase | ชื่อ | เป้าหมาย |
|---|---|---|
| 1–4 | Existing Foundation | รักษาฐานระบบ, Telemetry, Alert Engine และ Skill Framework ที่มีอยู่ |
| 4.5 | Reliability & Security | ตรวจ Windows จริงเมื่อเข้าถึงเครื่องได้, ปิด failure paths และยืนยัน Security Core |
| 5 | AI Provider & Intelligence | Provider Layer, Budget Manager, L0–L2 routing และ AI Debate |
| 6 | Agent Manager & Runtime Gate | จัดการ Agent/Sub-Agent และเชื่อม OpenClaw เฉพาะเมื่อผ่าน Decision Gate |
| 7 | Discord Integration | ช่องทางรับคำสั่ง รายงาน และ approval แยกจาก Agent Runtime |
| 8 | Proactive Intelligence | Task Engine, Morning SITREP และ event/rule-based monitoring |
| 9 | The Grid Desktop Experience | Tray, hotkey, overlay, file intelligence และ adaptive resource scheduling |
| 10 | Ecosystem & Maintenance | Versioning, compatibility, extension review, backup และ recovery |

### ลำดับความสำคัญในการทำงาน

1. ทำ Phase 4.5 ให้เป็นงานถัดไป ไม่เริ่ม multi-agent integration ก่อนยืนยันความน่าเชื่อถือของ Core
2. Phase 5 เป็นแกน AI ของ MasterControl และต้องทำงานได้โดยไม่พึ่ง OpenClaw
3. ตรวจ OpenClaw แบบ read-only เพื่อเก็บข้อมูลประกอบได้ แต่ห้ามถือว่าเป็นการอนุมัติ integration
4. Phase 6 เปิดได้ต่อเมื่อผ่าน OpenClaw Decision Gate; หากไม่ผ่านให้ใช้ MasterControl runtime แบบเล็กและจำกัดขอบเขตต่อไป
5. Discord เป็น communication/approval channel ไม่ใช่ตัวแทน Agent Runtime และไม่ควรผูกเป็นส่วนเดียวกับ OpenClaw

---

## 6. Phase 4.5 — Reliability & Security

### ขอบเขต

- ตรวจและทดสอบ failure paths ของ action lifecycle
- ตรวจ rollback, audit log และการจัดการ config ที่ผิดรูปแบบ
- ตรวจ permission/approval ให้ fail closed เมื่อข้อมูลไม่ครบหรือไม่ตรงกับ manifest
- ตรวจ path traversal, symlink/junction/reparse point ตามข้อจำกัดที่ระบุใน SECURITY.md
- ตรวจการทำงานของ Skill Framework และ dashboard โดยไม่ลดระดับสิทธิ์
- เมื่อกลับไปใช้เครื่องจริง ให้ทำ manual verification ของ Phase 1–4 ตาม checklist ใน STATUS.md

### Exit Criteria

- Action ที่ไม่ผ่าน validation, permission หรือ approval ต้องไม่ถูก execute
- ความล้มเหลวระหว่าง enable/run ต้องไม่ทิ้งสถานะครึ่งสำเร็จโดยไม่มี log
- มี tests สำหรับ failure paths ที่เกี่ยวข้อง
- Ruff และ pytest ผ่านใน CI
- เอกสารระบุชัดเจนว่าสิ่งใดยัง UNVERIFIED บน Windows
- ไม่มีการอ้างว่า Python Skills เป็น sandbox

---

## 7. Phase 5 — AI Provider & Intelligence MVP

Phase 5 เป็นความสามารถของ MasterControl เอง ไม่ขึ้นกับ OpenClaw ต้องเล็กพอให้ผู้พัฒนาคนเดียวดูแลได้ และเริ่มจาก Free API ที่มี quota จำกัด

### 7.1 Provider Layer

ทำ interface กลางเพื่อให้ MasterControl เรียก Provider ได้โดยไม่ผูกกับ API รายใดรายหนึ่ง

ขอบเขต MVP:

- รองรับ Provider ตามลำดับที่ตั้งค่าไว้ เช่น Groq, Gemini และ GitHub Models
- จัดการ API keys ผ่าน `.env`/secret store ที่เหมาะสมเท่านั้น
- มี timeout, error handling, response validation และ usage logging
- ส่งเฉพาะ prompt/context ที่จำเป็นและได้รับอนุญาต
- Provider ที่ไม่พร้อมใช้งานต้องไม่ทำให้ L0 หรือระบบแจ้งเตือนหยุดทำงาน
- ห้าม log API key, token หรือข้อมูลลับ

### 7.2 Budget Manager — MVP

เนื่องจากเป้าหมายคือ Free API ให้จัดการ **quota** ไม่ใช่ระบบเครดิต/ค่าใช้จ่ายที่ซับซ้อน

**ข้อมูลที่ต้องนับ**

- Request count ต่อ Provider ต่อวัน
- Token usage ต่อ Provider ต่อวัน แยก input/output เท่าที่ Provider รายงานได้
- ระบุแหล่งที่มาของ usage ว่าเป็นค่าจริงจาก Provider หรือค่าประมาณ
- นับการใช้งานของทุก Agent และ Sub-Agent รวมเป็น budget กลาง ห้ามแยกแล้วใช้เกิน quota รวม

**การจำกัดและสำรอง quota**

- ตั้ง daily budget แยกต่อ Provider ได้
- ค่าเริ่มต้นที่เสนอ: อนุญาตให้ใช้ไม่เกิน 80% ของ quota ที่ผู้ใช้กำหนด/ทราบ เพื่อกันส่วนสำรองไว้ 20%
- ตั้ง hard stop เมื่อถึง daily budget; ห้ามยิง request ต่อเพียงเพราะ fallback หรือ Agent ตัวอื่นร้องขอ
- จอง request/token budget ก่อนเริ่มเรียก Provider เพื่อป้องกันงานพร้อมกันหลายตัวใช้เกิน limit
- หลังจบ request ให้ settle usage จริงหรือค่าประมาณ และคืน reservation ส่วนที่ไม่ได้ใช้ตามความเหมาะสม
- การจองและตัดยอดต้อง atomic เพื่อป้องกัน concurrent requests เกินงบ
- จำกัดต่อ task ด้วยค่าตั้งต้นที่ปรับได้ เช่น max input tokens, max output tokens, max requests per task และ max total tokens per task

**Fallback**

- ใช้ Provider priority list ที่ผู้ใช้กำหนด เช่น Gemini → Groq → GitHub Models
- เมื่อ Provider หลักถึง threshold หรือใช้ไม่ได้ ให้ตรวจ Provider ถัดไปตามลำดับ
- แต่ละ Provider มี daily limit ของตัวเอง
- ก่อนส่งข้อมูลไป Provider สำรอง ต้องตรวจ privacy/consent policy ใหม่ทุกครั้ง
- ถ้าไม่มี Provider ที่ใช้ได้ ให้หยุดงาน AI อย่างปลอดภัยและรายงานเหตุผล ห้ามรายงานว่างานผ่าน

**Emergency Mode**

- เข้าโหมดฉุกเฉินได้ทั้งจาก quota ที่เหลือถึง threshold หรือผู้ใช้สั่งเอง
- ค่าเริ่มต้นที่เสนอ: เมื่อ budget ที่อนุญาตเหลือไม่เกิน 20% ให้เข้า Emergency Mode (ปรับค่าได้)
- ผู้ใช้กำหนด allowlist ว่า Agent/ฟังก์ชันใดทำงานต่อได้ เช่น เหลือเฉพาะ Sleep Reminder หรือการแจ้งเตือนที่ไม่ใช้ LLM
- Alerts, scheduler และ L0 rule-based tasks ต้องทำงานต่อแม้ quota หมด เพราะไม่เรียก AI
- งาน L1/L2 ที่ไม่ได้อยู่ใน allowlist ต้องพักหรือหยุด และแจ้งสถานะ
- การออกจาก Emergency Mode ต้องเป็นไปตาม policy ที่ผู้ใช้กำหนด ไม่ใช่ Agent ปลดเอง

**สิ่งที่ยังไม่ทำใน MVP:** Budget Profiles, dashboard ซับซ้อน, budget หลายมิติแบบเต็มรูปแบบ, การคำนวณค่าใช้จ่ายหลายสกุล และระบบคาดการณ์ quota ขั้นสูง

### 7.3 Task Routing L0–L3

| Level | วิธีทำงาน | การใช้ LLM |
|---|---|---|
| L0 | Rule-based / deterministic | ไม่ใช้ |
| L1 | เรียก AI Provider หนึ่งครั้ง | 1 call |
| L2 | AI Debate ระหว่าง Proposer และ Challenger | ปกติ 2 calls |
| L3 | งานเสี่ยงสูง/มีผลกระทบ: deterministic checks และ user approval | ไม่มี Debate ใน MVP |

- ตรวจ deterministic checks ก่อนเรียก LLM เสมอ
- เลือก Level จากประเภทและความซับซ้อนของงาน ไม่ใช่ให้ Agent ยกระดับตัวเอง
- L3 ใช้ Ruff, pytest, schema checks หรือ validation ที่เหมาะสมร่วมกับ user approval ตามความเสี่ยง
- L3 ยังคงต้องผ่าน Security Core ทุกครั้ง; การผ่าน tests ไม่ได้แปลว่าได้รับอนุญาตให้ execute
- ถ้าไม่แน่ใจเรื่องระดับความเสี่ยง ให้เลือกทางที่ปลอดภัยกว่าและถามผู้ใช้

### 7.4 AI Debate MVP

AI Debate เป็นส่วนหนึ่งของ Phase 5 และทำงานผ่าน Provider Layer ของ MasterControl โดยตรง ไม่ต้องรอ OpenClaw

**บทบาท**

- **Proposer:** เสนอแนวทางหรือคำตอบเบื้องต้น
- **Challenger:** ตรวจหาข้อผิดพลาด สมมติฐานที่ไม่ครบ และความเสี่ยง
- ใช้คนละ Provider เป็นค่าเริ่มต้น เพื่อหลีกเลี่ยงการให้โมเดลเดียวตรวจงานตัวเอง
- MasterControl เป็นผู้สรุปผลด้วย code/rules ใน MVP; AI Synthesizer ปิดไว้โดยค่าเริ่มต้น

**ขอบเขตการ Debate**

- Debate 1 รอบ: Proposer → Challenger
- อนุญาต revision ได้สูงสุด 1 รอบ
- จากนั้นส่งสรุปให้ผู้ใช้ตัดสินใจ ไม่วนซ้ำไม่จำกัด
- Debate ใช้เพื่อ reasoning/review เท่านั้น **ไม่ใช่การอนุมัติ action**
- ผลจาก Debate ไม่สามารถข้าม validation, permission, approval, executor, verification หรือ audit log

**เมื่อ Provider สำรองไม่พร้อม**

- ห้ามใช้ Provider เดียวกันทั้ง Proposer และ Challenger แบบเงียบ ๆ
- งานทั่วไปที่ยอมรับการตรวจแบบชั้นเดียวได้ อาจลดระดับ L2 → L1 โดยต้องบันทึกและแจ้งว่า Debate ไม่ครบ
- งานที่ต้องการ independent challenge หรือมีความสำคัญสูง ให้หยุดและขอให้ผู้ใช้ตัดสินใจว่าจะรอหรือใช้ L1
- หากไม่มี Provider ให้หยุดงาน AI อย่างปลอดภัย

### 7.5 Phase 5 Exit Criteria

Phase 5 จะผ่านเมื่อมีหลักฐานทดสอบครบอย่างน้อยดังนี้:

1. Provider interface เรียกใช้งาน Provider ที่ตั้งค่าไว้ได้ และ validate response ได้
2. Usage log แยก Provider, request และ input/output tokens ได้ พร้อมระบุ actual/estimated
3. Daily per-provider limits และ hard stop ทำงานจริงใน tests
4. Quota reservation ป้องกัน concurrent requests ใช้งบเกิน limit
5. Fallback เคารพ privacy/consent policy และ provider-specific limit
6. ไม่มี Provider ใช้งานได้แล้วระบบหยุด AI อย่างปลอดภัย แต่ L0/Alerts ยังทำงาน
7. L0 ไม่เรียก LLM; L1 เรียกหนึ่งครั้ง; L2 ใช้ Proposer/Challenger คนละ Provider ตาม policy
8. Debate จำกัดจำนวนรอบ และไม่สามารถอนุมัติ action ได้
9. Emergency Mode จำกัด Agent/ฟังก์ชันตาม allowlist ที่ผู้ใช้กำหนด
10. Usage ของทุก Agent/Sub-Agent ถูกนับใน budget กลาง
11. มี mock tests สำหรับ timeout, quota exhaustion, provider failure, privacy rejection, malformed output และ concurrency
12. Ruff และ pytest ผ่าน CI; รายงานชัดเจนว่า live free-quota behavior และ Windows target machine ยังไม่ได้รับการยืนยันถ้ายังไม่ได้ทดสอบ

---

## 8. Phase 6 — Agent Manager & OpenClaw Decision Gate

### 8.1 Agent Manager เป็นของ MasterControl

ไม่ว่าเลือก Runtime ใด MasterControl ต้องเป็นผู้ควบคุม lifecycle ของ Agent

- สร้าง/เลือก Agent จาก task ที่ได้รับอนุญาต
- กำหนด task scope, context, tool allowlist, budget และ timeout
- Temporary Sub-Agent มีอายุสั้นและสิทธิ์เฉพาะงาน
- ไม่สืบทอด blanket approval จาก Agent อื่นหรืองานก่อนหน้า
- Agent ห้าม spawn Agent เอง
- จำกัดจำนวน Agent ที่ทำงานพร้อมกันตาม resource และ quota budget
- Agent ส่ง structured result กลับให้ MasterControl ตรวจสอบ
- เมื่อ quota หมด, timeout หรือ task ถูกยกเลิก ต้องหยุดและบันทึกสถานะอย่างตรงไปตรงมา

### 8.2 OpenClaw เป็นตัวเลือก ไม่ใช่ข้อบังคับ

OpenClaw อาจทำหน้าที่เป็น Agent Runtime เพื่อลดภาระการสร้างระบบ Multi-Agent ใหม่ แต่จะใช้ได้ต่อเมื่อพิสูจน์ว่า MasterControl บังคับขอบเขตความปลอดภัยได้จริง

ก่อน integration ให้ audit installation จริง โดยบันทึกเวอร์ชันและตรวจ:

- Agent/Sub-Agent lifecycle และ API ที่ใช้งานได้จริง
- Tool, Skill, Plugin และ Hook permission model
- direct shell, filesystem, process และ network routes ที่อาจข้าม MasterControl
- วิธีบังคับให้ action ทั้งหมดผ่าน adapter และ Security Core
- วิธีส่ง LLM calls ผ่าน MasterControl Provider Layer/Privacy policy
- prompt injection และการแยก untrusted data
- CPU/RAM/GPU footprint ใน idle และขณะทำงาน
- version pinning, update process, release notes และ security advisories

เริ่มจาก read-only Agent เพียงหนึ่งตัว เช่น Doctor และอย่าเปิด write/control tools ก่อนผ่านการทดสอบ boundary

### 8.3 OpenClaw Decision Gate

| Gate | ต้องพิสูจน์อะไร | หากไม่ผ่าน |
|---|---|---|
| Security Boundary | ปิด/ควบคุมทุก route ที่ bypass MasterControl ได้ | ห้าม action integration; read-only เท่านั้น |
| Tool Isolation | จำกัด shell/filesystem/process/network ได้ตาม task | ปิด tool ที่ควบคุมไม่ได้ |
| Permission & Approval | action ทุกชนิดกลับเข้าระบบ validate → permission → approval | ไม่เปิด action จริง |
| Provider & Privacy | LLM calls อยู่ภายใต้ Provider Layer และ consent policy | ไม่ส่งข้อมูลสำคัญ/ไม่ใช้ cloud agent |
| Reliability | timeout, disconnect, malformed output และ rollback ไม่ทำให้ระบบเสียสถานะ | คงไว้ใน test mode |
| Resource | วัดได้ว่าไม่รบกวนเครื่องและเกมตาม budget | จำกัด concurrency/หยุด integration |
| Maintenance | เจ้าของดูแล update, advisory, regression tests และ rollback ได้จริง | ไม่เลือก OpenClaw เป็น runtime หลัก |

**ผลการตัดสิน**

- **PASS:** เชื่อมผ่าน adapter แบบแยกขอบเขต เริ่ม read-only แล้วค่อยเปิด action ที่จำเป็น
- **PARTIAL:** ใช้เฉพาะความสามารถ read-only ที่พิสูจน์ได้
- **FAIL:** ไม่ integrate; ใช้แนวทาง Plan 1 คือ MasterControl ที่มี Provider/Task/Agent orchestration แบบเล็กเท่าที่จำเป็น

### 8.4 Maintenance Burden — เงื่อนไขที่ต้องตอบให้ได้

OpenClaw ไม่ได้ลดภาระทั้งหมด แต่เปลี่ยนจากการเขียน Runtime เองเป็นการดูแล dependency และ adapter

ก่อนเลือกใช้จริง เจ้าของต้องสามารถทำสิ่งเหล่านี้ได้:

1. Pin เวอร์ชันที่ผ่านการทดสอบ ไม่อัปเดตอัตโนมัติทันที
2. ตรวจ release notes และ security advisories ก่อนอัปเดต
3. รัน adapter regression tests หลังอัปเดต
4. ตรวจว่า permission/tool boundary ไม่เปลี่ยนหรือเปิดช่องใหม่
5. Rollback ไปเวอร์ชันเดิมได้
6. จัดสรรเวลาบำรุงรักษาได้อย่างต่อเนื่อง

หากภาระเหล่านี้เกินกำลังของผู้พัฒนาคนเดียว ให้เลือก Runtime ที่เล็กกว่า/เขียน adapter เองเฉพาะส่วนที่จำเป็น หรือยังไม่ใช้ OpenClaw การเลือกเทคโนโลยีต้องคำนึงถึงความสามารถในการดูแลระยะยาว ไม่ใช่แค่ความสามารถในวันแรก

---

## 9. Phase 7 — Discord Integration

Discord เป็นช่องทางสื่อสารกับ MasterControl ไม่ใช่ Agent Runtime

ขอบเขตที่เสนอ:

- รับคำสั่งจาก owner ที่ระบุตัวตนได้เท่านั้น
- ส่ง notification, task reports และ approval requests
- ปุ่ม approve/cancel ต้องผูกกับ owner identity และ action ID ที่ตรวจสอบได้
- ห้ามใช้ Discord message เป็นหลักฐานอนุมัติ หาก identity หรือ context ไม่ครบ
- ไม่เปิด webhook URL หรือ bot token ใน logs/repository
- หาก Discord ล่ม ระบบ local alerts และ L0 ต้องทำงานต่อ

---

## 10. Phase 8 — Proactive Intelligence

เริ่มจาก rule-based/event-driven ก่อน เช่น:

- แจ้งเตือน task deadline, bedtime และเหตุการณ์ที่ผู้ใช้ตั้งไว้
- Morning SITREP เมื่อ login
- สรุป task ที่ค้างจากข้อมูลที่อนุญาต
- ตรวจ telemetry และแจ้งความผิดปกติด้วย threshold ที่กำหนด
- แนะนำ Agent ที่เหมาะสม แต่ให้ MasterControl เป็นผู้ตัดสินใจมอบหมาย
- ตรวจการเปลี่ยนแปลงใน folder allowlist เท่านั้น

ระบบต้องไม่กลายเป็นสิ่งรบกวน และต้องมีวิธี snooze, disable หรือปรับความถี่ได้

## 11. Phase 9 — The Grid Desktop Experience

ความสามารถเป้าหมาย:

- System tray และสถานะ MasterControl
- Global hotkey และ command palette/floating overlay
- Notification Center และประวัติ action
- หน้าตั้งค่า Privacy, Provider, Budget, Agent และ Permission
- File Intelligence เริ่มจาก metadata/read-only และ folder allowlist
- การเขียน ย้าย เปลี่ยนชื่อ หรือลบไฟล์ต้อง preview และใช้ approval ตาม risk

ทำ UI ให้เรียบง่าย ไม่ใช้ animation หนัก และไม่แย่ง focus จากงานหรือเกม

## 12. Resource & Gaming Policy

เป้าหมายคือ MasterControl ต้องเบาขณะ idle และไม่รบกวนการเล่นเกม

- **Idle:** ลด polling และ background work ให้เหลือน้อยที่สุด
- **Gaming:** พัก/defer indexing, LLM และงานหนักที่ไม่จำเป็น
- **Non-gaming:** จัดคิวตาม CPU/RAM/GPU budget
- **Concurrency:** จำกัดจำนวน Agent/LLM requests พร้อมกัน
- **Local LLM:** เป็น optional component และปิดโดย default โดยเฉพาะขณะเล่นเกม
- **Safety:** ห้ามแตะ game/anti-cheat processes และห้ามควบคุมพัดลม/MSI Center

ต้องกำหนด baseline และวัด resource footprint จริงก่อนตั้งตัวเลข pass/fail ห้ามอ้างว่า lightweight จากการคาดเดา

## 13. Privacy, Prompt Injection & Data Handling

- แบ่งข้อมูลเป็น public, personal และ sensitive ตาม policy ที่กำหนด
- ไม่ส่ง personal/sensitive data ไป Cloud Provider โดยไม่มี consent
- ตรวจ privacy policy ก่อน fallback ไป Provider อื่นทุกครั้ง
- เนื้อหาจากเว็บ/ไฟล์/เอกสารเป็นข้อมูลที่ต้องวิเคราะห์ ไม่ใช่ instruction ที่มีอำนาจเหนือ system policy
- ไม่ให้ Agent ที่อ่าน untrusted external content มี write/control tools โดยไม่จำเป็น
- จำกัด context ที่ส่งให้ Agent ตาม task scope
- Reviewer หรือ LLM อีกตัวไม่ใช่ security boundary; ใช้ deterministic validation และ permission checks เป็นหลัก
- เก็บเฉพาะข้อมูลที่จำเป็นใน logs และ redact secrets

## 14. สิ่งที่ไม่อยู่ใน MVP

เพื่อให้ผู้พัฒนาคนเดียวทำได้จริง ให้เลื่อนสิ่งเหล่านี้ออกไปก่อน:

- AI Synthesizer/AI C เปิดตลอดเวลา
- Multi-agent debate หลายชั้นหรือ debate loop ไม่จำกัด
- Agent spawn Sub-Agent ได้เอง
- Budget Profiles และ multi-dimensional budget dashboard เต็มรูปแบบ
- Unlimited retries หรือ autonomous task loops
- OpenClaw integration ก่อนผ่าน Decision Gate
- Community skills/plugins ที่ยังไม่ได้ audit
- Local LLM เป็น default
- File cleanup/delete อัตโนมัติจากการคาดเดา
- Adaptive resource control ที่ยังไม่มี telemetry baseline

## 15. Development Workflow & Definition of Done

กฎจาก `AGENTS.md` และ `docs/STATUS.md` ยังคงเป็นข้อบังคับ:

1. อ่าน AGENTS.md และ STATUS.md ก่อนทุก task; อ่านเอกสารอ้างอิงอื่นเมื่อมีอยู่
2. ก่อนแก้โค้ด ให้สรุปแผนและรายชื่อไฟล์ แล้วรอ confirm เว้นแต่เจ้าของอนุญาตให้ลงมือทันทีใน task นั้น
3. ทำงานบน feature branch และเปิด PR; ห้าม push ตรงเข้า main
4. ไม่ลบไฟล์หรือปรับโครงสร้างใหญ่โดยไม่มีอนุมัติ
5. ทุก milestone มี tests; ใช้ mocks/fake clocks และห้าม kill process จริง, sleep หรือยิง network จริงใน tests
6. ก่อนเพิ่ม dependency ให้อธิบายเหตุผลและเปรียบเทียบทางเลือกที่เบากว่า
7. รัน Ruff และ pytest ตามที่ repo กำหนด
8. อัปเดต STATUS.md เมื่อสถานะ implementation เปลี่ยนจริง โดยแยก Mock/CI verified กับ Windows verified
9. รายงานไฟล์ที่เปลี่ยน วิธีทดสอบ ข้อจำกัด และสิ่งที่ยังไม่ทำ
10. ห้ามรายงานว่าสำเร็จหากไม่มีหลักฐาน verify

ทุก Phase จะถือว่าผ่านเมื่อ scope เสร็จ, tests ที่เกี่ยวข้องผ่าน, failure/security paths ได้รับการทดสอบ, ไม่มีการลดระดับ Permission/Approval และเอกสารสะท้อนสถานะจริง

---

## 16. สรุปการตัดสินใจเชิงสถาปัตยกรรม

- **The Grid:** ชื่อระบบนิเวศทั้งหมด
- **MasterControl:** Control Plane, Security Authority, Provider/Budget Manager และ Agent Manager
- **OpenClaw:** Agent Runtime แบบ conditional; ไม่ใช่ผู้มีอำนาจด้าน security
- **Agents:** ผู้เชี่ยวชาญเฉพาะงานที่มี scope และ tool allowlist
- **Temporary Sub-Agents:** สร้างและควบคุมโดย MasterControl เท่านั้น
- **AI Debate:** ความสามารถของ MasterControl Phase 5 ไม่ขึ้นกับ OpenClaw
- **Discord:** ช่องทางคำสั่ง/รายงาน/approval แยกจาก Runtime
- **Security Core:** ทุก action ต้องผ่าน validate → permission → approval (if needed) → execute → verify → log

**แนวทางที่เลือก:** ทำ MasterControl ให้ปลอดภัยและทำงานได้ด้วยตัวเองก่อน จากนั้นค่อยเพิ่ม Agent Runtime เมื่อพิสูจน์แล้วว่าคุ้มค่ากับความเสี่ยงและภาระดูแลระยะยาว
