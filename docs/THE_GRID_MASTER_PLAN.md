<!-- แผนแม่บท The Grid และ Roadmap แบบ Hybrid ของ MasterControl -->

# THE GRID — Unified Hybrid Architecture & Roadmap

> **เอกสารนี้กำหนดสถาปัตยกรรมเป้าหมายและลำดับการพัฒนา** ไม่ใช่หลักฐานว่าฟีเจอร์ในแผนถูก implement แล้ว  
> สถานะ implementation และผลทดสอบจริงให้ยึด [docs/STATUS.md](STATUS.md) เป็นแหล่งข้อมูลเดียว  
> ตรวจทานเอกสารล่าสุด: 2026-11-09

---

## 1. วิสัยทัศน์และขอบเขต

**The Grid** คือระบบนิเวศผู้ช่วย AI ส่วนตัวบน Windows 11 ส่วน **MasterControl** คือศูนย์บัญชาการ (Control Plane) ที่รับคำสั่ง กำหนดขอบเขตงาน เลือก Skill/Provider/Agent และรักษานโยบายความปลอดภัยทั้งหมด

เป้าหมายไม่ใช่การให้ AI ควบคุมเครื่องได้อย่างอิสระ แต่เป็นการให้ AI ช่วยคิด ค้นข้อมูล วางแผน และเสนอการกระทำ โดย MasterControl ยังคงเป็นผู้ตัดสินว่าการกระทำนั้นได้รับอนุญาตหรือไม่

หลักการ:

1. **MasterControl governs; workers execute.** Skill, LLM และ Agent ไม่มีอำนาจเปลี่ยน Permission หรืออนุมัติ action
2. **Rule-based first.** งานที่ Core ทำได้แน่นอนให้ใช้กฎและโค้ดปกติ ไม่เรียก LLM
3. **Hybrid Skills.** รองรับทั้ง Skill ที่ให้คำแนะนำด้วย Markdown และ Skill ที่มี Python สำหรับงานที่ต้องกระทำจริง
4. **Security Core เดียว.** ทุก Action Skill และ AI proposal ใช้ lifecycle และ permission system ชุดเดิม ห้ามสร้างทางลัด
5. **Privacy by default.** ไม่ส่งไฟล์หรือข้อมูลส่วนตัวไป Cloud หากยังไม่มี consent และ policy ที่เหมาะสม
6. **Opt-in extensions.** Skill ภายนอกและความสามารถใหม่ต้องผ่านการตรวจสอบและเปิดใช้งานโดยเจ้าของ
7. **Lightweight.** idle ต้องเบา และระหว่างเล่นเกมให้พักหรือเลื่อนงาน AI/indexing ที่ไม่จำเป็น
8. **Small, verifiable milestones.** ทดสอบด้วย mocks/fake clocks แยกจากผลทดสอบบนเครื่อง Windows จริง

## 2. สถาปัตยกรรมเป้าหมาย

### 2.1 The Grid และ MasterControl

- **Command Interface:** รับคำสั่งจาก Dashboard, CLI, hotkey และช่องทางสื่อสารที่ได้รับอนุญาต
- **Command & Task Router:** แยกงานที่จัดการด้วยกฎ งานที่ต้องใช้ AI และงานที่เหมาะกับ Agent
- **Skill Manager:** ค้นพบ แสดงรายละเอียด ตรวจสอบ เปิด/ปิด และเรียกใช้ Skills
- **AI Provider Layer:** ส่ง prompt/context ที่ผ่าน privacy policy ไปยัง Provider และรับผลลัพธ์กลับมาเป็นข้อมูล
- **Budget Manager:** จำกัด request/token quota และจำนวนงาน AI
- **AI Debate / Review:** ให้ Proposer และ Challenger ตรวจงานตามขอบเขตที่กำหนด ไม่ใช่กลไกอนุมัติ
- **Agent Manager:** สร้าง มอบหมาย จำกัด และยุติ Agent/Sub-Agent
- **Security Core & Executors:** ตรวจ schema, permission, approval, execute, verify และบันทึก audit
- **User Interface & Notifications:** Dashboard, Notification Center, tray และ Discord ในฐานะช่องทางสื่อสาร

### 2.2 Worker และ Runtime

