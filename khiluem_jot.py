import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
import requests
import json
import time
import random
import urllib3

# ปิด Warning เรื่อง SSL สำหรับ Pukchain API
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ──── ⚙️ CONFIGURATION ───────────────────────────────────────
DB_DIR = "data"
DB_NAME = "khiluem_jot_v9_4.db" # อัปเกรดเวอร์ชันฐานข้อมูล
DB_FILE = os.path.join(DB_DIR, DB_NAME)
SUPER_ADMIN_ID = "01-0001" 

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

API_MAIN_URL = "https://puchain.pukmupee.com"
API_LOGIN_URL = f"{API_MAIN_URL}/api/v4/pager/login_secure"

os.makedirs(DB_DIR, exist_ok=True)

# ──── 🛠️ DATABASE FUNCTIONS ──────────────────────────────────
def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute('''CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id TEXT, 
            pager_id TEXT,
            content TEXT, 
            tags TEXT, 
            is_private INTEGER DEFAULT 0, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS qa (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, question TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS admins (
            pager_id TEXT PRIMARY KEY, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.execute("INSERT OR IGNORE INTO admins (pager_id) VALUES (?)", (SUPER_ADMIN_ID,))
init_db()

def is_user_admin(pager_id):
    if not pager_id: return False
    if pager_id == SUPER_ADMIN_ID: return True
    with get_db_connection() as conn:
        res = conn.execute("SELECT 1 FROM admins WHERE pager_id = ?", (pager_id,)).fetchone()
    return True if res else False

def delete_item(table, item_id):
    with get_db_connection() as conn:
        conn.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
    st.rerun()

# ──── 🎨 THEME DEFINITION ──────────────────────────────────
themes = {
    "Clean White 🤍": {"bg": "#f8f9fa", "card": "#ffffff", "text": "#212529", "primary": "#4f46e5", "accent": "#f1c40f", "border": "#dee2e6", "shadow": "rgba(0, 0, 0, 0.05)"},
    "Cute Pink 🌸": {"bg": "#fff5f7", "card": "#ffffff", "text": "#4a4a4a", "primary": "#ff85a1", "accent": "#ff9f43", "border": "#ffe3e9", "shadow": "rgba(255, 133, 161, 0.2)"},
    "Dark Cyber 🦾": {"bg": "#0d001a", "card": "#1e0033", "text": "#e0e0e0", "primary": "#ff79c6", "accent": "#00f0ff", "border": "#3d0066", "shadow": "rgba(0, 240, 255, 0.1)"}
}

st.set_page_config(page_title="ขี้ลืมจด V9.4 Private & AI Tags", layout="wide", page_icon="🛡️")

if "pager_user" not in st.session_state: st.session_state.pager_user = None
if "puk_balance" not in st.session_state: st.session_state.puk_balance = 0
if "display_name" not in st.session_state: st.session_state.display_name = ""
if "tos_agreed" not in st.session_state: st.session_state.tos_agreed = False
if "current_theme" not in st.session_state: st.session_state.current_theme = "Clean White 🤍"
if "active_menu" not in st.session_state: st.session_state.active_menu = "✍️ บันทึกใหม่"

t = themes[st.session_state.current_theme]
is_admin = is_user_admin(st.session_state.pager_user)
is_super_admin = st.session_state.pager_user == SUPER_ADMIN_ID

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600&display=swap');
    * {{ font-family: 'Kanit', sans-serif; }}
    .stApp {{ background-color: {t['bg']}; color: {t['text']}; }}
    .note-card {{ background: {t['card']}; border-radius: 15px; padding: 1.5rem; margin: 1rem 0; border: 1px solid {t['border']}; box-shadow: 0 5px 15px {t['shadow']}; }}
    .tag-badge {{ background: {t['primary']}20; color: {t['primary']}; padding: 3px 10px; border-radius: 50px; font-size: 0.8rem; font-weight: bold; border: 1px solid {t['primary']}; margin-right: 5px; cursor: pointer; }}
    .puk-balance {{ background: linear-gradient(135deg, #f1c40f, #f39c12); color: white; padding: 10px 20px; border-radius: 12px; font-weight: bold; text-align: center; margin-bottom: 10px; }}
    .private-badge {{ background: #ff4b4b20; color: #ff4b4b; padding: 2px 8px; border-radius: 5px; font-size: 0.7rem; font-weight: bold; border: 1px solid #ff4b4b; }}
</style>
""", unsafe_allow_html=True)

# ──── 🚀 APP FLOW ─────────────────────────────────────────────

if not st.session_state.pager_user:
    st.markdown("<h1 style='text-align:center;'>📜 ขี้ลืมจด@PUK-Chain V9.4</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        with st.container(border=True):
            p_id = st.text_input("Pager ID")
            p_pw = st.text_input("Password", type="password")
            if st.button("เข้าสู่ระบบ ⚡", use_container_width=True, type="primary"):
                try:
                    r = requests.post(API_LOGIN_URL, json={"pager_id": p_id, "password": p_pw}, timeout=7, verify=False)
                    if r.status_code == 200:
                        data = r.json()
                        st.session_state.update({"pager_user": data['pager_id'], "display_name": data['pager_id'], "puk_balance": data['balance']})
                        st.rerun()
                except: st.error("การเชื่อมต่อล้มเหลว")
            
            if st.button("GUEST MODE (ใช้งานแบบทั่วไป)", use_container_width=True):
                random_guest_id = f"Guest_{random.randint(1000, 9999)}"
                st.session_state.update({"pager_user": "guest", "display_name": random_guest_id, "puk_balance": 0})
                st.rerun()

elif not st.session_state.tos_agreed:
    st.markdown(f"<div style='text-align:center; margin-top:30px;'><h2>📜 ข้อตกลงแห่งพุกเชน V9.4</h2></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.form("tos_and_name_form"):
            st.markdown("ระเบียบปฏิบัติ: สื่อสารสร้างสรรค์ ให้เกียรติซึ่งกันและกัน และรับผิดชอบต่อข้อมูลสาธารณะ")
            new_name = st.text_input("ชื่อเรียกขาน:", value=st.session_state.display_name)
            if st.form_submit_button("ยอมรับและเริ่มจดบันทึก 🚀", use_container_width=True):
                if new_name.strip():
                    st.session_state.update({"display_name": new_name, "tos_agreed": True})
                    st.rerun()

else:
    with st.sidebar:
        st.markdown(f"<div class='puk-balance'>🪙 {st.session_state.puk_balance} PUK</div>", unsafe_allow_html=True)
        st.markdown(f"**👤 ชื่อ:** {st.session_state.display_name}")
        st.caption(f"ID: {st.session_state.pager_user}")
        st.divider()
        
        menu_options = ["📢 ประกาศระบบ", "✍️ บันทึกใหม่", "🔍 คลังความทรงจำ", "🔒 บันทึกส่วนตัว", "💬 กระดานถามตอบ"]
        if is_super_admin: menu_options.append("🛡️ จัดการสิทธิ์")
        
        st.session_state.active_menu = st.radio("เมนูหลัก", menu_options)
        st.divider()
        st.session_state.current_theme = st.selectbox("🎨 ธีม", list(themes.keys()), index=list(themes.keys()).index(st.session_state.current_theme))
        if st.button("Logout 🚪", use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

    # --- 🛡️ จัดการสิทธิ์ ---
    if st.session_state.active_menu == "🛡️ จัดการสิทธิ์":
        st.title("🛡️ จัดการสภาแอดมิน")
        if is_super_admin:
            target_id = st.text_input("Pager ID มอบสิทธิ์")
            if st.button("แต่งตั้ง"):
                with get_db_connection() as conn:
                    conn.execute("INSERT OR IGNORE INTO admins (pager_id) VALUES (?)", (target_id,))
                st.rerun()

    # --- 📢 ประกาศระบบ ---
    elif st.session_state.active_menu == "📢 ประกาศระบบ":
        st.title("📢 ข่าวสาร")
        if is_admin:
            with st.form("news_form"):
                nt, nc = st.text_input("หัวข้อ"), st.text_area("เนื้อหา")
                if st.form_submit_button("โพสต์ประกาศ"):
                    with get_db_connection() as conn: conn.execute("INSERT INTO news (title, content) VALUES (?,?)", (nt, nc))
                    st.rerun()
        with get_db_connection() as conn: news = pd.read_sql("SELECT * FROM news ORDER BY id DESC", conn)
        for _, n in news.iterrows():
            st.info(f"**{n['title']}**\n\n{n['content']}")

    # --- ✍️ บันทึกใหม่ + AI Tags ---
    elif st.session_state.active_menu == "✍️ บันทึกใหม่":
        st.title("✍️ บันทึกใหม่ (AI Auto-Tag)")
        with st.form("note_form", clear_on_submit=True):
            content = st.text_area("จดอะไรดี...", height=150)
            is_p = st.checkbox("🔒 บันทึกเป็นส่วนตัว (เห็นเฉพาะคุณ)", value=False)
            if st.form_submit_button("บันทึก ✨"):
                if content.strip():
                    # AI เจนแท็คอัตโนมัติ
                    try:
                        prompt = f"Categorize this text into ONE short Thai word (e.g. อาหาร, งาน, ทั่วไป, บ่น): {content}"
                        r = requests.post(f"{OLLAMA_HOST}/api/generate", 
                                         json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}, timeout=3)
                        tag = r.json().get("response", "ทั่วไป").strip().replace(".", "")
                    except: tag = "ทั่วไป"
                    
                    with get_db_connection() as conn:
                        conn.execute("INSERT INTO notes (user_id, pager_id, content, tags, is_private) VALUES (?,?,?,?,?)",
                                   (st.session_state.display_name, st.session_state.pager_user, content, tag, 1 if is_p else 0))
                    st.success(f"บันทึกแล้ว! AI จัดหมวดหมู่เป็น: #{tag}")
                    time.sleep(1)
                    st.rerun()

    # --- 🔍 คลังความทรงจำ (Public + ค้นหาแท็ก) ---
    elif st.session_state.active_menu == "🔍 คลังความทรงจำ":
        st.title("🔍 คลังความทรงจำสาธารณะ")
        with get_db_connection() as conn:
            all_tags = pd.read_sql("SELECT DISTINCT tags FROM notes WHERE is_private = 0", conn)['tags'].tolist()
        
        search_tag = st.multiselect("🏷️ กรองตามแท็กที่ AI เจนให้:", ["ทั้งหมด"] + all_tags, default="ทั้งหมด")
        
        query = "SELECT * FROM notes WHERE is_private = 0"
        if "ทั้งหมด" not in search_tag and search_tag:
            query += f" AND tags IN ({','.join(['?']*len(search_tag))})"
            params = search_tag
        else: params = []
        
        with get_db_connection() as conn:
            notes = pd.read_sql(query + " ORDER BY id DESC", conn, params=params)
        
        for _, row in notes.iterrows():
            st.markdown(f"""<div class="note-card"><span class="tag-badge">#{row['tags']}</span>
                <p>{row['content']}</p><small>👤 {row['user_id']} | 🕒 {row['created_at']}</small></div>""", unsafe_allow_html=True)
            if is_admin: 
                if st.button("🗑️", key=f"d_{row['id']}"): delete_item("notes", row['id'])

    # --- 🔒 บันทึกส่วนตัว (Private Only) ---
    elif st.session_state.active_menu == "🔒 บันทึกส่วนตัว":
        st.title("🔒 พื้นที่ส่วนตัวของคุณ")
        if st.session_state.pager_user == "guest":
            st.warning("Guest Mode ไม่สามารถใช้งานบันทึกส่วนตัวได้")
        else:
            with get_db_connection() as conn:
                my_notes = pd.read_sql("SELECT * FROM notes WHERE pager_id = ? AND is_private = 1 ORDER BY id DESC", 
                                      conn, params=(st.session_state.pager_user,))
            if my_notes.empty: st.caption("ยังไม่มีบันทึกส่วนตัว")
            for _, row in my_notes.iterrows():
                st.markdown(f"""<div class="note-card" style="border-left: 5px solid #ff4b4b;">
                    <span class="private-badge">PRIVATE</span> <span class="tag-badge">#{row['tags']}</span>
                    <p>{row['content']}</p><small>🕒 {row['created_at']}</small></div>""", unsafe_allow_html=True)
                if st.button("🗑️ ลบส่วนตัว", key=f"dp_{row['id']}"): delete_item("notes", row['id'])

    # --- 💬 กระดานถามตอบ ---
    elif st.session_state.active_menu == "💬 กระดานถามตอบ":
        st.title("💬 กระดานถามตอบ")
        with st.form("qa"):
            txt = st.text_input("พิมพ์ข้อความ...")
            if st.form_submit_button("ส่ง"):
                with get_db_connection() as conn: conn.execute("INSERT INTO qa (user_id, question) VALUES (?,?)", (st.session_state.display_name, txt))
                st.rerun()
        with get_db_connection() as conn: qa = pd.read_sql("SELECT * FROM qa ORDER BY id DESC LIMIT 30", conn)
        for _, q in qa.iterrows():
            st.chat_message("user").write(f"**{q['user_id']}**: {q['question']}")

st.caption(f"📟 Pukchain V9.4 | Private & AI Enhanced")