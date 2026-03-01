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

# 1. SETUP PAGE CONFIG (ต้องอยู่บรรทัดแรกสุดของ Streamlit commands)
st.set_page_config(page_title="ขี้ลืมจด V9.4 Private & AI Tags", layout="wide", page_icon="🛡️")

# ปิด Warning เรื่อง SSL สำหรับ Pukchain API
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ──── ⚙️ CONFIGURATION ───────────────────────────────────────
DB_DIR = "data"
DB_NAME = "khiluem_jot_v9_4.db" 
DB_FILE = os.path.join(DB_DIR, DB_NAME)
SUPER_ADMIN_ID = "01-0001" 

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

API_MAIN_URL = "https://puchain.pukmupee.com"
API_LOGIN_URL = f"{API_MAIN_URL}/api/v4/pager/login_secure"

os.makedirs(DB_DIR, exist_ok=True)

# ──── 🚀 SPEED BOOST NOTICE ──────────────────────────
if "speed_notice_shown" not in st.session_state:
    with st.container(border=True):
        st.markdown("""
        <div style='text-align: center;'>
            <h2 style='margin-bottom: 0;'>🚀 พบเวอร์ชันที่เข้าถึงได้ไวกว่า!</h2>
            <p style='color: #666;'>ระบบตรวจพบว่าคุณกำลังรันผ่าน Server สำรอง</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("""
        **เหตุผล:** เนื่องจากแอปนี้ใช้ `import streamlit as st` การรันผ่าน **Streamlit Cloud Server** จะช่วยให้การจัดการ Python Runtime และความเร็วในการเชื่อมต่อ AI มีประสิทธิภาพสูงสุด
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            st.link_button("เปิดเวอร์ชัน Speed Boost ⚡", "https://khiluem-jot.streamlit.app/", 
                           type="primary", use_container_width=True)
        with col2:
            if st.button("ปิดและใช้งานเวอร์ชันนี้ ❌", use_container_width=True):
                st.session_state.speed_notice_shown = True
                st.rerun()
        st.stop() 

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
        # แก้ไข Tuple ตรงนี้โดยเติม , หลัง SUPER_ADMIN_ID
        conn.execute("INSERT OR IGNORE INTO admins (pager_id) VALUES (?)", (SUPER_ADMIN_ID,))

# เรียกใช้งานฐานข้อมูล
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
                    else:
                        st.error("Pager ID หรือ Password ไม่ถูกต้อง")
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
                st.success(f"แต่งตั้ง {target_id} เป็นแอดมินแล้ว")

# --- 📢 ประกาศระบบ ---
    elif st.session_state.active_menu == "📢 ประกาศระบบ":
        st.title("📢 ข่าวสารและประกาศ")
        
        # ส่วนสำหรับ Admin ในการโพสต์ประกาศใหม่
        if is_admin:
            with st.expander("➕ สร้างประกาศใหม่ (เฉพาะแอดมิน)", expanded=False):
                with st.form("news_form", clear_on_submit=True):
                    nt = st.text_input("หัวข้อประกาศ", placeholder="เช่น ปิดปรับปรุงระบบชั่วคราว...")
                    nc = st.text_area("เนื้อหา/รายละเอียด")
                    if st.form_submit_button("📢 โพสต์ประกาศเลย"):
                        if nt.strip() and nc.strip():
                            with get_db_connection() as conn: 
                                conn.execute("INSERT INTO news (title, content) VALUES (?,?)", (nt, nc))
                            st.success("โพสต์ประกาศสำเร็จ!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("กรุณากรอกทั้งหัวข้อและเนื้อหา")

        st.divider()

        # ส่วนแสดงรายการประกาศ (แสดงแค่หัวข้อ อยากอ่านกดกางออก)
        with get_db_connection() as conn: 
            news = pd.read_sql("SELECT * FROM news ORDER BY id DESC", conn)
        
        if news.empty:
            st.caption("ยังไม่มีประกาศในขณะนี้")
        else:
            for _, n in news.iterrows():
                # ใช้ st.expander เพื่อซ่อนเนื้อหา ให้เห็นแค่หัวข้อ (Title)
                with st.expander(f"📌 {n['title']}", expanded=False):
                    st.markdown(f"""
                    <div style="padding: 10px; border-left: 3px solid #4f46e5; background-color: rgba(79, 70, 229, 0.05); border-radius: 5px;">
                        <p style="white-space: pre-wrap;">{n['content']}</p>
                        <hr style="margin: 10px 0; border: 0.5px solid #eee;">
                        <small style="color: gray;">📅 ประกาศเมื่อ: {n['created_at']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # ถ้าเป็นแอดมิน ให้มีปุ่มลบประกาศได้
                    if is_admin:
                        if st.button(f"🗑️ ลบประกาศ #{n['id']}", key=f"del_news_{n['id']}"):
                            with get_db_connection() as conn:
                                conn.execute("DELETE FROM news WHERE id = ?", (n['id'],))
                            st.rerun()

# --- ✍️ บันทึกใหม่ + AI Tags (Smart Version 2026) ---
    elif st.session_state.active_menu == "✍️ บันทึกใหม่":
        st.markdown("<h2 style='text-align: center;'>✍️ จดบันทึกความทรงจำ</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>ใส่ความรู้สึกลงไป แล้วให้ AI ช่วยคัดแยกหมวดหมู่ให้คุณ</p>", unsafe_allow_html=True)

        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            with st.container(border=True):
                # ส่วนหัวแสดงสถานะผู้ใช้งาน
                st.markdown(f"""
                <div style='background: rgba(79, 70, 229, 0.1); padding: 15px; border-radius: 10px; border-left: 5px solid #4f46e5; margin-bottom: 20px;'>
                    <small style='color: #4f46e5; font-weight: bold;'>👤 ผู้บันทึก:</small><br>
                    <strong>{st.session_state.display_name}</strong> (ID: {st.session_state.pager_user})
                </div>
                """, unsafe_allow_html=True)

                with st.form("note_form", clear_on_submit=True):
                    # 1. ช่องกรอกเนื้อหา
                    content = st.text_area(
                        "วันนี้มีเรื่องอะไรน่าจดจำบ้าง...", 
                        height=220, 
                        placeholder="พิมพ์เรื่องราวของคุณที่นี่... (AI จะช่วยสรุปหมวดหมู่ให้เอง)",
                        help="ข้อมูลจะถูกจัดเก็บเข้าสู่ระบบ Pukchain Network"
                    )
                    
                    # 2. ตัวเลือกความเป็นส่วนตัว (Privacy Toggle)
                    col_opt1, col_opt2 = st.columns(2)
                    with col_opt1:
                        is_private = st.toggle("🔒 บันทึกเป็นส่วนตัว", value=False, help="เปิดเพื่อเก็บไว้อ่านคนเดียวในเมนู 'บันทึกส่วนตัว'")
                    
                    with col_opt2:
                        st.caption("✨ AI Smart Tagging Enabled")

                    st.divider()

                    # 3. ปุ่มบันทึก (Primary Button)
                    submit_btn = st.form_submit_button("บันทึกความทรงจำ ✨", use_container_width=True, type="primary")

                    if submit_btn:
                        if content.strip():
                            # สร้างพื้นที่แสดงสถานะ AI
                            status_container = st.empty()
                            with status_container:
                                st.markdown("🤖 **AI กำลังวิเคราะห์เนื้อหา (Llama3/Qwen)...**")
                            
                            # --- 🧠 AI Logic: กระตุ้นให้ฉลาดด้วย System Prompt ---
                            try:
                                # บังคับให้ AI ตอบคำสั้นๆ เพียงคำเดียวที่เป็นคำนาม (Noun)
                                smart_prompt = f"""
                                [Instruction]
                                You are a professional Thai content categorizer. 
                                Analyze the text and provide ONLY ONE single Thai word that represents its main category.
                                NO hashtags, NO periods, NO sentences.
                                
                                Text: "{content}"
                                
                                Category (Thai):"""

                                r = requests.post(
                                    f"{OLLAMA_HOST}/api/generate", 
                                    json={
                                        "model": OLLAMA_MODEL, 
                                        "prompt": smart_prompt, 
                                        "stream": False,
                                        "options": {
                                            "temperature": 0.1,  # ต่ำมากเพื่อให้แม่นยำที่สุด
                                            "top_k": 20,
                                            "stop": ["\n", ".", " ", "#"] # ตัดทันทีถ้า AI เริ่มเพ้อเจ้อ
                                        }
                                    }, 
                                    timeout=10 # เผื่อเวลาให้ PowerEdge T320 หมุน
                                )
                                
                                if r.status_code == 200:
                                    # ทำความสะอาดผลลัพธ์ที่ได้จาก AI อีกครั้ง
                                    tag = r.json().get("response", "ทั่วไป").strip()
                                    tag = tag.split('\n')[0].split(' ')[0].replace("#", "")
                                    if not tag: tag = "ทั่วไป"
                                else:
                                    tag = "ทั่วไป"
                            except Exception as e:
                                # กรณี Ollama มีปัญหา ให้ fallback กลับไปที่ 'ทั่วไป'
                                tag = "ทั่วไป"
                            
                            # --- 💾 Database Logic ---
                            with get_db_connection() as conn:
                                conn.execute(
                                    "INSERT INTO notes (user_id, pager_id, content, tags, is_private) VALUES (?,?,?,?,?)",
                                    (st.session_state.display_name, st.session_state.pager_user, content, tag, 1 if is_private else 0)
                                )
                            
                            # แจ้งเตือนความสำเร็จ
                            status_container.empty()
                            st.balloons()
                            st.toast(f"บันทึกสำเร็จ! หมวดหมู่: #{tag}", icon="✅")
                            time.sleep(1.2)
                            st.rerun()
                        else:
                            st.error("กรุณาพิมพ์เนื้อหาก่อนบันทึกนะครับ")

            # ส่วนท้ายตกแต่ง
            st.markdown(f"""
            <div style='text-align: center; margin-top: 25px; color: #888; font-size: 0.85rem;'>
                💡 <b>Tip:</b> บันทึกนี้จะถูกส่งไปยัง Llama3 บนเซิร์ฟเวอร์ส่วนตัวของคุณเพื่อวิเคราะห์แท็กอัตโนมัติ
            </div>
            """, unsafe_allow_html=True)

  # --- 🔍 คลังความทรงจำ (Public + ค้นหาแท็ก) ---
    elif st.session_state.active_menu == "🔍 คลังความทรงจำ":
        st.title("🔍 คลังความทรงจำสาธารณะ")
        
        # 1. ส่วนการค้นหาและกรอง (Filter & Search Bar)
        with st.container(border=True):
            col_search, col_tag = st.columns([2, 1])
            with col_search:
                search_query = st.text_input("🔍 ค้นหาจากเนื้อหา...", placeholder="พิมพ์คำที่ต้องการค้นหาที่นี่")
            with col_tag:
                with get_db_connection() as conn:
                    all_tags_df = pd.read_sql("SELECT DISTINCT tags FROM notes WHERE is_private = 0", conn)
                    all_tags = all_tags_df['tags'].tolist() if not all_tags_df.empty else []
                selected_tags = st.multiselect("🏷️ แท็กที่สนใจ:", ["ทั้งหมด"] + all_tags, default="ทั้งหมด")
            
            col_limit, col_empty = st.columns([1, 2])
            with col_limit:
                items_per_page = st.selectbox("📄 แสดงหน้าละ:", [10, 20, 50, 100], index=1)

        # 2. สร้าง SQL Query แบบ Dynamic
        base_query = "FROM notes WHERE is_private = 0"
        params = []

        # กรองตามคำค้นหา
        if search_query:
            base_query += " AND content LIKE ?"
            params.append(f"%{search_query}%")

        # กรองตามแท็ก
        if "ทั้งหมด" not in selected_tags and selected_tags:
            placeholders = ','.join(['?'] * len(selected_tags))
            base_query += f" AND tags IN ({placeholders})"
            params.extend(selected_tags)

        # 3. คำนวณการแบ่งหน้า (Pagination)
        with get_db_connection() as conn:
            total_records = pd.read_sql(f"SELECT COUNT(*) as count {base_query}", conn, params=params).iloc[0]['count']
            
            total_pages = (total_records // items_per_page) + (1 if total_records % items_per_page > 0 else 0)
            
            if total_records > 0:
                # ส่วนเลือกหน้า (Pagination Control)
                st.write(f"พบทั้งหมด **{total_records:,}** รายการ")
                page_num = st.number_input(f"หน้า (จาก {total_pages:,})", min_value=1, max_value=total_pages if total_pages > 0 else 1, step=1)
                
                offset = (page_num - 1) * items_per_page
                
                # ดึงข้อมูลเฉพาะหน้านั้นๆ
                final_query = f"SELECT * {base_query} ORDER BY id DESC LIMIT ? OFFSET ?"
                fetch_params = params + [items_per_page, offset]
                notes = pd.read_sql(final_query, conn, params=fetch_params)

                # 4. แสดงผลรายการ (UI)
                st.divider()
                for _, row in notes.iterrows():
                    # สร้าง Card
                    with st.container():
                        st.markdown(f"""
                        <div class="note-card" style="margin-bottom: 5px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span class="tag-badge">#{row['tags']}</span>
                                <small style="color: gray;">ID: {row['id']}</small>
                            </div>
                            <p style="font-size: 1.1rem; margin: 15px 0; line-height: 1.6;">{row['content']}</p>
                            <div style="display: flex; justify-content: space-between; border-top: 1px solid #eee; padding-top: 10px;">
                                <small>👤 <b>{row['user_id']}</b></small>
                                <small>🕒 {row['created_at']}</small>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # ส่วน Admin (ปุ่มลบ)
                        if is_admin:
                            col_del, col_space = st.columns([1, 5])
                            with col_del:
                                if st.button("🗑️ ลบ", key=f"d_pub_{row['id']}", help="เฉพาะแอดมินที่เห็นปุ่มนี้"):
                                    delete_item("notes", row['id'])
                        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
            else:
                st.info("🌙 ไม่พบข้อมูลที่ตรงกับการค้นหาของคุณ")
# --- 🔒 บันทึกส่วนตัว (Private Only) ---
    elif st.session_state.active_menu == "🔒 บันทึกส่วนตัว":
        st.title("🔒 พื้นที่ส่วนตัวของคุณ")
        
        if st.session_state.pager_user == "guest":
            st.warning("Guest Mode ไม่สามารถใช้งานบันทึกส่วนตัวได้")
        else:
            # 1. ดึงหมวดหมู่ (Tags) ทั้งหมดของผู้ใช้คนนี้มาทำ Filter
            with get_db_connection() as conn:
                my_tags_df = pd.read_sql("SELECT DISTINCT tags FROM notes WHERE pager_id = ? AND is_private = 1", 
                                        conn, params=(st.session_state.pager_user,))
                my_tags = my_tags_df['tags'].tolist() if not my_tags_df.empty else []

            # --- ส่วนกรองข้อมูล (Filter Bar) ---
            col_f1, col_f2 = st.columns([2, 1])
            with col_f1:
                selected_tag = st.multiselect("📂 แยกตามหมวดหมู่ (Tags):", ["ทั้งหมด"] + my_tags, default="ทั้งหมด")
            with col_f2:
                items_per_page = st.selectbox("📄 จำนวนต่อหน้า:", [10, 20, 50, 100], index=0)

            # 2. สร้าง Query ตามเงื่อนไขการกรอง
            query = "SELECT * FROM notes WHERE pager_id = ? AND is_private = 1"
            params = [st.session_state.pager_user]
            
            if "ทั้งหมด" not in selected_tag and selected_tag:
                query += f" AND tags IN ({','.join(['?']*len(selected_tag))})"
                params.extend(selected_tag)
            
            # 3. ระบบแบ่งหน้า (Pagination) - สำคัญมากสำหรับหมื่นรายการ
            with get_db_connection() as conn:
                # นับจำนวนรายการทั้งหมดก่อน
                total_count = pd.read_sql(f"SELECT COUNT(*) as cnt FROM ({query})", conn, params=params).iloc[0]['cnt']
                
                total_pages = (total_count // items_per_page) + (1 if total_count % items_per_page > 0 else 0)
                
                # ตัวเลือกหน้าปัจจุบัน
                if total_pages > 1:
                    page_num = st.number_input(f"หน้า (จากทั้งหมด {total_pages} หน้า)", min_value=1, max_value=total_pages, step=1)
                else:
                    page_num = 1
                
                offset = (page_num - 1) * items_per_page
                
                # ดึงข้อมูลเฉพาะส่วนที่ต้องแสดง (LIMIT / OFFSET)
                final_query = query + f" ORDER BY id DESC LIMIT {items_per_page} OFFSET {offset}"
                my_notes = pd.read_sql(final_query, conn, params=params)

            # --- แสดงผลรายการ ---
            st.divider()
            if my_notes.empty: 
                st.info("🌙 ยังไม่มีบันทึกในหมวดนี้")
            else:
                st.caption(f"แสดงรายการที่ {offset+1} - {min(offset+items_per_page, total_count)} จากทั้งหมด {total_count} รายการ")
                
                for _, row in my_notes.iterrows():
                    with st.container():
                        st.markdown(f"""
                        <div class="note-card" style="border-left: 5px solid #ff4b4b; margin-bottom: 0px;">
                            <div style="display: flex; justify-content: space-between;">
                                <span class="private-badge">PRIVATE</span>
                                <span style="font-size: 0.8rem; color: gray;">ID: #{row['id']}</span>
                            </div>
                            <div style="margin-top: 10px;">
                                <span class="tag-badge">#{row['tags']}</span>
                            </div>
                            <p style="font-size: 1.1rem; margin: 15px 0;">{row['content']}</p>
                            <small>🕒 {row['created_at']}</small>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # ปุ่มลบวางไว้ใต้ Card
                        if st.button(f"🗑️ ลบบันทึกนี้", key=f"dp_{row['id']}", use_container_width=False):
                            delete_item("notes", row['id'])
                        st.markdown("<br>", unsafe_allow_html=True)

# --- 💬 กระดานถามตอบ (Forum Style) ---
    elif st.session_state.active_menu == "💬 กระดานถามตอบ":
        st.markdown("<h2 style='text-align: center;'>💬 สภากาแฟ Pukchain</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>พื้นที่สำหรับแลกเปลี่ยนความคิดเห็นและถามตอบปัญหา</p>", unsafe_allow_html=True)

        # 1. ส่วนการตั้งกระทู้/ส่งข้อความ (Post Box)
        with st.container(border=True):
            with st.form("qa_forum", clear_on_submit=True):
                col_input, col_btn = st.columns([4, 1])
                with col_input:
                    txt = st.text_input("", placeholder="ตั้งคำถามหรือพูดคุยอะไรบางอย่าง...", label_visibility="collapsed")
                with col_btn:
                    submit = st.form_submit_button("ส่งกระทู้ 🚀", use_container_width=True, type="primary")
                
                if submit:
                    if txt.strip():
                        with get_db_connection() as conn:
                            conn.execute("INSERT INTO qa (user_id, question) VALUES (?,?)", 
                                       (st.session_state.display_name, txt))
                        st.toast("โพสต์กระทู้เรียบร้อย!", icon="✨")
                        time.sleep(0.5)
                        st.rerun()

        st.divider()

        # 2. ส่วนแสดงรายการกระทู้ (Forum Feed)
        with get_db_connection() as conn:
            qa = pd.read_sql("SELECT * FROM qa ORDER BY id DESC LIMIT 50", conn)

        if qa.empty:
            st.info("🌙 ยังไม่มีการพูดคุยในขณะนี้ เริ่มเป็นคนแรกเลยไหม?")
        else:
            for _, q in qa.iterrows():
                # สุ่มสี Avatar จากชื่อผู้ใช้ (Deterministic Random)
                user_seed = sum(ord(char) for char in q['user_id'])
                colors = ["#FF5733", "#33FF57", "#3357FF", "#F333FF", "#FF33A8", "#33FFF5"]
                avatar_color = colors[user_seed % len(colors)]
                
                # Render Forum Card
                st.markdown(f"""
                <div style="background: {t['card']}; border-radius: 12px; padding: 15px; margin-bottom: 12px; border: 1px solid {t['border']}; box-shadow: 2px 2px 10px {t['shadow']};">
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <div style="width: 35px; height: 35px; background: {avatar_color}; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; margin-right: 12px; font-size: 0.8rem;">
                            {q['user_id'][:2].upper()}
                        </div>
                        <div style="flex-grow: 1;">
                            <div style="display: flex; justify-content: space-between;">
                                <span style="font-weight: 600; color: {t['primary']};">{q['user_id']}</span>
                                <small style="color: gray;">#{q['id']}</small>
                            </div>
                            <small style="color: #999; font-size: 0.7rem;">🕒 {q['created_at']}</small>
                        </div>
                    </div>
                    <div style="padding-left: 47px; font-size: 1rem; line-height: 1.5; color: {t['text']};">
                        {q['question']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # ปุ่มลบสำหรับ Admin (แยกออกมาจาก CSS เพื่อความปลอดภัย)
                if is_admin:
                    col_del, col_empty = st.columns([1, 8])
                    with col_del:
                        if st.button("🗑️ ลบ", key=f"del_qa_{q['id']}", help="ลบกระทู้นี้"):
                            with get_db_connection() as conn:
                                conn.execute("DELETE FROM qa WHERE id = ?", (q['id'],))
                            st.rerun()

st.caption(f"📟 Pukchain V9.4 | Private & AI Enhanced")