- **Instruction Skill:** ขั้นตอน/ความรู้ที่ AI ใช้เป็นบริบท ไม่มี Python executor และไม่มีสิทธิ์กระทำกับเครื่อง
- **Action Skill:** Python extension ที่ทำงานภายใต้ manifest และ Security Core
- **Agent:** ผู้ปฏิบัติงานตาม task scope และ tool allowlist ที่ MasterControl กำหนด
- **Agent Runtime:** ส่วนที่รัน Agent จริง อาจเป็น runtime ภายในที่มีขอบเขตเล็ก หรือ runtime ภายนอกที่ผ่าน Decision Gate แล้วเท่านั้น
- **The Grid Host:** Windows 11, ไฟล์/folder ที่อนุญาต, application และ telemetry ที่อ่านได้ตาม policy

ไม่มี Worker ใดเชื่อมต่อ executor หรือควบคุมระบบโดยข้าม MasterControl ได้

## 3. Security Core — ข้อบังคับที่ห้ามลดระดับ

ทุก action ที่มีผลต่อไฟล์ การตั้งค่า process หรือระบบ ต้องผ่านขั้นตอนตามลำดับ:

**Validate → Permission Check → Approval (เมื่อจำเป็น) → Controlled Executor → Verify → Audit Log**

กฎบังคับ:

- LLM/Agent/Skill ส่งได้เฉพาะ structured proposal ที่ผ่าน schema validation ไม่ส่ง shell command อิสระให้ระบบรัน
- Core ตรวจ action กับ Skill manifest ที่ติดตั้งและเปิดใช้งานจริง รวมถึง parameter schema และ capability risk floor
- SAFE/LOW ทำงานได้เฉพาะเมื่อผ่าน validation และ permission; MEDIUM/HIGH ต้องมี explicit approval; CRITICAL ปฏิเสธเสมอ
- Approval ต้องผูกกับ action, parameters, risk และผู้ร้องขอที่ตรวจสอบได้ ห้ามใช้ blanket approval หรือสืบทอด approval ข้ามงาน
- Action log ต้องเขียนได้ก่อนเริ่มเรียก Skill code; หากเขียน log ไม่ได้ต้อง fail closed
- หลัง execute ต้อง verify ผลจริง การตอบว่า success จาก Worker อย่างเดียวไม่ถือเป็นหลักฐาน
- ห้ามใช้ shell=True, eval, exec หรือ os.system กับข้อความจากผู้ใช้, LLM, Skill, Agent หรือแหล่งข้อมูลภายนอก
- ห้ามแตะ game/anti-cheat processes; ห้ามควบคุมพัดลม/MSI Center; temperature เป็น read-only
- secrets อยู่ใน .env ที่ gitignore หรือ secret store ที่เหมาะสมเท่านั้น ห้าม commit/log keys หรือ webhook URLs
- หาก validation, permission, approval, verification หรือ audit ทำงานไม่ครบ ให้หยุดและรายงานตามจริง

**ข้อจำกัดปัจจุบัน:** Python Skills ทำงานใน process เดียวกับ MasterControl จึงไม่ใช่ OS sandbox; capability tags เป็น metadata สำหรับ permission ไม่ใช่ isolation ระดับระบบปฏิบัติการ ต้องตรวจ source ก่อน enable และห้ามอ้างว่า Skill ภายนอกปลอดภัยเพียงเพราะ manifest ผ่าน

## 4. Hybrid Skill Architecture

ระบบจะมี Skill สองชนิดที่ใช้ Skill Manager และนโยบายเดียวกัน แต่มีขอบเขตการทำงานต่างกัน

### 4.1 Instruction Skill — Markdown only

โครงสร้างเป้าหมาย:

- มีไฟล์ SKILL.md เป็นหลัก
- อาจมี references/ สำหรับเอกสารประกอบ และ assets/ สำหรับไฟล์อ้างอิงที่จำเป็น
- ใช้บอกความสามารถ เงื่อนไขการเลือกใช้ ขั้นตอน และข้อจำกัดของ Skill
- ไม่มี skill.py, ไม่มี action executor และไม่มี capability ที่ใช้อนุญาตการกระทำ

Instruction Skill ทำหน้าที่ให้บริบทและแนวทางแก่ AI เท่านั้น ไม่สามารถอ่าน/เขียนไฟล์ สั่ง process เรียก network หรืออนุมัติ action ด้วยตัวเอง หากขั้นตอนที่แนะนำต้องทำงานบนเครื่อง ต้องส่งเป็น proposal ไปยัง Action Skill ที่มีอยู่และผ่าน Security Core ตามปกติ

