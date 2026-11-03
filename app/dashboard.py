# Dashboard Streamlit สำหรับดูสถานะ task การอนุมัติ และ action log
from __future__ import annotations

import sys
from pathlib import Path

import psutil
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.approval import approve, cancel, pending
from core.commands import handle_command
from core.db import DEFAULT_DB_PATH, fetch_all, init_db

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
status_col, memory_col = st.columns(2)
with status_col:
    st.metric("CPU", f"{psutil.cpu_percent(interval=0.1):.1f}%")
with memory_col:
    st.metric("RAM", f"{psutil.virtual_memory().percent:.1f}%")

st.subheader("คำสั่ง")
command = st.text_input("พิมพ์คำสั่ง", placeholder="เช่น add task ส่งฟิสิกส์ พรุ่งนี้")
if st.button("ส่งคำสั่ง") and command:
    result = handle_command(command, DEFAULT_DB_PATH)
    if result["ok"]:
        st.success(result["message"])
    else:
        st.error(result["message"])

st.subheader("Pending Approvals")
for item in pending(DEFAULT_DB_PATH):
    with st.container(border=True):
        st.write(f"#{item['id']} | {item['action']} | {item['details']} | {item['risk_level']}")
        approve_col, cancel_col = st.columns(2)
        if approve_col.button("อนุมัติ", key=f"approve-{item['id']}"):
            approve(item["id"], db_path=DEFAULT_DB_PATH)
            st.rerun()
        if cancel_col.button("ยกเลิก", key=f"cancel-{item['id']}"):
            cancel(item["id"], db_path=DEFAULT_DB_PATH)
            st.rerun()

st.subheader("Task list")
st.dataframe(fetch_all("SELECT * FROM tasks ORDER BY id DESC", db_path=DEFAULT_DB_PATH))

st.subheader("Action Log")
st.dataframe(
    fetch_all("SELECT * FROM action_log ORDER BY id DESC", db_path=DEFAULT_DB_PATH)
)
