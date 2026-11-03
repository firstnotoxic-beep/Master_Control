# MasterControl — Phase 1 Foundation

โครงสร้างพื้นฐานแบบ Local-first สำหรับ Windows 11 โดยยังไม่มี AI/LLM, Voice หรือ Local AI

## ติดตั้ง

ต้องใช้ Python 3.11 ขึ้นไป

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
copy .env.example .env
```

ถ้าต้องการ Discord ให้เปิด `.env` แล้วใส่ค่า `DISCORD_WEBHOOK_URL` เท่านั้น ห้ามใส่คีย์ในโค้ดหรือ commit ไฟล์ `.env`

## รันและทดสอบ

```bash
pytest
streamlit run app/dashboard.py
```

เปิด URL ที่ Streamlit แสดง แล้วตรวจ CPU/RAM, task list, action log และ Pending Approvals

คำสั่งที่รองรับ:

- `status`
- `help`
- `add task <รายละเอียด>`
- `list tasks`
- `test medium` (สร้างคำขออนุมัติระดับ MEDIUM แบบ stub ไม่ทำคำสั่งจริง)

การทดสอบแจ้งเตือนใช้ Python shell:

```python
from core.notify import send_notification
send_notification("ทดสอบ", "MasterControl notification")
```

Windows toast ใช้ได้บน Windows เท่านั้น หาก Discord ล้มเหลว ระบบจะบันทึก error และไม่ทำให้แอป crash

## สิ่งที่ยังไม่ได้ทำ

- ยังไม่มี AI/LLM, Voice หรือ Local AI
- action ระดับ MEDIUM เป็น stub และยังไม่ปิดโปรเซสจริง
- ยังไม่มีการควบคุมพัดลมหรือโหมด MSI Center

เมื่อใช้งานได้แล้ว ให้ตรวจ diff และสร้าง commit ด้วย `git commit`