ข้อมูลใน SKILL.md, references และ assets ถือเป็น untrusted input เสมอ เนื้อหาเหล่านี้ไม่มีอำนาจเปลี่ยน system policy, permissions หรือ approval rules

### 4.2 Action Skill — Markdown + Python

โครงสร้างเป้าหมายสำหรับ Skill ใหม่ที่ต้องลงมือทำ:

- SKILL.md: คำอธิบาย วิธีใช้ เงื่อนไข ข้อจำกัด และตัวอย่าง
- skill.toml: manifest และแหล่งข้อมูลจริงเพียงแห่งเดียวสำหรับ action IDs, descriptions, risk, capabilities, parameters และ target paths
- skill.py: implementation ของ run(action_id, params) และ verify(action_id, params, result)
- references/ และ assets/ เป็นส่วนเสริมเมื่อจำเป็น

**skill.toml เป็น authority ด้าน Action และ Permission เท่านั้น** SKILL.md ไม่สามารถเพิ่ม action, capability, risk, target path หรือสิทธิ์ใด ๆ ได้

Skill เดิมที่เป็น Python + skill.toml ไม่จำเป็นต้องถูกเขียนใหม่ทั้งหมดในครั้งเดียว ให้รักษาความเข้ากันได้และทยอยเพิ่ม SKILL.md เมื่อมีการปรับปรุง Skill นั้น

### 4.3 Discovery, Loading และ Invocation

เป้าหมายของ Skill Manager:

1. **Discovery:** ค้นหาเฉพาะโฟลเดอร์ภายใน skills/ และอ่าน metadata ที่จำเป็นเพื่อแสดงรายการ ห้าม import หรือ execute Python เพียงเพราะค้นพบโฟลเดอร์
2. **Validation:** ตรวจชื่อ/version/metadata/manifest และโครงสร้างไฟล์ด้วย schema ที่เข้มงวด; ปฏิเสธ field ที่ไม่รู้จักหรือ path ที่ออกนอกโฟลเดอร์ Skill
3. **Opt-in:** Skill ที่ติดตั้งใหม่ต้อง disabled โดย default; ต้องให้เจ้าของตรวจ source และยืนยันการ enable
4. **Lazy loading:** โหลดเนื้อหา SKILL.md เฉพาะเมื่อผู้ใช้เรียกหรือ Router เลือก Skill ที่เปิดใช้งานแล้ว; โหลด references เฉพาะไฟล์ที่เกี่ยวข้อง
5. **Python loading:** โหลด Action Skill module เฉพาะตอนที่ Core จะเตรียม action ตาม lifecycle ที่กำหนด ไม่ใช่ตอน discovery
6. **Invocation:** รองรับการเรียกด้วยชื่อ Skill โดยตรงก่อน แล้วจึงเพิ่มการเลือกอัตโนมัติด้วย AI ใน Phase 5
7. **Execution:** Instruction Skill ตอบเป็นคำแนะนำเท่านั้น; Action Skill ต้องผ่าน prepare/validate/permission/approval/executor/verify/log ของ Core
8. **Failure:** เมื่อ manifest, reference, module หรือ execution ผิดพลาด ให้ fail closed; แสดง error ที่ตรวจสอบได้และไม่ปล่อยให้ Skill ที่ผิดพลาดค้าง enabled

ชื่อคำสั่งอย่าง /skill-name, skills search, skill info และ skill review เป็น **รูปแบบ UX ที่เสนอ** ยังไม่ใช่คำสั่งที่รับประกันว่ามีใน CLI ปัจจุบัน

### 4.4 Skill Library และการนำเข้า

ลำดับที่แนะนำ:

- เริ่มจาก Local Folder และ ZIP ที่ผู้ใช้นำเข้ามาเอง
- ตรวจ archive path traversal, symlink/reparse point, ขนาดไฟล์, ชื่อซ้ำ และรายการไฟล์ที่อนุญาตก่อนแตกไฟล์
- แสดงผู้สร้าง/แหล่งที่มา/version, ไฟล์ทั้งหมด, manifest, capabilities, risk floor และ target paths ให้ตรวจ
- Imported Skill ต้องอยู่ในสถานะ disabled จนกว่าเจ้าของจะตรวจ source และ enable เอง
- ห้ามติดตั้ง package/dependency หรือรัน setup script อัตโนมัติ
- Git import และ Online Registry เป็นงานระยะหลัง ต้องมี source integrity, version pinning, update review และ supply-chain policy ก่อนเปิดใช้

