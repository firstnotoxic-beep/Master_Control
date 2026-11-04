# Dashboard Streamlit สำหรับดูสถานะ task การอนุมัติ และ action log
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.alerts import AlertEngine, acknowledge_alert, snooze_alert
from core.approval import approve, cancel, pending
from core.commands import handle_command
from core.db import DEFAULT_DB_PATH, fetch_all, init_db
from core.modes import apply_mode, restore_mode
from core.skills import SkillRegistry, execute_approved_skill
from core.telemetry import read_telemetry

init_db(DEFAULT_DB_PATH)
st.set_page_config(page_title="MasterControl", page_icon="🟢", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: #07110b; color: #b6ffb6; }
    h1, h2, h3, label, p { color: #b6ffb6 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("MasterControl")
st.subheader("Telemetry")
refresh = st.checkbox("เปิด telemetry refresh ทุก 5 วินาที", value=False)


def show_telemetry() -> None:
    telemetry = read_telemetry()
    telemetry_cols = st.columns(5)
    telemetry_cols[0].metric("CPU", f"{telemetry['cpu_percent']:.1f}%")
    telemetry_cols[1].metric("RAM", f"{telemetry['ram_used_mb']:.0f}/{telemetry['ram_total_mb']:.0f} MB")
    telemetry_cols[2].metric("GPU", telemetry["gpu_name"] or "N/A")
    telemetry_cols[3].metric("VRAM", f"{telemetry['vram_used_mb']:.0f}/{telemetry['vram_total_mb']:.0f} MB" if telemetry["vram_used_mb"] is not None else "N/A")
    telemetry_cols[4].metric("GPU temp", f"{telemetry['gpu_temperature_c']:.0f} C" if telemetry["gpu_temperature_c"] is not None else "N/A")
    st.dataframe(telemetry["top_processes"])


if refresh and hasattr(st, "fragment"):
    @st.fragment(run_every="5s")
    def live_telemetry() -> None:
        show_telemetry()

    live_telemetry()
elif st.button("อ่าน telemetry ตอนนี้"):
    show_telemetry()

st.subheader("คำสั่ง")
command = st.text_input("พิมพ์คำสั่ง", placeholder="เช่น gaming mode")
if st.button("ส่งคำสั่ง") and command:
    result = handle_command(command, DEFAULT_DB_PATH)
    if result["ok"]:
        st.success(result["message"])
    else:
        st.error(result["message"])

st.subheader("Skills Framework")
skill_registry = SkillRegistry(db_path=DEFAULT_DB_PATH)
st.dataframe(skill_registry.list_skills())
skill_name_input = st.text_input("Skill name to manage", key="skill-name-input")
preview_col, enable_col, disable_col = st.columns(3)
if preview_col.button("Preview permissions") and skill_name_input:
    preview_result = handle_command(f"skill enable {skill_name_input}", DEFAULT_DB_PATH)
    if preview_result["ok"]:
        st.session_state["skill_preview_name"] = skill_name_input
        st.session_state["skill_preview"] = preview_result["preview"]
        st.json(preview_result["preview"])
    else:
        st.error(preview_result["message"])
if enable_col.button("Confirm enable") and skill_name_input:
    if st.session_state.get("skill_preview_name") != skill_name_input:
        st.warning("Preview this Skill first.")
    else:
        enable_result = handle_command(f"skill enable {skill_name_input} confirm", DEFAULT_DB_PATH)
        st.write(enable_result["message"])
        st.rerun()
if disable_col.button("Disable") and skill_name_input:
    disable_result = handle_command(f"skill disable {skill_name_input}", DEFAULT_DB_PATH)
    st.write(disable_result["message"])
    st.rerun()
if "skill_preview" in st.session_state:
    st.json(st.session_state["skill_preview"])
st.dataframe(
    fetch_all(
        "SELECT name, enabled, version, last_error, updated_at FROM skill_state ORDER BY name",
        db_path=DEFAULT_DB_PATH,
    )
)

st.dataframe(
    fetch_all(
        "SELECT name, enabled, version, last_error, updated_at FROM skill_state ORDER BY name",
        db_path=DEFAULT_DB_PATH,
    )
)

st.subheader("Pending Approvals")
for item in pending(DEFAULT_DB_PATH):
    with st.container(border=True):
        st.write(f"#{item['id']} | {item['action']} | {item['details']} | {item['risk_level']}")
        if item["action"] in {"gaming_mode", "focus_mode"}:
            import json

            st.json(json.loads(item["details"]))
        approve_col, cancel_col = st.columns(2)
        if approve_col.button("อนุมัติ", key=f"approve-{item['id']}"):
            approve(item["id"], db_path=DEFAULT_DB_PATH)
            if item["action"] in {"gaming_mode", "focus_mode"}:
                import json

                result = apply_mode(json.loads(item["details"]), DEFAULT_DB_PATH)
                st.session_state["mode_result"] = result
            elif item["action"].startswith("skill."):
                st.session_state["skill_result"] = execute_approved_skill(item["id"], DEFAULT_DB_PATH)
            elif item["action"] == "restore_mode":
                import json

                session_id = json.loads(item["details"])["session_id"]
                st.session_state["restore_result"] = restore_mode(session_id, DEFAULT_DB_PATH)
            st.rerun()
        if cancel_col.button("ยกเลิก", key=f"cancel-{item['id']}"):
            cancel(item["id"], db_path=DEFAULT_DB_PATH)
            st.rerun()

st.subheader("Task list")
st.dataframe(fetch_all("SELECT * FROM tasks ORDER BY id DESC", db_path=DEFAULT_DB_PATH))

st.subheader("Notification Center")
alert_engine = AlertEngine(DEFAULT_DB_PATH)
active_alerts = alert_engine.active_events()
if not active_alerts:
    st.info("ไม่มี alert ที่กำลังรอการจัดการ")
for alert in active_alerts:
    with st.container(border=True):
        st.write(f"#{alert['id']} | {alert['level']} | {alert['title']}")
        st.write(alert["message"])
        ack_col, snooze_col = st.columns(2)
        if ack_col.button("รับทราบ", key=f"alert-ack-{alert['id']}"):
            acknowledge_alert(alert["id"], DEFAULT_DB_PATH)
            st.rerun()
        snooze_minutes = snooze_col.selectbox(
            "เลื่อน",
            [15, 30, 60],
            key=f"alert-snooze-select-{alert['id']}",
        )
        if snooze_col.button("Snooze", key=f"alert-snooze-{alert['id']}"):
            snooze_alert(alert["id"], snooze_minutes, DEFAULT_DB_PATH)
            st.rerun()
st.dataframe(alert_engine.history())

st.subheader("Action Log")
st.dataframe(
    fetch_all("SELECT * FROM action_log ORDER BY id DESC", db_path=DEFAULT_DB_PATH)
)

if "mode_result" in st.session_state:
    st.subheader("Mode result")
    st.dataframe(st.session_state["mode_result"]["results"])
    session_id = st.session_state["mode_result"].get("session_id")
    if session_id and st.button("Restore mode", key=f"restore-{session_id}"):
        result = handle_command(f"restore mode {session_id}", DEFAULT_DB_PATH)
        if result["ok"]:
            st.success(result["message"])
        else:
            st.error(result["message"])
        st.rerun()
if "restore_result" in st.session_state:
    st.subheader("Restore result")
    st.dataframe(st.session_state["restore_result"]["results"])
