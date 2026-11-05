<!-- แผนแม่บท The Grid และการพัฒนา MasterControl -->

# THE GRID — Master Plan

> **สถานะเอกสาร:** แผนเป้าหมายและทิศทางการพัฒนา (Proposal)  
> **โปรเจกต์หลัก:** [Master_Control](https://github.com/firstnotoxic-beep/Master_Control)  
> **หลักการ:** ระบบรวมศูนย์ที่มี MasterControl เป็นผู้ควบคุมสูงสุด และใช้ OpenClaw เป็น Agent Runtime โดยต้องไม่ข้ามระบบความปลอดภัยของ MasterControl

---

## 1. วิสัยทัศน์

**The Grid** คือระบบนิเวศ AI ส่วนตัวบนเครื่อง Windows ที่รวมผู้ช่วยอัจฉริยะ เครื่องมือ และ Agent หลายบทบาทไว้ภายใต้ศูนย์บัญชาการเดียว

เป้าหมายไม่ใช่แค่แชตบอตที่รอรับคำสั่ง แต่เป็นผู้ช่วยที่สามารถรับรู้ข้อมูลที่ได้รับอนุญาต วิเคราะห์บริบท ตรวจพบสิ่งที่ควรแจ้งเตือน มอบหมายงานให้ผู้เชี่ยวชาญ และเสนอหรือดำเนินการตามสิทธิ์ที่กำหนด

### หลักการสำคัญ

1. **Centralized Control:** ทุก Agent อยู่ภายใต้นโยบายและการกำกับของ MasterControl
2. **Agent Executes, MasterControl Governs:** Agent รับผิดชอบงานเฉพาะด้าน แต่ MasterControl เป็นผู้จัดสรรงานและควบคุมการกระทำ
3. **Security First:** ไม่มี Agent หรือ LLM ใดมีสิทธิ์ข้าม Permission, Approval และ Audit
4. **Proactive, Not Intrusive:** แจ้งเตือนเมื่อมีประโยชน์ ไม่รบกวนหรือบังคับผู้ใช้
5. **Lightweight:** ใช้ทรัพยากรต่ำขณะ idle และลด/พักงานหนักระหว่างเล่นเกม
6. **Incremental Development:** พัฒนาทีละส่วน รักษาของเดิม และตรวจสอบได้ทุกขั้น

## 2. โครงสร้างระบบเป้าหมาย

```text
THE GRID — Personal AI Ecosystem
|
+-- MASTERCONTROL — Central Command & Control Plane
|   |
|   +-- Context / Proactive Engine
|   +-- Agent Manager & Task Router
|   +-- Permission / Approval / Audit
|   +-- Resource & Gaming Mode Manager
|   +-- Windows Integration (Tray / Hotkey / Overlay)
|   +-- File & Knowledge Intelligence
|   |
|   +-- OPENCLAW RUNTIME — Agent Execution Layer
|       |
|       +-- Doctor
|       +-- Developer
|       +-- Document Staff
|       +-- Researcher
|       +-- Analyst
|       +-- Reviewer
|       +-- Temporary Sub-Agents
|
+-- MASTERCONTROL SECURITY CORE
|   +-- Validate
|   +-- Permission Check
|   +-- Approval (when required)
|   +-- Execute through controlled adapters
|   +-- Verify
|   +-- Audit Log
|
+-- THE GRID HOST — Windows 11
    +-- Files / Folders
    +-- Applications / Processes
    +-- Hardware Telemetry
    +-- Notifications
    +-- User-approved integrations
```

แผนภาพนี้เป็นสถาปัตยกรรมเป้าหมาย ไม่ใช่คำยืนยันว่าทุกส่วนมีอยู่ในโค้ดปัจจุบันแล้ว

### หน้าที่ของแต่ละส่วน

| ส่วน | หน้าที่ |
|---|---|
| The Grid | ชื่อระบบนิเวศและสภาพแวดล้อมทั้งหมด |
| MasterControl | ศูนย์บัญชาการ รับคำขอ วิเคราะห์บริบท เลือก Agent ควบคุมสิทธิ์ และติดตามผล |
| OpenClaw | Runtime สำหรับสนทนา จัดการ Agent/Sub-Agent และเรียกใช้ Tools/Skills ที่อนุญาต |
| Security Core | ด่านบังคับก่อนการกระทำกับข้อมูลหรือระบบจริง |
| Resource Manager | จัดคิวงานและควบคุมการใช้ CPU/RAM/GPU ตามสถานการณ์ |
| The Grid Host | เครื่อง Windows และทรัพยากรที่ระบบได้รับอนุญาตให้เข้าถึง |

## 3. ทำไมเลือกปรับแต่ง OpenClaw แทนการสร้าง Agent Runtime ใหม่

แนวทางที่เสนอคือ **ใช้ OpenClaw เป็นฐานการทำงานของ Agent และสร้าง Integration Layer เชื่อมกับ MasterControl** แทนการเขียนระบบ Multi-Agent ใหม่ทั้งหมด

สิ่งที่ต้องตรวจสอบกับ OpenClaw เวอร์ชันที่ติดตั้งจริงก่อนพัฒนา ได้แก่

- การสร้าง จัดการ และเรียกใช้ Agent/Sub-Agent
- การส่งงานและรับผลกลับระหว่าง Agent
- การกำหนด Tools, Skills, Plugins และสิทธิ์ของแต่ละ Agent
- Hooks หรือจุดเชื่อมต่อสำหรับตรวจคำขอและผลการทำงาน
- การจำกัดสิทธิ์เข้าถึงไฟล์, shell, process และ network
- การทำงานแบบ local, การเชื่อมต่อ และผลต่อทรัพยากร
- วิธีอัปเดตและความเข้ากันได้ของ API ในเวอร์ชันที่ใช้อยู่

**แนวทางการปรับแต่ง:** เริ่มจาก config, plugin, skill และ adapter ก่อน หลีกเลี่ยงการแก้ OpenClaw core หรือทำ fork ขนาดใหญ่จนกว่าจะพิสูจน์ว่าจำเป็น เพื่อให้รับ upstream updates ได้ง่าย

การใช้ OpenClaw ยังเป็นข้อเสนอเชิงสถาปัตยกรรม ต้องผ่านการ audit ของ installation จริงก่อนยืนยันความสามารถและข้อจำกัด

## 4. Agent Organization

Agent เป็นผู้เชี่ยวชาญตามหน้าที่ ไม่ใช่ผู้มีอำนาจอิสระเหนือเครื่อง

| Agent | ขอบเขตงานเป้าหมาย | ข้อจำกัดเริ่มต้น |
|---|---|---|
| Doctor | ตรวจสุขภาพระบบ วิเคราะห์ resource และอธิบายปัญหา | Read-only; ห้ามซ่อมหรือเปลี่ยนค่าระบบเอง |
| Developer | ช่วยเขียน ตรวจ และทดสอบโค้ด | ทำงานใน workspace ที่อนุญาต; การแก้ไฟล์ต้องผ่านนโยบาย |
| Document Staff | ค้นหา สรุป จัดหมวด และเปรียบเทียบเอกสาร | จำกัดโฟลเดอร์; ไม่ส่งเนื้อหาส่วนตัวขึ้น cloud โดยไม่มี consent |
| Researcher | ค้นคว้าและรวบรวมข้อมูล | Network ตาม allowlist และนโยบายข้อมูล |
| Analyst | วิเคราะห์ข้อมูลและสร้างรายงาน | ใช้เฉพาะข้อมูลที่ได้รับอนุญาต |
| Reviewer | ตรวจงาน ความถูกต้อง ความเสี่ยง และผลลัพธ์ | ไม่มีสิทธิ์อนุมัติ action แทนเจ้าของ |
| Temporary Sub-Agent | รับงานย่อยเฉพาะกิจ | อายุสั้น ขอบเขตแคบ และสิทธิ์เฉพาะงาน |

### กฎการมอบหมายงาน

- MasterControl เป็นผู้เลือก Agent และกำหนดขอบเขตงาน
- งานหนึ่งอาจแบ่งเป็นงานย่อยให้หลาย Agent ได้ แต่ต้องมีผู้รวบรวมผลกลับ
- Agent ต้องรายงานผลและข้อจำกัด ไม่อ้างว่าสำเร็จหากยังไม่ได้ตรวจสอบ
- Temporary Sub-Agent ต้องมี task scope, tool allowlist และอายุการทำงานจำกัด
- ห้ามสืบทอด blanket approval จาก Agent อื่นหรือจากงานก่อนหน้า
- Agent ที่เริ่มต้นใช้งานควรเป็น read-only ก่อนเปิดความสามารถแก้ไขหรือสั่งงานระบบ

## 5. Security & Permission Architecture

ทุกการกระทำที่กระทบข้อมูลหรือเครื่องต้องผ่านเส้นทางเดียว:

```text
Agent / AI proposes structured action
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
  User Approval
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

- LLM และ Agent เสนอได้เฉพาะ action แบบ structured/validated data ไม่ใช่ส่งคำสั่งอิสระให้ระบบรัน
- รักษา flow: **validate → permission → approval (if needed) → execute → verify → log**
- ระดับความเสี่ยง MEDIUM ขึ้นไปต้องอนุมัติจากผู้ใช้
- CRITICAL ห้ามระบบดำเนินการเอง
- ห้ามใช้ `shell=True`, `eval`, `exec` หรือ `os.system` กับข้อความจากผู้ใช้, LLM, Skill หรือ Agent
- ใช้ allowlist และ argument list สำหรับเครื่องมือที่จำเป็น
- Agent ไม่ได้รับ unrestricted shell, filesystem หรือ process-control access
- ห้ามแตะต้อง game/anti-cheat processes; การปิด process ต้องใช้ exact-name allowlist เท่านั้น
- ห้ามควบคุมพัดลมหรือ MSI Center; อ่านอุณหภูมิได้ตามข้อกำหนดเดิม
- Secrets อยู่ในไฟล์ที่ gitignore และห้ามบันทึกลง log หรือส่งเข้า cloud
- หากตรวจสอบผลไม่ได้ ให้รายงานว่าไม่สามารถยืนยันผลได้
- Skill Python ปัจจุบันทำงานใน process เดียวกับ MasterControl และ **ไม่ใช่ OS sandbox**; ต้อง review source ก่อน enable

### OpenClaw Integration Security Gate

ก่อนเชื่อมต่อ OpenClaw ต้องตรวจว่ามีเส้นทางใดที่ Agent สามารถเรียกเครื่องมือโดยตรงโดยไม่ผ่าน MasterControl หรือไม่

- ปิดหรือจำกัด direct tools ที่ทำให้ข้าม Security Core ได้
- เปิดให้เรียก action ผ่าน adapter ที่มี schema และ allowlist เท่านั้น
- แยก read-only tools ออกจาก write/control tools
- ทดสอบทั้งกรณีอนุญาต ปฏิเสธ approval ไม่ครบ และ executor ล้มเหลว
- ถ้ารับประกันการบังคับใช้ permission ไม่ได้ ให้คง OpenClaw ไว้ในโหมดทดลอง/read-only และยังไม่เชื่อมต่อ action จริง

## 6. Proactive Intelligence

เป้าหมายคือให้ MasterControl ตรวจจับเหตุการณ์ที่ได้รับอนุญาตและเสนอความช่วยเหลืออย่างเหมาะสม

ตัวอย่างความสามารถในอนาคต:

- ตรวจสถานะ CPU/RAM/GPU และ process ที่ใช้ทรัพยากรสูง
- แจ้งเตือนเมื่อพบความผิดปกติหรือเหตุการณ์ที่ตรงกับกฎ
- สรุปงานค้างและกำหนดส่ง
- Morning SITREP เมื่อเข้าสู่ระบบ
- ตรวจการเปลี่ยนแปลงในโฟลเดอร์ที่ผู้ใช้อนุญาต
- แนะนำ Agent ที่เหมาะกับงานและมอบหมายงานย่อย
- ติดตามผลของงานและแจ้งเมื่อจำเป็นต้องให้ผู้ใช้ตัดสินใจ

เริ่มจาก rule-based detection ก่อน ใช้ LLM เฉพาะเมื่อกฎไม่สามารถตีความคำขอหรือบริบทได้ และต้องผ่าน AI Provider Layer ตามแผน

## 7. File & Knowledge Intelligence

ระบบค้นหาและช่วยจัดการไฟล์โดยเคารพความเป็นส่วนตัว

ลำดับความสามารถเป้าหมาย:

1. ค้นหาไฟล์จากชื่อ นามสกุล ตำแหน่ง และ metadata ในโฟลเดอร์ที่อนุญาต
2. ทำดัชนีเนื้อหาเฉพาะชนิดไฟล์และพื้นที่ที่ผู้ใช้เลือก
3. ค้นหาจากความหมายหรือคำอธิบายของเนื้อหา
4. เปรียบเทียบเอกสารที่คล้ายกันและแสดงความแตกต่าง
5. ประเมินว่าไฟล์ใดน่าจะเป็นฉบับล่าสุดหรือสมบูรณ์กว่า โดยอธิบายเหตุผลและไม่ตัดสินแทนผู้ใช้
6. เสนอการจัดหมวดหมู่หรือย้ายไฟล์เป็นแผนก่อนเสมอ

### Privacy & Safety

- ใช้ folder allowlist และเริ่มต้นจาก metadata/read-only
- ไม่อ่านโฟลเดอร์ส่วนตัวที่ไม่ได้อนุญาต
- ไม่ส่งเนื้อหาไฟล์ไปยัง cloud AI โดยไม่มี consent ชัดเจน
- การเขียน ย้าย เปลี่ยนชื่อ หรือลบ ต้องมี preview และ permission ตามความเสี่ยง
- ห้ามลบไฟล์อัตโนมัติจากการคาดเดาว่าเป็น duplicate

## 8. Desktop Experience

ความสามารถที่ต้องการในระยะถัดไป:

- Global hotkey เรียก MasterControl ได้จากทุกหน้าต่าง
- Command palette หรือ floating overlay
- System tray สำหรับสถานะและ quick actions
- Notification Center ที่ดูย้อนหลังได้
- หน้าตั้งค่า Privacy, Agent และ Permission
- พิจารณาการ remap Copilot key เฉพาะเมื่อ Windows และฮาร์ดแวร์รองรับอย่างปลอดภัย

เริ่มจาก UI แบบเรียบง่าย ไม่ใช้ animation หนัก และไม่แย่ง focus จากแอปที่ผู้ใช้กำลังใช้งาน

## 9. Resource & Gaming Management

The Grid ต้องไม่รบกวนการเล่นเกม

- Idle: ใช้ทรัพยากรให้น้อยที่สุดและไม่โหลด local LLM โดยอัตโนมัติ
- Gaming: ลด polling, หยุดหรือพักงาน indexing/LLM ที่ไม่จำเป็น และไม่เปิดงานหนักใหม่
- Non-gaming: ทำงานเบื้องหลังตาม resource budget
- Heavy tasks: จัดคิว จำกัด concurrency และให้ผู้ใช้ยกเลิก/เลื่อนงานได้
- Local model เป็น optional component ไม่ใช่ default; cloud provider ใช้ตาม consent และ privacy policy
- ห้ามแตะ game/anti-cheat processes และไม่ควบคุมพัดลม

เป้าหมายคือ Resource Manager แบบ adaptive ที่ค่อย ๆ พัฒนาโดยใช้ telemetry จริง ไม่ใช่ hardcode การคาดเดา

## 10. AI Provider Strategy

แนวทางที่ระบุใน STATUS ปัจจุบันคือ Cloud-first free APIs: Groq → Gemini → GitHub Models และ Local AI/Ollama เป็น optional plugin ที่ปิดระหว่างเล่นเกม

ข้อกำหนด:

- AI Provider Layer เป็นผู้จัดการ provider, fallback, timeout และ usage log
- ส่งเฉพาะ prompt/context ที่จำเป็นและได้รับอนุญาต
- ห้ามส่ง secrets หรือข้อมูลส่วนตัวโดยไม่มี consent
- AI ส่งกลับ structured proposals ที่ผ่าน Pydantic validation
- หาก provider ใช้งานไม่ได้ ระบบ rule-based และคำสั่งพื้นฐานต้องยังทำงานได้
- ไม่เรียก LLM สำหรับงานง่ายที่ rule-based ทำได้

## 11. สถานะโปรเจกต์ปัจจุบันจาก Repository

ข้อมูลส่วนนี้อ้างอิงจาก `docs/STATUS.md`, `README.md`, `AGENTS.md`, `docs/SKILLS.md`, `docs/SECURITY.md` และโค้ดที่ตรวจได้ ณ วันที่จัดทำเอกสาร

### สิ่งที่มีอยู่แล้ว

| ส่วน | สถานะในเอกสาร/โค้ดปัจจุบัน |
|---|---|
| Phase 1 — Foundation | ทำแล้วใน mock tests; Windows verification ยัง pending |
| Phase 2 — Telemetry / Process Monitor / Mode Engine | ทำแล้วใน mocks; Windows verification ยัง pending |
| Phase 3 — Alert Engine | ทำแล้วใน mocks; Windows verification ยัง pending |
| Phase 4 — Skill Framework | Code complete และ CI verified; Windows verification ยัง pending |
| Skill Registry | มี opt-in loader, manifest validation, capability risk floors, prepare/execute validation และ action logging |
| Example Skills | quick_note, task_list, brain_dump, daily_report; ปิดไว้โดยค่าเริ่มต้น |
| Database | SQLite schema version 4 |
| CI | GitHub Actions ใช้ Windows runner, Python 3.12, Ruff และ pytest; เป็น mock tests ไม่ใช่การยืนยันบนเครื่องจริง |
| Security notes | มีเอกสารข้อจำกัดด้าน path/reparse checks และย้ำว่า Python Skills ไม่ใช่ OS sandbox |

### สิ่งที่ยังไม่ควรเข้าใจว่าทำเสร็จแล้ว

- OpenClaw ยังไม่ได้รับการยืนยันว่าเชื่อมกับ MasterControl ผ่าน security boundary ได้
- ยังไม่มีหลักฐานว่า Agent/Sub-Agent ทั้งหมดในแผนนี้ถูกสร้างและจัดการโดย MasterControl แล้ว
- AI Provider Layer ยังเป็นแผน
- Discord integration ยังเป็นแผนใน STATUS ปัจจุบัน
- Task Engine, Morning SITREP, Voice และ File/Screenshot Intelligence ยังอยู่ใน roadmap
- Hotkey, overlay, system tray และ Resource Manager แบบ adaptive ยังไม่ควรนับว่าเสร็จ
- Windows 11 target-machine verification ยัง pending

### ความต่างของแผนเดิมกับทิศทางใหม่

STATUS ปัจจุบันระบุ Phase 6 เป็น Discord bot และ OpenClaw migration แต่แผน The Grid ฉบับนี้เสนอให้ **ประเมิน OpenClaw ใหม่ในฐานะ Agent Runtime หลัก** แทนการรีบแทนที่ OpenClaw ด้วย Discord bot

ดังนั้นยังไม่ควรแก้ STATUS หรือย้าย phase จนกว่าจะ audit OpenClaw installation จริงและยืนยันสถาปัตยกรรมร่วมกัน

## 12. Roadmap ที่เสนอ

ลำดับต่อไปนี้เป็นแผนเสนอเพื่อพัฒนาอย่างปลอดภัย ไม่ใช่สถานะงานที่ทำเสร็จแล้ว

### Stage 0 — Baseline & OpenClaw Audit

- อ่าน repository status และรักษา Phase 1–4 ตามเดิม
- ตรวจ OpenClaw เวอร์ชันและรูปแบบการติดตั้งจริง
- ตรวจ Agent/Sub-Agent, Tools, Skills, Plugins, Hooks และ security controls ที่มีจริง
- ตรวจ direct execution paths ที่อาจข้าม MasterControl
- วัด resource footprint แบบ idle และขณะทำงาน
- สรุป architecture options และข้อจำกัดก่อนเริ่ม integration

**Exit criteria:** มีรายงาน capability matrix, security gap list, resource baseline และข้อเสนอ adapter design

### Stage 1 — Phase 4.5: Reliability & Security

- Self-diagnostic และ error recovery
- Action preview และ audit timeline
- ทดสอบ failure paths และ rollback
- ตรวจ config validation และ recovery
- ปิดช่องทางที่ทำให้ action ข้าม permission/approval
- ทำ pending real-Windows checks ของ Phase 1–4 เมื่อเข้าถึงเครื่องได้

**Exit criteria:** การทำงานผิดพลาดไม่ทำให้ action ที่ไม่ได้รับอนุญาตเกิดขึ้น และมี log/ผลตรวจสอบครบ

### Stage 2 — MasterControl ↔ OpenClaw Adapter (Read-only)

- สร้าง adapter boundary แยกจาก core
- เชื่อมเฉพาะ status/context ที่อนุญาต
- ทดลอง Agent หนึ่งตัว เช่น Doctor ใน read-only mode
- จำกัด tools, context และ resource budget
- ทดสอบ disconnect, timeout, malformed output และ agent failure

**Exit criteria:** Agent ส่งผลกลับ MasterControl ได้ แต่ไม่สามารถสั่งเปลี่ยนแปลงระบบโดยตรง

### Stage 3 — Central Agent Manager

- MasterControl สร้าง/เลือก/มอบหมาย Agent ตามงาน
- รองรับ temporary subagents ที่มี task scope
- กำหนด tool allowlist ต่อ Agent
- รวมผลลัพธ์และส่งให้ผู้ใช้ตรวจสอบ
- เพิ่ม audit trail ของการมอบหมายและผลลัพธ์

**Exit criteria:** MasterControl เป็นจุดกลางของการจัดงานและติดตามผลทุก Agent

### Stage 4 — Controlled Actions

- เพิ่ม action adapter แบบ structured
- เชื่อมกับ Pydantic validation, Permission และ Approval เดิม
- เริ่มจาก action ความเสี่ยงต่ำและ workspace ที่กำหนด
- เพิ่ม verify และ audit ทุกการกระทำ
- ทดสอบการปฏิเสธคำสั่งที่พยายามข้าม policy

**Exit criteria:** ไม่มี consequential action ที่เรียกจาก Agent แล้วข้าม Security Core ได้

### Stage 5 — AI Provider Layer

- ทำ provider abstraction และ fallback
- ใช้ Groq → Gemini → GitHub Models ตาม config/availability
- บังคับ structured proposals และ validation
- เพิ่ม consent, privacy filtering, usage logging และ failure handling

**Exit criteria:** AI ช่วยตีความ/เสนอ action ได้โดย Core ยังคงเป็นผู้ตัดสินใจ

### Stage 6 — Proactive & Personal Intelligence

- Task Engine และ Morning SITREP
- Event-driven/rule-based monitoring
- File indexing แบบ opt-in
- Document Staff และ Researcher
- Voice interface เป็น optional module

**Exit criteria:** ระบบแจ้งสิ่งที่มีประโยชน์และค้นหาข้อมูลในพื้นที่ที่ผู้ใช้อนุญาตได้

### Stage 7 — Desktop & Gaming Experience

- Hotkey, tray, command palette และ overlay
- Resource Manager และ adaptive scheduling
- Gaming-aware pause/defer
- UI Privacy/Agent/Permission settings

**Exit criteria:** เรียกใช้ได้สะดวกและไม่รบกวนงานหรือเกม

### Stage 8 — Ecosystem & Extensibility

- Skill/Agent versioning
- Compatibility checks
- Review workflow สำหรับ extension
- Config export/import
- Documentation และ recovery procedures

**Exit criteria:** เพิ่มความสามารถใหม่ได้โดยไม่ต้องแก้ core บ่อย และยังรักษา security boundary ได้

## 13. แนวทางการพัฒนาและ GitHub Workflow

กฎของ repository ยังคงมีผลกับทุก Stage:

1. อ่าน `AGENTS.md`, `docs/STATUS.md` และเอกสารที่เกี่ยวข้องก่อนทำงาน
2. ก่อนแก้โค้ด สรุปแผนและรายการไฟล์ที่จะแก้ แล้วรอคำว่า confirm เว้นแต่เจ้าของอนุญาตให้ลงมือทันทีใน task นั้น
3. ทำงานบน feature branch และเปิด PR เท่านั้น
4. **ห้าม push/merge เข้า main โดยตรง และห้าม merge PR เอง**
5. ไม่ลบไฟล์หรือปรับโครงสร้างใหญ่โดยไม่มีอนุมัติ
6. ทุก milestone มี pytest tests; ใช้ mocks/fake clocks และห้าม kill process จริง, sleep หรือยิง network จริงใน tests
7. ใช้ dependencies เท่าที่จำเป็นและเลือกทางเลือกที่เบากว่าก่อน
8. อัปเดต `docs/STATUS.md` ให้แยก mock/CI verified กับ Windows verified ชัดเจน
9. สรุปไฟล์ที่เปลี่ยน วิธีทดสอบ สิ่งที่ยังไม่ทำ และขั้นตอนตรวจบนเครื่องจริง
10. ไม่รายงานว่าสำเร็จจนกว่าจะ verify ผลจริง

## 14. Definition of Done

ทุก Stage จะถือว่าเสร็จเมื่อ:

- ขอบเขตงานตรงกับแผนและไม่มีการเปลี่ยนแปลงนอก scope
- `ruff check .` และ `pytest -q` ผ่าน
- มี tests สำหรับ failure paths และ security boundaries ที่เกี่ยวข้อง
- ไม่มีการลดระดับ Permission หรือ Approval
- มี audit log และการตรวจผลตามความเหมาะสม
- `docs/STATUS.md` อัปเดตแล้ว
- รายงานข้อจำกัดและสถานะ Windows verification ตามจริง
- เจ้าของตรวจและอนุมัติ PR ก่อน merge

## 15. งานถัดไปที่แนะนำ

**เริ่มจาก Stage 0 — OpenClaw Audit เท่านั้น**

ยังไม่ควรเริ่มเขียน integration หรือแก้ OpenClaw core จนกว่าจะได้คำตอบจากการตรวจจริงว่า:

1. OpenClaw ที่ติดตั้งอยู่เป็นเวอร์ชันใดและเปิดใช้งานอย่างไร
2. มี API หรือ plugin interface ใดที่เหมาะสำหรับ MasterControl
3. Agent/Sub-Agent สามารถจำกัด tool permissions ได้ระดับใด
4. มีเส้นทางใดที่ Agent เรียก shell/filesystem/process ได้โดยไม่ผ่าน MasterControl
5. จะบังคับให้ action ทั้งหมดผ่าน Security Core ได้อย่างไร
6. การทำงานเพิ่มขึ้นส่งผลต่อ CPU/RAM/GPU เท่าใด

เมื่อ audit เสร็จ ให้ทำเอกสาร integration design และ threat model ก่อนสร้าง adapter

---

**สรุปสั้นที่สุด:** The Grid คือระบบรวมศูนย์, MasterControl คือผู้บัญชาการและผู้รักษากฎ, OpenClaw คือ Agent Runtime, Agent คือผู้เชี่ยวชาญเฉพาะด้าน และไม่มี Agent ใดมีอำนาจข้าม Security Core ของ MasterControl ได้