## 5. AI Intelligence และ Task Routing

### 5.1 ฐานที่มีแล้วและสิ่งที่ยังไม่มี

PR #33 เพิ่มรากฐาน Phase 5 แล้ว ได้แก่ Provider protocol, deterministic MockProvider, configuration-only provider stubs, ProviderRouter, Pydantic ActionProposal, Core-owned proposal submission และการ redact private fields โดย default

ขอบเขตที่ต้องเข้าใจให้ตรงกัน:

- Provider stubs สำหรับ Groq, Gemini และ GitHub Models ยังไม่ใช่ API client และไม่ส่ง network request
- ActionProposal ปัจจุบันจำกัดรูปแบบ action ให้อยู่ใน namespace สำหรับ Action Skill เท่านั้น; ไม่รับ shell command หรือ action นอก manifest; Core ตรวจ enabled Skill manifest และส่งต่อผ่าน executor เดิม
- MEDIUM/HIGH สร้าง approval request; CRITICAL ถูกปฏิเสธ; SAFE/LOW จึงอาจทำงานผ่าน Skill executor หลัง validation/permission
- Privacy redaction ปัจจุบันเป็นการ redact จากชื่อ field ที่รู้จัก ไม่ใช่ระบบตรวจจับข้อมูลส่วนบุคคลได้ครบทุกแบบ
- การมี ProviderRouter หรือ API key ใน environment ไม่ได้แปลว่า Provider นั้นพร้อมใช้งานจริง

รายละเอียด implementation และการทดสอบล่าสุดให้อ่านจาก STATUS.md และ code ปัจจุบันก่อนเริ่มแต่ละ milestone

### 5.2 Provider Layer — เป้าหมายถัดไป

- เริ่มด้วย Provider ที่ใช้ฟรีหรือมี free quota; ตรวจ API, ข้อกำหนด, rate limit และ quota จริง ณ เวลาพัฒนา
- API key ต้องอ่านจาก .env/secret store; ห้ามฝังคีย์ใน source, config ที่ commit หรือ log
- มี timeout, bounded retry, response validation, error classification และ usage record
- Provider ส่งกลับข้อมูลเท่านั้น; ห้ามได้รับ DB handle, executor หรือ method ที่ทำให้สั่งเครื่องได้โดยตรง
- Fallback ต้องตรวจ provider-specific quota และ privacy/consent ใหม่ทุกครั้งก่อนส่ง context ไปยังรายถัดไป
- หากไม่มี Provider ที่พร้อมใช้งาน ให้หยุดงาน AI อย่างปลอดภัย แต่ L0, local alerts และ scheduler ต้องทำงานต่อ

### 5.3 Task Routing L0–L3

| Level | ใช้เมื่อ | วิธีทำงาน |
|---|---|---|
| L0 | กฎหรือโค้ด deterministic ทำงานได้ | ไม่เรียก LLM |
| L1 | ต้องการภาษา/การวิเคราะห์ที่กฎทำไม่ได้ | เรียก Provider หนึ่งครั้งและตรวจ response |
| L2 | งานซับซ้อนที่ได้ประโยชน์จากการตรวจทานอิสระ | Proposer เสนอ และ Challenger ตรวจตามจำนวนรอบที่จำกัด |
| L3 | งานมีผลกระทบหรือ risk สูง | ใช้ deterministic checks, preview และ explicit user approval ตาม Security Core; ไม่เพิ่มอำนาจให้ AI |

Core เป็นผู้เลือก Level จากประเภทงานและ policy; LLM/Agent ห้ามยกระดับตัวเอง หากไม่แน่ใจให้เลือกเส้นทางที่ปลอดภัยกว่าและถามเจ้าของ

### 5.4 AI Debate

- Proposer เสนอคำตอบ/แผน และ Challenger ตรวจข้อผิดพลาด สมมติฐาน และความเสี่ยง
- ใช้คนละ Provider เมื่อ policy และ quota เอื้ออำนวย
- MVP จำกัดหนึ่งรอบ Proposer → Challenger และ revision ได้ไม่เกินหนึ่งครั้ง
- MasterControl เป็นผู้สรุป ไม่เปิด AI Synthesizer หรือ debate loop แบบไม่จำกัดโดย default
- Debate เป็นการตรวจทาน ไม่ใช่การอนุมัติ และไม่สามารถเปลี่ยน Permission หรือข้าม Security Core
- หาก Challenger ไม่พร้อม ต้องรายงานว่า Debate ไม่ครบ; ห้ามแอบใช้ Provider เดียวกันแทนการตรวจอิสระ

### 5.5 Budget Manager

- นับ request และ input/output token ต่อ Provider; แยก actual usage กับ estimate
- มี daily cap, per-task cap, concurrency limit และ hard stop
- จอง quota ก่อนเรียก Provider และ settle usage หลังจบแบบ atomic เพื่อป้องกันงานพร้อมกันใช้เกินงบ
- ทุก Agent/Sub-Agent ใช้ budget กลาง ไม่ได้ quota แยกที่ทำให้รวมแล้วเกิน limit
- ก่อน fallback ต้องตรวจ quota และ privacy policy ของ Provider ปลายทางใหม่
- Emergency Mode พักงาน L1/L2 ที่ไม่อยู่ใน allowlist แต่ไม่หยุด L0 หรือ local alerts
- ตัวเลขสำรอง quota เช่น ใช้งานไม่เกิน 80% และเข้า Emergency Mode เมื่อเหลือ 20% เป็นค่าเริ่มต้นที่เสนอและปรับได้ ไม่ใช่ quota ที่ Provider รับประกัน

## 6. Agent Manager และ Runtime

### 6.1 Agent อยู่ใต้ MasterControl

Agent เป็น worker ตามบทบาท เช่น Doctor, Developer, Researcher, Analyst และ Reviewer ไม่ใช่ผู้มีอำนาจด้านความปลอดภัย

เมื่อมอบหมายงาน MasterControl ต้องกำหนด:

- task และขอบเขตที่ชัดเจน
- context เฉพาะที่จำเป็นและผ่าน privacy policy
- tool/action allowlist
- Provider/budget limit
- timeout, concurrency และเงื่อนไขยกเลิก
- รูปแบบผลลัพธ์ที่ต้องส่งกลับและวิธี verify

Agent ส่ง structured result/proposal กลับมาเท่านั้น Agent ห้าม spawn Agent เอง ห้ามให้ approval แก่ตัวเองหรือ worker อื่น และห้ามถือ blanket permission จากงานก่อนหน้า

### 6.2 Temporary Sub-Agents

- สร้างและควบคุมโดย Agent Manager ของ MasterControl เท่านั้น
- อายุสั้น จำกัด task/context/tools/budget/timeout
- ไม่มีสิทธิ์เกิน Agent แม่ และไม่รับช่วง approval ของ Agent แม่
- จำกัดจำนวนที่ทำงานพร้อมกันตาม CPU/RAM/quota
- เมื่อ timeout, cancel, provider failure หรือ quota หมด ต้องหยุดและบันทึกสถานะจริง

### 6.3 OpenClaw Decision Gate

OpenClaw เป็นตัวเลือก Agent Runtime ไม่ใช่ dependency และไม่ใช่ Security Authority

ก่อน integration ต้อง audit installation/version/config จริง รวมถึง tools, plugins, hooks, shell/filesystem/process/network routes, provider routing, prompt-injection boundary, resource usage, version pinning และ rollback

| Gate | สิ่งที่ต้องพิสูจน์ | เมื่อไม่ผ่าน |
|---|---|---|
| Security Boundary | ไม่มี route ที่ bypass MasterControl ได้ | read-only เท่านั้นหรือไม่ integrate |
| Tool Isolation | จำกัด shell/filesystem/process/network ได้จริง | ปิด tool ที่ควบคุมไม่ได้ |
| Permission & Approval | ทุก action กลับเข้า Security Core | ห้ามเปิด action tools |
| Provider & Privacy | LLM calls ผ่าน Provider/consent policy | ไม่ส่งข้อมูลสำคัญ |
| Reliability | timeout/disconnect/malformed output/cancel ไม่ทำให้สถานะค้าง | คง test mode |
| Resource | ไม่รบกวนเครื่องและเกมตาม baseline ที่วัดจริง | จำกัดหรือไม่ integrate |
| Maintenance | pin/update/audit/test/rollback ดูแลได้จริง | เลือก runtime ที่เล็กกว่า |

ผล Gate เป็น PASS, PARTIAL หรือ FAIL; PARTIAL อนุญาตเฉพาะความสามารถ read-only ที่พิสูจน์แล้ว หาก FAIL ให้ใช้ MasterControl runtime แบบเล็กและจำกัดแทน ไม่ฝืนเชื่อมต่อ

## 7. Unified Roadmap และลำดับพัฒนา

ลำดับนี้เป็นแผนเป้าหมาย ส่วนสถานะปัจจุบันของแต่ละ Phase ต้องอ่านจาก STATUS.md เสมอ

| Milestone | Phase | ขอบเขตและผลลัพธ์ที่ต้องการ |
|---|---|---|
| A — Secure Foundation | 1–4 | รักษา Foundation, Telemetry, Alert Engine และ Python Skill Framework; ปิด Windows verification ที่ค้าง |
| A — Reliability Gate | 4.5 | ยืนยัน diagnostics, action preview, audit, config recovery, approval expiry และ fail-closed paths บนเครื่องเจ้าของ |
| B — Hybrid Skills | 4.6 | เพิ่ม SKILL.md, Instruction Skill, Action Skill แบบ Markdown + TOML + Python, discovery และ lazy loading |
| B — Skill Manager | 4.7 | เพิ่ม search/info/review/invoke UX, dashboard browser และ Local Folder/ZIP import แบบ opt-in |
| C — AI Intelligence | 5 | ต่อยอด Provider groundwork ไปสู่ live provider ที่เลือกใช้ได้, Budget Manager, L0–L3 และ AI Debate |
| D — Agent Orchestration | 6 | Agent Manager, scoped Agent/Sub-Agent และ OpenClaw Decision Gate |
| E — Connected Control | 7 | Discord commands, reports และ approval channel ที่ตรวจ owner identity |
| F — Proactive | 8 | Task Engine, Morning SITREP และ event/rule-based monitoring |
| G — Desktop | 9 | tray, hotkey, overlay, Notification Center, privacy/provider/budget/agent controls และ file intelligence |
| H — Ecosystem | 10 | versioning, compatibility, Skill review/update, backup/recovery และ maintenance |

### 7.1 งานถัดไปตามลำดับ

1. ปิด manual Windows checks ของ Phase 4.5 และรายการ security สำคัญจาก Phase 1–4 ตาม STATUS.md; อย่าใช้ CI แทนการทดสอบบนเครื่องจริง
2. พัฒนา Phase 4.6 เป็น PR ขนาดเล็ก: เริ่มจาก schema/discovery/loader ของ SKILL.md และ tests; ไม่เปลี่ยน Security Core หรือ DB schema โดยไม่มีเหตุผล
3. พัฒนา Phase 4.7 หลัง loader ผ่าน: เพิ่มการค้นหา รายละเอียด review ก่อน enable และ local import
4. ทำ Phase 5 ให้สมบูรณ์ทีละส่วน: provider จริงที่ได้รับอนุญาต → usage/budget → routing → debate; อย่าเปิด provider ทั้งหมดพร้อมกัน
5. เริ่ม Phase 6 เมื่อ Core, Skill boundaries, Provider policy และ resource budget พร้อมแล้วเท่านั้น

### 7.2 Phase Exit Criteria

ทุก Phase ต้องมีอย่างน้อย:

- scope ที่ตรวจสอบได้และไม่ขยายเกิน milestone
- pytest tests สำหรับ success, invalid input, permission denial, approval และ failure paths ตามความเกี่ยวข้อง
- mocks/fake clocks; tests ห้าม hit real network, sleep หรือ kill real processes
- Ruff และ pytest ผ่าน GitHub Actions
- ไม่มีการลด risk floor, approval, opt-in, audit หรือ privacy policy
- STATUS.md ระบุสิ่งที่ CI/mock verified และ owner-Windows verified แยกกัน
- มีขั้นตอน manual verification และข้อจำกัดที่ยังเหลือ
- ไม่มีการอ้างว่า feature ทำงานจริงจาก stub, mock หรือผลการทดสอบที่ไม่ได้รัน

## 8. Resource, Gaming และ Privacy Policy

### Resource & Gaming

- idle: ลด polling และ background work ให้ต่ำที่สุด
- gaming: defer indexing, LLM, Agent และงานหนักที่ไม่จำเป็น; local LLM ปิดโดย default
- non-gaming: จำกัด concurrency ตาม CPU/RAM/GPU budget ที่วัดจริง
- ห้ามตั้งตัวเลขว่า near-zero หรือ lightweight โดยไม่มี baseline และผลวัดบนเครื่องจริง
- ห้ามแตะ game/anti-cheat processes และห้ามควบคุมพัดลม/MSI Center

### Privacy & Prompt Injection

- แบ่งข้อมูลตามระดับ public/personal/sensitive และส่งเฉพาะ context ที่จำเป็น
- เนื้อหาเว็บ/ไฟล์/เอกสาร/Skill เป็นข้อมูลที่ไม่เชื่อถือ ไม่ใช่ system instruction
- ตรวจ consent ก่อนส่งข้อมูลไป Cloud Provider ทุกครั้ง รวมถึงตอน fallback
- redact secrets และ private fields ก่อน logging/provider transmission; การ redact ตามชื่อ field ไม่ใช่การรับประกันว่าไม่มี PII
- Agent ที่อ่าน untrusted content ไม่ควรได้รับ write/control tools โดยไม่จำเป็น
- เก็บ log เท่าที่จำเป็น ไม่บันทึก API keys, webhook URLs หรือเนื้อหาลับ

## 9. สิ่งที่ไม่อยู่ใน MVP

- Community Skill Registry หรือ auto-install Skill จากอินเทอร์เน็ต
- การรัน Python จาก Skill ที่นำเข้าโดยอัตโนมัติ
- Unrestricted shell, filesystem หรือ process control
- Agent spawn Sub-Agent เอง หรือ autonomous loop ที่ไม่มีเพดาน
- AI Debate หลายชั้นหรือไม่จำกัดจำนวนรอบ
- AI Synthesizer ที่เปิดตลอดเวลา
- Local LLM เป็น default หรือทำงานระหว่างเล่นเกม
- File delete/cleanup อัตโนมัติจากการคาดเดา
- Adaptive resource control ก่อนมี telemetry baseline
- OpenClaw integration ก่อนผ่านทุก gate ที่จำเป็น

## 10. Development Workflow

ข้อกำหนดใน AGENTS.md และ STATUS.md มีผลเหนือแผนนี้เสมอ:

1. อ่าน AGENTS.md, STATUS.md และเอกสาร security/Skills ที่เกี่ยวข้องก่อนทุกงาน
2. ก่อนแก้โค้ดให้สรุปแผนและรายชื่อไฟล์; รอ confirm เว้นแต่เจ้าของอนุญาตให้ลงมือทันทีในงานนั้น
3. ทำงานบน feature branch และ PR; ห้าม push ตรงเข้า main
4. แก้เฉพาะไฟล์ใน scope; ไม่ลบไฟล์หรือ refactor ใหญ่โดยไม่มีเหตุผลและอนุมัติ
5. ทุก code milestone มี tests; ใช้ mocks/fake clocks และไม่ hit network จริงใน tests
6. ก่อนเพิ่ม dependency ให้เปรียบเทียบ standard library/ทางเลือกที่เบากว่า
7. รัน Ruff และ pytest; ตรวจ diff, links, claims และผล CI ก่อน merge
8. อัปเดต STATUS.md เมื่อสถานะ implementation เปลี่ยนจริงเท่านั้น
9. รายงานไฟล์ที่เปลี่ยน วิธีทดสอบ วิธีตรวจบน Windows สิ่งที่ยังไม่ทำ และข้อจำกัดตามจริง

**แนวทางสรุป:** ทำให้ MasterControl เป็น Control Plane ที่ปลอดภัยและใช้งานได้ด้วยตัวเองก่อน เพิ่ม Hybrid Skills เพื่อให้ขยายความรู้และความสามารถได้โดยไม่แก้ Core ทุกครั้ง จากนั้นจึงต่อยอด AI และ Agent ภายใต้ Security Core เดิม โดยไม่มี Worker ใดมีอำนาจเหนือเจ้าของเครื่อง