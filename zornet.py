import streamlit as st
import sqlite3
import datetime
import os
import pytz
import json
import requests
import feedparser
from PIL import Image
from pathlib import Path
import mimetypes
import uuid
import re
import hashlib
import streamlit.components.v1 as components

# ================= ПЕРСИСТЕНТНОЕ ХРАНЕНИЕ =================
def load_storage():
    """Загружает данные из файла"""
    storage_file = Path("zornet_storage.json")
    if storage_file.exists():
        try:
            with open(storage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_storage(data):
    """Сохраняет данные в файл"""
    storage_file = Path("zornet_storage.json")
    with open(storage_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_quick_links(links):
    """Сохраняет быстрые ссылки для текущего пользователя"""
    storage = load_storage()
    if st.session_state.is_logged_in:
        username = st.session_state.user_data.get("username")
        if username:
            if "users" not in storage:
                storage["users"] = {}
            if username not in storage["users"]:
                storage["users"][username] = {}
            storage["users"][username]["quick_links"] = links
            save_storage(storage)

def load_quick_links():
    """Загружает быстрые ссылки для текущего пользователя"""
    if st.session_state.is_logged_in:
        username = st.session_state.user_data.get("username")
        if username:
            storage = load_storage()
            user_links = storage.get("users", {}).get(username, {}).get("quick_links")
            if user_links:
                return user_links
    return None

# ================= НАСТРОЙКИ =================
st.set_page_config(
    page_title="ZORNET",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= СЕССИЯ =================
if "page" not in st.session_state:
    st.session_state.page = "Главная"
if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = []
if "weather_data" not in st.session_state:
    st.session_state.weather_data = None
if "user_city" not in st.session_state:
    st.session_state.user_city = None
if "rooms" not in st.session_state:
    st.session_state.rooms = []
if "music_rooms" not in st.session_state:
    st.session_state.music_rooms = []
if "watch_room" not in st.session_state:
    st.session_state.watch_room = None
if "current_music_room" not in st.session_state:
    st.session_state.current_music_room = None
if "user_data" not in st.session_state:
    st.session_state.user_data = {}
if "user_photo" not in st.session_state:
    st.session_state.user_photo = None
if "disk_current_path" not in st.session_state:
    st.session_state.disk_current_path = "zornet_cloud"
if "disk_action" not in st.session_state:
    st.session_state.disk_action = "view"
if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
if "messages" not in st.session_state:
    st.session_state.messages = {}
if "chat_partner" not in st.session_state:
    st.session_state.chat_partner = None
if "room_messages" not in st.session_state:
    st.session_state.room_messages = {}
# Загружаем состояние входа, если есть
storage = load_storage()
if "current_auth" in storage and storage["current_auth"]["is_logged_in"]:
    st.session_state.is_logged_in = True
    st.session_state.user_data = storage["current_auth"]["user_data"]
if "quick_links" not in st.session_state:
    # Загружаем сохраненные ссылки, если пользователь авторизован
    if st.session_state.is_logged_in:
        saved_links = load_quick_links()
        if saved_links:
            st.session_state.quick_links = saved_links
        else:
            # Если нет сохраненных, используем стандартные
            st.session_state.quick_links = [
                {"name": "YouTube", "url": "https://www.youtube.com", "icon": "📺"},
                {"name": "Gmail", "url": "https://mail.google.com", "icon": "📧"},
            ]
    else:
        # Для неавторизованных пользователей - стандартные ссылки
        st.session_state.quick_links = [
            {"name": "YouTube", "url": "https://www.youtube.com", "icon": "📺"},
            {"name": "Gmail", "url": "https://mail.google.com", "icon": "📧"},
        ]

if "show_add_link" not in st.session_state:
    st.session_state.show_add_link = False
if "registration_success" not in st.session_state:
    st.session_state.registration_success = False
if "registration_message" not in st.session_state:
    st.session_state.registration_message = ""
if "new_user_email" not in st.session_state:
    st.session_state.new_user_email = ""
if "new_user_username" not in st.session_state:
    st.session_state.new_user_username = ""

# ================= ОБНОВЛЕННЫЕ CSS СТИЛИ =================
st.markdown("""
<style>
    /* ОСНОВНЫЕ СТИЛИ */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* ГЛАВНЫЙ ЗАГОЛОВОК */
    .gold-title {
        font-size: 5rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(135deg, #C5A028 0%, #F5E6B3 50%, #C5A028 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -2px;
        margin: 20px 0 40px 0;
        text-shadow: 0 10px 30px rgba(197, 160, 40, 0.2);
        animation: titleGlow 3s ease-in-out infinite;
    }
    
    @keyframes titleGlow {
        0%, 100% { filter: drop-shadow(0 0 20px rgba(197, 160, 40, 0.3)); }
        50% { filter: drop-shadow(0 0 40px rgba(197, 160, 40, 0.5)); }
    }
    
    /* СТИЛИ ДЛЯ КНОПОК НАВИГАЦИИ */
    div[data-testid="stSidebar"] div.stButton > button {
        background: transparent !important;
        border: none !important;
        border-radius: 12px !important;
        color: #1a1a1a !important;
        padding: 12px 16px !important;
        font-weight: 500 !important;
        text-align: left !important;
        transition: all 0.3s ease !important;
        margin: 2px 0 !important;
    }
    
    div[data-testid="stSidebar"] div.stButton > button:hover {
        background: linear-gradient(135deg, rgba(197, 160, 40, 0.1) 0%, rgba(197, 160, 40, 0.2) 100%) !important;
        transform: translateX(5px);
    }
    
    /* КАРТОЧКИ БЫСТРЫХ ССЫЛОК */
    .link-card {
        background: white;
        border-radius: 24px;
        padding: 25px 20px;
        margin: 10px 0;
        border: 1px solid rgba(197, 160, 40, 0.2);
        text-align: center;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        position: relative;
        overflow: hidden;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
    }
    
    .link-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #C5A028, #F5E6B3, #C5A028);
        transform: translateX(-100%);
        transition: transform 0.6s ease;
    }
    
    .link-card:hover {
        transform: translateY(-8px) scale(1.02);
        border-color: #C5A028;
        box-shadow: 0 20px 40px rgba(197, 160, 40, 0.15);
    }
    
    .link-card:hover::before {
        transform: translateX(100%);
    }
    
    .link-icon {
        font-size: 3.5rem;
        margin-bottom: 15px;
        display: inline-block;
        transition: transform 0.3s ease;
    }
    
    .link-card:hover .link-icon {
        transform: scale(1.1) rotate(5deg);
    }
    
    .link-name {
        font-weight: 700;
        font-size: 1.1rem;
        color: #1a1a1a;
        margin-bottom: 8px;
    }
    
    .link-url {
        font-size: 0.8rem;
        color: #666;
        word-break: break-all;
        background: #f8f9fa;
        padding: 5px 10px;
        border-radius: 20px;
        display: inline-block;
        max-width: 100%;
    }
    
    /* КНОПКА УДАЛЕНИЯ */
    .delete-btn {
        position: absolute !important;
        top: 10px !important;
        right: 10px !important;
        width: 28px !important;
        height: 28px !important;
        min-width: 28px !important;
        padding: 0 !important;
        border-radius: 50% !important;
        background: white !important;
        border: 1px solid #ff4444 !important;
        color: #ff4444 !important;
        font-size: 18px !important;
        font-weight: bold !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        opacity: 0;
        transition: all 0.3s ease !important;
        z-index: 10;
        box-shadow: 0 2px 10px rgba(255, 68, 68, 0.2);
    }
    
    .link-card:hover .delete-btn {
        opacity: 1;
    }
    
    .delete-btn:hover {
        background: #ff4444 !important;
        color: white !important;
        transform: scale(1.1);
    }
    
    /* КНОПКА "ОТКРЫТЬ" */
    .open-link-btn {
        background: linear-gradient(135deg, #C5A028, #B38F1A) !important;
        color: white !important;
        border: none !important;
        border-radius: 30px !important;
        padding: 10px 20px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        transition: all 0.3s ease !important;
        margin-top: 15px !important;
        width: 100% !important;
        box-shadow: 0 4px 15px rgba(197, 160, 40, 0.3) !important;
    }
    
    .open-link-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(197, 160, 40, 0.4) !important;
    }
    
    /* КАРТОЧКИ ПОГОДЫ */
    .weather-main-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 30px;
        padding: 30px;
        color: white;
        box-shadow: 0 20px 40px rgba(102, 126, 234, 0.3);
    }
    
    .weather-temp {
        font-size: 5rem;
        font-weight: 800;
        line-height: 1;
    }
    
    .weather-icon {
        font-size: 5rem;
        filter: drop-shadow(0 10px 20px rgba(0,0,0,0.2));
    }
    
    .weather-detail-item {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 15px;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* КАРТОЧКИ НОВОСТЕЙ */
    .news-card {
        background: white;
        border-radius: 20px;
        padding: 25px;
        margin-bottom: 20px;
        border: 1px solid rgba(197, 160, 40, 0.1);
        transition: all 0.3s ease;
        box-shadow: 0 5px 20px rgba(0,0,0,0.03);
    }
    
    .news-card:hover {
        transform: translateY(-5px);
        border-color: #C5A028;
        box-shadow: 0 15px 30px rgba(197, 160, 40, 0.1);
    }
    
    .news-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 15px;
        line-height: 1.4;
    }
    
    .news-summary {
        color: #666;
        line-height: 1.6;
    }
    
    /* ЧАТ МЕССЕНДЖЕРА */
    .chat-container {
        background: white;
        border-radius: 30px;
        overflow: hidden;
        box-shadow: 0 20px 40px rgba(0,0,0,0.08);
        border: 1px solid rgba(197, 160, 40, 0.1);
    }
    
    .contact-item {
        padding: 15px 20px;
        border-bottom: 1px solid #f0f0f0;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .contact-item:hover {
        background: linear-gradient(135deg, rgba(197, 160, 40, 0.05), rgba(197, 160, 40, 0.1));
        padding-left: 25px;
    }
    
    .contact-item.active {
        background: linear-gradient(135deg, rgba(197, 160, 40, 0.1), rgba(197, 160, 40, 0.15));
        border-left: 4px solid #C5A028;
    }
    
    .contact-avatar {
        width: 45px;
        height: 45px;
        border-radius: 15px;
        background: linear-gradient(135deg, #C5A028, #B38F1A);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 700;
        font-size: 1.2rem;
    }
    
    .message-bubble {
        max-width: 70%;
        padding: 12px 18px;
        border-radius: 20px;
        margin-bottom: 10px;
        position: relative;
        animation: messageAppear 0.3s ease;
    }
    
    @keyframes messageAppear {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .message-bubble.you {
        background: linear-gradient(135deg, #C5A028, #B38F1A);
        color: white;
        margin-left: auto;
        border-bottom-right-radius: 4px;
    }
    
    .message-bubble.other {
        background: #f0f2f5;
        color: #1a1a1a;
        margin-right: auto;
        border-bottom-left-radius: 4px;
    }
    
    .message-time {
        font-size: 0.7rem;
        opacity: 0.7;
        margin-top: 4px;
    }
    
    /* ДИСК */
    .disk-stats-card {
        background: linear-gradient(135deg, #C5A028, #B38F1A);
        border-radius: 20px;
        padding: 25px;
        color: white;
        margin-bottom: 20px;
    }
    
    .file-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 15px;
        margin-top: 20px;
    }
    
    .file-item {
        background: white;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        border: 1px solid rgba(197, 160, 40, 0.1);
        transition: all 0.3s ease;
    }
    
    .file-item:hover {
        transform: translateY(-5px);
        border-color: #C5A028;
        box-shadow: 0 10px 25px rgba(197, 160, 40, 0.15);
    }
    
    .file-icon {
        font-size: 3rem;
        margin-bottom: 10px;
    }
    
    /* ПРОФИЛЬ */
    .profile-card {
        background: white;
        border-radius: 30px;
        padding: 40px;
        text-align: center;
        box-shadow: 0 30px 60px rgba(0,0,0,0.1);
        border: 1px solid rgba(197, 160, 40, 0.2);
        max-width: 500px;
        margin: 0 auto;
    }
    
    .profile-avatar {
        width: 120px;
        height: 120px;
        border-radius: 30px;
        background: linear-gradient(135deg, #C5A028, #B38F1A);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 3rem;
        font-weight: 700;
        margin: 0 auto 20px;
        border: 4px solid white;
        box-shadow: 0 10px 30px rgba(197, 160, 40, 0.3);
    }
    
    .profile-name {
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 5px;
        background: linear-gradient(135deg, #C5A028, #B38F1A);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .profile-username {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 20px;
    }
    
    .profile-email {
        background: #f8f9fa;
        padding: 12px 20px;
        border-radius: 50px;
        display: inline-block;
        color: #333;
        font-weight: 500;
    }
    
    /* ФОРМЫ ВХОДА/РЕГИСТРАЦИИ */
    .auth-container {
        max-width: 450px;
        margin: 0 auto;
        background: white;
        border-radius: 30px;
        padding: 40px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.08);
        border: 1px solid rgba(197, 160, 40, 0.2);
    }
    
    .auth-tabs {
        display: flex;
        gap: 10px;
        margin-bottom: 30px;
    }
    
    .auth-tab {
        flex: 1;
        padding: 12px;
        text-align: center;
        font-weight: 600;
        border-radius: 15px;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .auth-tab.active {
        background: linear-gradient(135deg, #C5A028, #B38F1A);
        color: white;
    }
    
    /* КИНОТЕАТР */
    .room-card {
        background: white;
        border-radius: 20px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid rgba(197, 160, 40, 0.1);
        transition: all 0.3s ease;
    }
    
    .room-card:hover {
        transform: translateY(-5px);
        border-color: #C5A028;
        box-shadow: 0 15px 30px rgba(197, 160, 40, 0.1);
    }
    
    .room-name {
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 10px;
        color: #1a1a1a;
    }
    
    .room-meta {
        color: #666;
        font-size: 0.9rem;
        margin-bottom: 5px;
    }
    
    /* КНОПКИ */
    .stButton > button {
        border-radius: 16px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        border: none !important;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #C5A028, #B38F1A) !important;
        color: white !important;
        box-shadow: 0 8px 20px rgba(197, 160, 40, 0.3) !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 30px rgba(197, 160, 40, 0.4) !important;
    }
    
    /* ИНПУТЫ */
    .stTextInput > div > div > input {
        border-radius: 16px !important;
        border: 2px solid #e0e0e0 !important;
        padding: 12px 20px !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #C5A028 !important;
        box-shadow: 0 0 0 4px rgba(197, 160, 40, 0.1) !important;
    }
    
    /* РАЗДЕЛИТЕЛИ */
    hr {
        margin: 30px 0 !important;
        border: none !important;
        height: 2px !important;
        background: linear-gradient(90deg, transparent, #C5A028, transparent) !important;
    }
    
    /* АНИМАЦИИ */
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .fade-in {
        animation: fadeIn 0.5s ease;
    }
</style>
""", unsafe_allow_html=True)

# ================= БАЗА ДАННЫХ =================
def init_db():
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    # Пользователи
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Сообщения мессенджера
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_username TEXT NOT NULL,
            receiver_username TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Комнаты совместного просмотра
    c.execute("""
        CREATE TABLE IF NOT EXISTS watch_rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            youtube_url TEXT NOT NULL,
            password TEXT NOT NULL,
            owner_username TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Сообщения в комнатах
    c.execute("""
        CREATE TABLE IF NOT EXISTS room_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL,
            username TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def register_user(email, username, first_name, last_name, password):
    """Регистрация пользователя"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    try:
        # Проверяем почту
        c.execute("SELECT email FROM users WHERE LOWER(email) = LOWER(?)", (email,))
        if c.fetchone():
            return {"success": False, "message": "Email уже используется"}
        
        # Проверяем никнейм (без учета регистра)
        c.execute("SELECT username FROM users WHERE LOWER(username) = LOWER(?)", (username,))
        if c.fetchone():
            return {"success": False, "message": "Никнейм уже занят"}
        
        # Проверяем длину пароля
        if len(password) < 6:
            return {"success": False, "message": "Пароль должен быть не менее 6 символов"}
        
        # Проверяем валидность email
        if '@' not in email or '.' not in email:
            return {"success": False, "message": "Неверный формат email"}
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        c.execute("""
            INSERT INTO users (email, username, first_name, last_name, password_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (email.strip(), username.strip(), first_name.strip(), 
              last_name.strip() if last_name else "", password_hash))
        
        conn.commit()
        
        # Создаем папку для пользователя в облачном хранилище
        user_folder = Path(f"zornet_cloud/{username}")
        user_folder.mkdir(parents=True, exist_ok=True)
        
        return {
            "success": True, 
            "message": "Аккаунт успешно создан!",
            "email": email,
            "username": username
        }
    except sqlite3.IntegrityError as e:
        error_msg = str(e)
        if "UNIQUE constraint failed: users.email" in error_msg:
            return {"success": False, "message": "Email уже используется"}
        elif "UNIQUE constraint failed: users.username" in error_msg:
            return {"success": False, "message": "Никнейм уже занят"}
        else:
            return {"success": False, "message": f"Ошибка регистрации: {error_msg}"}
    except Exception as e:
        return {"success": False, "message": f"Ошибка: {str(e)}"}
    finally:
        conn.close()

def login_user(email, password):
    """Вход пользователя"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    try:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        c.execute("""
            SELECT id, email, username, first_name, last_name
            FROM users 
            WHERE email = ? AND password_hash = ?
        """, (email, password_hash))
        
        user = c.fetchone()
        
        if user:
            return {
                "id": user[0],
                "email": user[1],
                "username": user[2],
                "first_name": user[3],
                "last_name": user[4]
            }
        return None
    finally:
        conn.close()

def get_user_by_username(username):
    """Поиск пользователя по никнейму"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    c.execute("""
        SELECT id, email, username, first_name, last_name
        FROM users 
        WHERE username = ?
    """, (username,))
    
    user = c.fetchone()
    conn.close()
    
    if user:
        return {
            "id": user[0],
            "email": user[1],
            "username": user[2],
            "first_name": user[3],
            "last_name": user[4]
        }
    return None

def save_chat_message(sender, receiver, message):
    """Сохранение сообщения в чате"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO chat_messages (sender_username, receiver_username, message)
        VALUES (?, ?, ?)
    """, (sender, receiver, message))
    
    conn.commit()
    conn.close()

def save_room_message_to_db(room_id, username, message):
    """Сохранение сообщения в комнате в БД"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO room_messages (room_id, username, message)
        VALUES (?, ?, ?)
    """, (room_id, username, message))
    
    conn.commit()
    conn.close()

def save_room_message(room_id, username, message):
    """Сохранение сообщения в комнате"""
    if room_id not in st.session_state.room_messages:
        st.session_state.room_messages[room_id] = []
    
    st.session_state.room_messages[room_id].append({
        "username": username,
        "message": message,
        "timestamp": datetime.datetime.now().strftime("%H:%M")
    })

def get_chat_history(user1, user2):
    """Получение истории чата"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    c.execute("""
        SELECT sender_username, receiver_username, message, timestamp
        FROM chat_messages
        WHERE (sender_username = ? AND receiver_username = ?)
           OR (sender_username = ? AND receiver_username = ?)
        ORDER BY timestamp ASC
    """, (user1, user2, user2, user1))
    
    messages = c.fetchall()
    conn.close()
    
    return messages

def create_watch_room(room_id, name, youtube_url, password, owner_username):
    """Создание комнаты в БД"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    try:
        c.execute("""
            INSERT INTO watch_rooms (room_id, name, youtube_url, password, owner_username)
            VALUES (?, ?, ?, ?, ?)
        """, (room_id, name, youtube_url, password, owner_username))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка создания комнаты: {e}")
        return False
    finally:
        conn.close()

def get_watch_room(room_id, password):
    """Получение комнаты из БД"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    c.execute("""
        SELECT room_id, name, youtube_url, password, owner_username
        FROM watch_rooms 
        WHERE room_id = ? AND password = ?
    """, (room_id, password))
    
    room = c.fetchone()
    conn.close()
    
    if room:
        return {
            "id": room[0],
            "name": room[1],
            "youtube_url": room[2],
            "password": room[3],
            "owner": room[4]
        }
    return None

def get_all_watch_rooms():
    """Получение всех комнат из БД"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    c.execute("SELECT room_id, name, youtube_url, password, owner_username FROM watch_rooms")
    rooms = c.fetchall()
    conn.close()
    
    return [
        {
            "id": room[0],
            "name": room[1],
            "youtube_url": room[2],
            "password": room[3],
            "owner": room[4]
        }
        for room in rooms
    ]

# ================= САЙДБАР =================
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <span style="font-size: 2.5rem; font-weight: 800; background: linear-gradient(135deg, #C5A028, #F5E6B3); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Z</span>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.is_logged_in:
        user = st.session_state.user_data
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #f8f9fa, #ffffff); padding: 20px; border-radius: 20px; margin-bottom: 20px; border: 1px solid rgba(197, 160, 40, 0.2);">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="width: 50px; height: 50px; border-radius: 15px; background: linear-gradient(135deg, #C5A028, #B38F1A); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 1.5rem;">
                    {user.get('first_name', 'U')[0]}
                </div>
                <div>
                    <div style="font-weight: 700; color: #1a1a1a;">{user.get('first_name', '')} {user.get('last_name', '')}</div>
                    <div style="font-size: 0.8rem; color: #666;">@{user.get('username', '')}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    pages = [
        ("🏠", "Главная"),
        ("📰", "Новости"),
        ("🌤️", "Погода"),
        ("💬", "Мессенджер"),
        ("🎬", "Кинотеатр"),
        ("💾", "Диск"),
        ("👤", "Профиль"),
    ]
    
    for icon, page in pages:
        if st.button(f"{icon} {page}", key=f"nav_{page}", use_container_width=True):
            st.session_state.page = page
            st.rerun()

# ================= ФУНКЦИИ ПОГОДЫ =================
def get_weather_icon(condition_code):
    icons = {
        "01d": "☀️", "01n": "🌙",
        "02d": "⛅", "02n": "⛅",
        "03d": "☁️", "03n": "☁️",
        "04d": "☁️", "04n": "☁️",
        "09d": "🌧️", "09n": "🌧️",
        "10d": "🌦️", "10n": "🌦️",
        "11d": "⛈️", "11n": "⛈️",
        "13d": "❄️", "13n": "❄️",
        "50d": "🌫️", "50n": "🌫️",
    }
    return icons.get(condition_code, "🌡️")

def get_wind_direction(degrees):
    directions = ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"]
    index = round(degrees / 45) % 8
    return directions[index]

def get_weather_by_city(city_name):
    API_KEY = "20ebdd8243b8a3a29abe332fefdadb44"
    
    try:
        geocode_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={API_KEY}"
        geocode_response = requests.get(geocode_url, timeout=10)
        
        if geocode_response.status_code == 200 and geocode_response.json():
            city_data = geocode_response.json()[0]
            lat = city_data["lat"]
            lon = city_data["lon"]
            
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=ru"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=ru"
                forecast_response = requests.get(forecast_url, timeout=10)
                forecast_data = forecast_response.json() if forecast_response.status_code == 200 else None
                
                return {
                    "current": {
                        "temp": round(data["main"]["temp"]),
                        "feels_like": round(data["main"]["feels_like"]),
                        "humidity": data["main"]["humidity"],
                        "pressure": data["main"]["pressure"],
                        "description": data["weather"][0]["description"].capitalize(),
                        "icon": data["weather"][0]["icon"],
                        "wind_speed": data["wind"]["speed"],
                        "wind_deg": data["wind"].get("deg", 0),
                        "clouds": data["clouds"]["all"],
                        "visibility": data.get("visibility", 10000) / 1000,
                        "city": data["name"],
                        "country": data["sys"]["country"],
                        "sunrise": datetime.datetime.fromtimestamp(data["sys"]["sunrise"]).strftime('%H:%M'),
                        "sunset": datetime.datetime.fromtimestamp(data["sys"]["sunset"]).strftime('%H:%M')
                    },
                    "forecast": forecast_data
                }
    except Exception as e:
        print(f"Ошибка получения погоды: {e}")
    
    return None

# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================
def get_icon(file_path):
    ext = file_path.suffix.lower()
    if file_path.is_dir():
        return "📁"
    if ext in [".jpg", ".jpeg", ".png", ".gif"]:
        return "🖼️"
    if ext == ".pdf":
        return "📄"
    if ext in [".doc", ".docx"]:
        return "📝"
    if ext in [".mp3", ".wav"]:
        return "🎵"
    if ext in [".mp4", ".avi", ".mov"]:
        return "🎬"
    return "📦"

# ================= НОВОСТИ =================
def get_belta_news():
    try:
        headers = {"User-Agent": "ZORNET/1.0"}
        response = requests.get("https://www.belta.by/rss", headers=headers, timeout=10)
        feed = feedparser.parse(response.content)
        return feed.entries[:5]
    except:
        return [
            {"title": "Новости Беларуси", "link": "#", "summary": "Следите за обновлениями"},
            {"title": "Экономические новости", "link": "#", "summary": "Развитие экономики страны"},
            {"title": "Спортивные события", "link": "#", "summary": "Последние спортивные новости"},
        ]

# ================= СТРАНИЦА ГЛАВНАЯ =================
if st.session_state.page == "Главная":
    st.markdown('<div class="gold-title fade-in">ZORNET</div>', unsafe_allow_html=True)
    
    current_time = datetime.datetime.now(pytz.timezone('Europe/Minsk')).strftime('%H:%M')
    
    # Верхняя панель с кнопками
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #f8f9fa, #ffffff); padding: 20px; border-radius: 20px; text-align: center; border: 1px solid rgba(197, 160, 40, 0.2);">
            <div style="font-size: 2rem;">🕒</div>
            <div style="font-weight: 700; font-size: 1.2rem;">{current_time}</div>
            <div style="color: #666; font-size: 0.9rem;">Минск</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.button("⛅ Погода", use_container_width=True):
            st.session_state.page = "Погода"
            st.rerun()
    
    with col3:
        if st.button("💬 Мессенджер", use_container_width=True):
            st.session_state.page = "Мессенджер"
            st.rerun()
    
    with col4:
        if st.button("📰 Новости", use_container_width=True):
            st.session_state.page = "Новости"
            st.rerun()
    
    st.markdown("---")
    
    if not st.session_state.is_logged_in:
        st.info("👋 Добро пожаловать! Для полного доступа к функциям войдите в профиль.")
    
    # Поиск Google
    components.html("""
    <div style="margin: 30px 0; text-align: center;">
        <form action="https://www.google.com/search" method="get" target="_blank" style="max-width: 600px; margin: 0 auto;">
            <div style="display: flex; gap: 10px;">
                <input type="text" name="q" placeholder="🔍 Поиск в Google..." 
                       style="flex: 1; padding: 18px 25px; font-size: 16px; border: 2px solid #e0e0e0; border-radius: 30px; outline: none; transition: all 0.3s ease; background: white;">
                <button type="submit" 
                        style="background: linear-gradient(135deg, #C5A028, #B38F1A); color: white; border: none; padding: 0 40px; border-radius: 30px; font-weight: 700; cursor: pointer; transition: all 0.3s ease;">
                    Найти
                </button>
            </div>
        </form>
    </div>
    """, height=100)
    
    st.markdown("---")
    
    # Быстрые ссылки
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h3 style="margin: 0;">📌 Быстрые ссылки</h3>
    </div>
    """, unsafe_allow_html=True)
    
    quick_links = st.session_state.quick_links
    
    if not quick_links:
        st.info("📭 Нет быстрых ссылок. Добавьте первую!")
    else:
        # Показываем ссылки в сетке 4 колонки
        for i in range(0, len(quick_links), 4):
            cols = st.columns(4)
            row_links = quick_links[i:i+4]
            
            for j, link in enumerate(row_links):
                with cols[j]:
                    # Карточка ссылки
                    st.markdown(f"""
                    <div class="link-card">
                        <div class="link-icon">{link.get('icon', '🔗')}</div>
                        <div class="link-name">{link['name']}</div>
                        <div class="link-url">{link['url'][:30]}...</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🌐 Открыть", key=f"open_{link['name']}_{i}_{j}", use_container_width=True):
                            js_code = f'window.open("{link["url"]}", "_blank");'
                            components.html(f"<script>{js_code}</script>", height=0)
                    
                    with col2:
                        if st.button("✖", key=f"delete_{link['name']}_{i}_{j}", use_container_width=True):
                            st.session_state.quick_links.remove(link)
                            save_quick_links(st.session_state.quick_links)
                            st.rerun()
    
    # Кнопка добавления ссылки
    if st.button("➕ Добавить новую ссылку", use_container_width=True, type="primary"):
        st.session_state.show_add_link = not st.session_state.show_add_link
        st.rerun()
    
    # Форма добавления ссылки
    if st.session_state.show_add_link:
        with st.form("add_link_form"):
            st.markdown("### Новая ссылка")
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Название")
                new_icon = st.selectbox("Иконка", ["🔍", "📺", "📧", "🤖", "💻", "🌐", "🎮", "📚", "🎵", "🛒"])
            with col2:
                new_url = st.text_input("URL")
            
            if st.form_submit_button("💾 Сохранить", use_container_width=True):
                if new_name and new_url:
                    if not new_url.startswith(('http://', 'https://')):
                        new_url = 'https://' + new_url
                    
                    st.session_state.quick_links.append({
                        "name": new_name,
                        "url": new_url,
                        "icon": new_icon
                    })
                    save_quick_links(st.session_state.quick_links)
                    st.session_state.show_add_link = False
                    st.rerun()

# ================= МЕССЕНДЖЕР =================
elif st.session_state.page == "Мессенджер":
    st.markdown('<div class="gold-title fade-in">💬 МЕССЕНДЖЕР</div>', unsafe_allow_html=True)
    
    if not st.session_state.is_logged_in:
        st.warning("⚠️ Для использования мессенджера войдите в систему")
        if st.button("Перейти к входу", type="primary"):
            st.session_state.page = "Профиль"
            st.rerun()
        st.stop()
    
    # Создаем две колонки
    col_contacts, col_chat = st.columns([1, 2])
    
    with col_contacts:
        st.markdown("""
        <div style="background: white; border-radius: 20px; padding: 20px; border: 1px solid rgba(197, 160, 40, 0.1);">
            <h4 style="margin: 0 0 20px 0;">🔍 Поиск</h4>
        </div>
        """, unsafe_allow_html=True)
        
        search_username = st.text_input("", placeholder="@username", label_visibility="collapsed")
        
        if st.button("🔍 Найти пользователя", use_container_width=True, type="primary"):
            if search_username:
                if search_username == st.session_state.user_data.get("username"):
                    st.error("Нельзя написать самому себе")
                else:
                    user = get_user_by_username(search_username)
                    if user:
                        st.session_state.chat_partner = user
                        st.success(f"✅ Найден: {user['first_name']}")
                    else:
                        st.error("❌ Пользователь не найден")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Контакты")
        
        # Пример контактов
        contacts = [
            {"id": 2, "username": "alex", "first_name": "Алексей", "last_name": "Петров"},
            {"id": 3, "username": "marina", "first_name": "Марина", "last_name": "Иванова"},
        ]
        
        for contact in contacts:
            is_active = st.session_state.chat_partner and st.session_state.chat_partner.get("username") == contact["username"]
            active_class = "active" if is_active else ""
            
            st.markdown(f"""
            <div class="contact-item {active_class}" onclick="document.getElementById('contact_{contact['id']}').click()">
                <div class="contact-avatar">{contact['first_name'][0]}</div>
                <div>
                    <div style="font-weight: 600;">{contact['first_name']} {contact['last_name']}</div>
                    <div style="font-size: 0.8rem; color: #666;">@{contact['username']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Скрытая кнопка для клика
            if st.button("", key=f"contact_{contact['id']}", help=contact['username']):
                st.session_state.chat_partner = contact
                st.rerun()
    
    with col_chat:
        if st.session_state.chat_partner:
            partner = st.session_state.chat_partner
            current_user = st.session_state.user_data.get("username", "")
            partner_user = partner.get("username", "")
            chat_key = f"{current_user}_{partner_user}"
            
            # Заголовок чата
            st.markdown(f"""
            <div style="background: white; border-radius: 20px; padding: 20px; margin-bottom: 20px; border: 1px solid rgba(197, 160, 40, 0.1); display: flex; align-items: center; gap: 15px;">
                <div style="width: 50px; height: 50px; border-radius: 15px; background: linear-gradient(135deg, #C5A028, #B38F1A); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 1.5rem;">
                    {partner.get('first_name', '?')[0]}
                </div>
                <div>
                    <div style="font-weight: 700; font-size: 1.2rem;">{partner.get('first_name', '')} {partner.get('last_name', '')}</div>
                    <div style="color: #666;">@{partner.get('username', '')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Загружаем сообщения
            if chat_key not in st.session_state.messages:
                db_messages = get_chat_history(current_user, partner_user)
                st.session_state.messages[chat_key] = []
                for msg in db_messages:
                    st.session_state.messages[chat_key].append({
                        "sender": msg[0],
                        "receiver": msg[1],
                        "text": msg[2],
                        "time": msg[3]
                    })
            
            # Контейнер для сообщений
            messages_container = st.container(height=400)
            with messages_container:
                for msg in st.session_state.messages.get(chat_key, []):
                    is_you = msg.get("sender") == current_user
                    msg_text = msg.get("text", "")
                    msg_time = msg.get("time", "")
                    time_display = msg_time.split(" ")[1][:5] if " " in msg_time else msg_time[:5]
                    
                    st.markdown(f"""
                    <div class="message-bubble {'you' if is_you else 'other'}">
                        <div>{msg_text}</div>
                        <div class="message-time">{time_display}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Поле ввода
            col_input, col_send = st.columns([5, 1])
            with col_input:
                new_message = st.text_input("", placeholder="Введите сообщение...", key="chat_input", label_visibility="collapsed")
            with col_send:
                if st.button("📤", use_container_width=True, type="primary"):
                    if new_message:
                        save_chat_message(current_user, partner_user, new_message)
                        st.session_state.messages[chat_key].append({
                            "sender": current_user,
                            "receiver": partner_user,
                            "text": new_message,
                            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.rerun()
        else:
            st.markdown("""
            <div style="background: white; border-radius: 20px; padding: 60px 20px; text-align: center; border: 1px solid rgba(197, 160, 40, 0.1);">
                <div style="font-size: 4rem; margin-bottom: 20px;">💬</div>
                <h3>Выберите контакт для начала общения</h3>
                <p style="color: #666;">Найдите пользователя по никнейму или выберите из списка контактов</p>
            </div>
            """, unsafe_allow_html=True)

# ================= КИНОТЕАТР =================
elif st.session_state.page == "Кинотеатр":
    st.markdown('<div class="gold-title fade-in">🎬 КИНОТЕАТР</div>', unsafe_allow_html=True)
    
    if not st.session_state.is_logged_in:
        st.warning("⚠️ Для создания комнат войдите в систему")
        if st.button("Перейти к входу", type="primary"):
            st.session_state.page = "Профиль"
            st.rerun()
    else:
        # Если пользователь уже в комнате
        if st.session_state.get("watch_room"):
            room_id = st.session_state.watch_room
            
            # Получаем комнату
            room_data = None
            for room in st.session_state.rooms:
                if room["id"] == room_id:
                    room_data = room
                    break
            
            if room_data:
                # Извлекаем ID видео
                video_url = room_data.get("youtube_url", "")
                video_id = None
                
                patterns = [
                    r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([0-9A-Za-z_-]{11})',
                    r'youtube\.com\/embed\/([0-9A-Za-z_-]{11})',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, video_url)
                    if match:
                        video_id = match.group(1)
                        break
                
                # Информация о комнате
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #C5A028, #B38F1A); border-radius: 20px; padding: 25px; color: white; margin-bottom: 20px;">
                    <h2 style="margin: 0 0 10px 0;">{room_data['name']}</h2>
                    <p>ID: {room_id} | Создатель: @{room_data['owner']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # YouTube плеер
                if video_id:
                    components.html(f"""
                    <div style="border-radius: 20px; overflow: hidden; margin-bottom: 20px;">
                        <iframe width="100%" height="500" 
                                src="https://www.youtube.com/embed/{video_id}?autoplay=1"
                                frameborder="0" 
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                                allowfullscreen>
                        </iframe>
                    </div>
                    """, height=520)
                
                # Чат комнаты
                st.markdown("### Чат комнаты")
                
                room_chat_key = f"room_{room_id}"
                if room_chat_key not in st.session_state.room_messages:
                    st.session_state.room_messages[room_chat_key] = [{
                        "username": "Система",
                        "message": f"Добро пожаловать в комнату!",
                        "timestamp": datetime.datetime.now().strftime("%H:%M")
                    }]
                
                # Контейнер для сообщений
                chat_container = st.container(height=200)
                with chat_container:
                    for msg in st.session_state.room_messages[room_chat_key]:
                        username = msg.get("username", "")
                        message = msg.get("message", "")
                        timestamp = msg.get("timestamp", "")
                        
                        st.markdown(f"""
                        <div style="background: {'#e3f2fd' if username == 'Система' else 'white'}; padding: 10px 15px; border-radius: 15px; margin: 5px 0; border-left: 4px solid #C5A028;">
                            <div><strong>{username}:</strong> {message}</div>
                            <div style="font-size: 0.7rem; color: #666; text-align: right;">{timestamp}</div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Отправка сообщения
                col_msg, col_send = st.columns([5, 1])
                with col_msg:
                    room_message = st.text_input("", placeholder="Сообщение...", key="room_msg", label_visibility="collapsed")
                with col_send:
                    if st.button("📤", use_container_width=True):
                        if room_message.strip():
                            username = st.session_state.user_data.get("username", "Гость")
                            save_room_message(room_chat_key, username, room_message)
                            st.rerun()
                
                # Кнопка выхода
                if st.button("← Выйти из комнаты", use_container_width=True, type="primary"):
                    st.session_state.watch_room = None
                    st.rerun()
                
                st.stop()
        
        # Создание/присоединение к комнате
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div style="background: white; border-radius: 20px; padding: 25px; border: 1px solid rgba(197, 160, 40, 0.1);">
                <h3>🎥 Создать комнату</h3>
            </div>
            """, unsafe_allow_html=True)
            
            room_name = st.text_input("Название комнаты", value="Моя комната")
            youtube_url = st.text_input("YouTube ссылка", placeholder="https://youtube.com/watch?v=...")
            room_password = st.text_input("Пароль комнаты", type="password")
            
            if st.button("✨ Создать комнату", use_container_width=True, type="primary"):
                if room_name and youtube_url and room_password:
                    room_id = str(uuid.uuid4())[:8]
                    owner = st.session_state.user_data.get("username", "Гость")
                    
                    if create_watch_room(room_id, room_name, youtube_url, room_password, owner):
                        st.session_state.rooms.append({
                            "id": room_id,
                            "name": room_name,
                            "youtube_url": youtube_url,
                            "password": room_password,
                            "owner": owner
                        })
                        st.session_state.watch_room = room_id
                        st.success(f"✅ Комната создана! ID: {room_id}")
                        st.rerun()
        
        with col2:
            st.markdown("""
            <div style="background: white; border-radius: 20px; padding: 25px; border: 1px solid rgba(197, 160, 40, 0.1);">
                <h3>🔗 Присоединиться</h3>
            </div>
            """, unsafe_allow_html=True)
            
            join_id = st.text_input("ID комнаты")
            join_password = st.text_input("Пароль комнаты", type="password")
            
            if st.button("🚪 Войти в комнату", use_container_width=True, type="primary"):
                if join_id and join_password:
                    room_data = get_watch_room(join_id, join_password)
                    
                    if room_data:
                        st.session_state.rooms.append({
                            "id": room_data["id"],
                            "name": room_data["name"],
                            "youtube_url": room_data["youtube_url"],
                            "password": room_data["password"],
                            "owner": room_data["owner"]
                        })
                        st.session_state.watch_room = room_data["id"]
                        st.rerun()
                    else:
                        st.error("❌ Комната не найдена или неверный пароль")

# ================= ДИСК =================
elif st.session_state.page == "Диск":
    st.markdown('<div class="gold-title fade-in">💾 ДИСК</div>', unsafe_allow_html=True)
    
    # Создаем корневую папку
    os.makedirs("zornet_cloud", exist_ok=True)
    
    # Функции для работы с диском
    def format_size(size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def get_stats():
        total = 0
        files = 0
        folders = 0
        for root, dirs, files_list in os.walk("zornet_cloud"):
            folders += len(dirs)
            for file in files_list:
                files += 1
                total += os.path.getsize(os.path.join(root, file))
        return total, files, folders
    
    # Статистика
    total_size, file_count, folder_count = get_stats()
    
    st.markdown(f"""
    <div class="disk-stats-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h3 style="margin: 0; color: white;">📊 Статистика</h3>
            <span style="background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 30px;">{format_size(total_size)} / 1 GB</span>
        </div>
        <div style="background: rgba(255,255,255,0.2); height: 8px; border-radius: 4px; margin-bottom: 15px;">
            <div style="width: {min(100, (total_size / (1024**3)) * 100)}%; height: 100%; background: white; border-radius: 4px;"></div>
        </div>
        <div style="display: flex; gap: 20px;">
            <div>📁 Папок: {folder_count}</div>
            <div>📄 Файлов: {file_count}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Панель инструментов
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📤 Загрузить", use_container_width=True):
            st.session_state.disk_action = "upload"
    
    with col2:
        if st.button("📁 Новая папка", use_container_width=True):
            st.session_state.disk_action = "new_folder"
    
    with col3:
        if st.button("🔍 Поиск", use_container_width=True):
            st.session_state.disk_action = "search"
    
    with col4:
        if st.button("🔄 Обновить", use_container_width=True):
            st.rerun()
    
    st.markdown("---")
    
    # Действия
    if st.session_state.disk_action == "upload":
        st.markdown("### 📤 Загрузка файлов")
        uploaded_files = st.file_uploader("Выберите файлы", accept_multiple_files=True)
        if uploaded_files:
            for file in uploaded_files:
                file_path = os.path.join("zornet_cloud", file.name)
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
            st.success(f"✅ Загружено {len(uploaded_files)} файлов!")
            st.session_state.disk_action = "view"
            st.rerun()
    
    elif st.session_state.disk_action == "new_folder":
        st.markdown("### 📁 Создание папки")
        folder_name = st.text_input("Название папки")
        if st.button("✅ Создать", use_container_width=True, type="primary"):
            if folder_name:
                os.makedirs(os.path.join("zornet_cloud", folder_name), exist_ok=True)
                st.success(f"✅ Папка '{folder_name}' создана!")
                st.session_state.disk_action = "view"
                st.rerun()
    
    elif st.session_state.disk_action == "search":
        st.markdown("### 🔍 Поиск")
        query = st.text_input("Введите название")
        if query:
            results = []
            for root, dirs, files in os.walk("zornet_cloud"):
                for name in dirs + files:
                    if query.lower() in name.lower():
                        results.append(os.path.join(root, name))
            
            if results:
                st.markdown(f"**Найдено {len(results)}:**")
                for res in results[:10]:
                    st.markdown(f"📄 {os.path.basename(res)}")
            else:
                st.info("Ничего не найдено")
    
    else:
        # Просмотр файлов
        st.markdown("### 📁 Файлы и папки")
        
        # Навигация
        current_path = st.session_state.disk_current_path
        if current_path != "zornet_cloud":
            if st.button("← Назад"):
                st.session_state.disk_current_path = os.path.dirname(current_path)
                st.rerun()
        
        try:
            items = os.listdir(current_path)
        except:
            items = []
        
        if not items:
            st.info("📭 Папка пуста")
        else:
            # Сортируем: папки сверху
            items.sort(key=lambda x: (not os.path.isdir(os.path.join(current_path, x)), x.lower()))
            
            # Показываем в сетке
            cols = st.columns(4)
            for idx, item in enumerate(items):
                with cols[idx % 4]:
                    item_path = os.path.join(current_path, item)
                    is_dir = os.path.isdir(item_path)
                    
                    if is_dir:
                        st.markdown(f"""
                        <div class="file-item">
                            <div class="file-icon">📁</div>
                            <div style="font-weight: 600;">{item[:20]}</div>
                            <div style="font-size: 0.8rem; color: #666;">Папка</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("📂 Открыть", key=f"open_{item}", use_container_width=True):
                            st.session_state.disk_current_path = item_path
                            st.rerun()
                    
                    else:
                        size = os.path.getsize(item_path)
                        icon = "🖼️" if item.lower().endswith(('.jpg','.png')) else "📄"
                        
                        st.markdown(f"""
                        <div class="file-item">
                            <div class="file-icon">{icon}</div>
                            <div style="font-weight: 600;">{item[:15]}</div>
                            <div style="font-size: 0.8rem; color: #666;">{format_size(size)}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        with open(item_path, 'rb') as f:
                            st.download_button("📥 Скачать", f.read(), item, use_container_width=True)

# ================= НОВОСТИ =================
elif st.session_state.page == "Новости":
    st.markdown('<div class="gold-title fade-in">📰 НОВОСТИ</div>', unsafe_allow_html=True)
    
    with st.spinner("Загружаю новости..."):
        news = get_belta_news()
        
        for item in news:
            st.markdown(f"""
            <div class="news-card">
                <div class="news-title">{item.title}</div>
                <div class="news-summary">{item.summary[:200]}...</div>
                <div style="margin-top: 15px;">
                    <a href="{item.link}" target="_blank" style="color: #C5A028; text-decoration: none; font-weight: 600;">Читать далее →</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ================= ПОГОДА =================
elif st.session_state.page == "Погода":
    st.markdown('<div class="gold-title fade-in">🌤️ ПОГОДА</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background: white; border-radius: 20px; padding: 25px; margin-bottom: 30px; border: 1px solid rgba(197, 160, 40, 0.1);">
        <h4 style="margin: 0 0 15px 0;">🔍 Поиск города</h4>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        city_input = st.text_input("", placeholder="Например: Минск, Москва...", label_visibility="collapsed")
    with col2:
        search_clicked = st.button("🔍 Найти", type="primary", use_container_width=True)
    
    city_to_show = st.session_state.user_city if st.session_state.user_city else "Минск"
    
    if search_clicked and city_input:
        city_to_show = city_input
        st.session_state.user_city = city_input
    
    with st.spinner(f"Получаю погоду..."):
        weather_data = get_weather_by_city(city_to_show)
        
        if not weather_data:
            st.error(f"❌ Город {city_to_show} не найден")
            weather_data = get_weather_by_city("Минск")
        
        if weather_data:
            current = weather_data["current"]
            
            # Основная карточка
            st.markdown(f"""
            <div class="weather-main-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="margin: 0; color: white;">{current['city']}, {current['country']}</h2>
                    <div style="font-size: 1.2rem; background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 30px;">
                        {current['description']}
                    </div>
                </div>
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <div class="weather-temp">{current['temp']}°C</div>
                        <div style="font-size: 1.2rem;">Ощущается как {current['feels_like']}°C</div>
                    </div>
                    <div class="weather-icon">{get_weather_icon(current['icon'])}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Детали
            st.markdown("### Детали")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="weather-detail-item">
                    <div style="font-size: 1.5rem;">💧</div>
                    <div style="font-weight: 600;">{current['humidity']}%</div>
                    <div style="font-size: 0.9rem;">Влажность</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="weather-detail-item">
                    <div style="font-size: 1.5rem;">💨</div>
                    <div style="font-weight: 600;">{current['wind_speed']} м/с</div>
                    <div style="font-size: 0.9rem;">Ветер</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="weather-detail-item">
                    <div style="font-size: 1.5rem;">📊</div>
                    <div style="font-weight: 600;">{current['pressure']} гПа</div>
                    <div style="font-size: 0.9rem;">Давление</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="weather-detail-item">
                    <div style="font-size: 1.5rem;">☁️</div>
                    <div style="font-weight: 600;">{current['clouds']}%</div>
                    <div style="font-size: 0.9rem;">Облачность</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Прогноз
            if weather_data.get("forecast"):
                st.markdown("### Прогноз на 5 дней")
                
                forecast = weather_data["forecast"]["list"]
                days = {}
                for item in forecast:
                    date = item["dt_txt"].split(" ")[0]
                    if date not in days:
                        days[date] = item
                
                forecast_dates = list(days.keys())[:5]
                cols = st.columns(len(forecast_dates))
                
                for idx, date in enumerate(forecast_dates):
                    with cols[idx]:
                        day = days[date]
                        day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][
                            datetime.datetime.strptime(date, "%Y-%m-%d").weekday()
                        ]
                        
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 15px; padding: 15px; text-align: center; color: white;">
                            <div style="font-weight: 600;">{day_name}</div>
                            <div style="font-size: 2rem;">{get_weather_icon(day['weather'][0]['icon'])}</div>
                            <div style="font-size: 1.2rem; font-weight: 600;">{round(day['main']['temp'])}°C</div>
                        </div>
                        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🇧🇾 Города Беларуси")
    
    cities = ["Минск", "Гомель", "Витебск", "Могилёв", "Брест", "Гродно"]
    cols = st.columns(3)
    for idx, city in enumerate(cities):
        with cols[idx % 3]:
            if st.button(city, use_container_width=True):
                st.session_state.user_city = city
                st.rerun()

# ================= ПРОФИЛЬ =================
elif st.session_state.page == "Профиль":
    if st.session_state.is_logged_in:
        user = st.session_state.user_data
        
        st.markdown(f"""
        <div class="profile-card fade-in">
            <div class="profile-avatar">{user.get('first_name', 'U')[0]}</div>
            <div class="profile-name">{user.get('first_name', '')} {user.get('last_name', '')}</div>
            <div class="profile-username">@{user.get('username', '')}</div>
            <div class="profile-email">{user.get('email', '')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚪 Выйти из аккаунта", use_container_width=True, type="primary"):
            save_quick_links(st.session_state.quick_links)
            st.session_state.is_logged_in = False
            st.session_state.user_data = {}
            st.session_state.page = "Главная"
            st.rerun()
    
    else:
        st.markdown('<div class="gold-title fade-in">ZORNET ID</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔐 Вход", "📝 Регистрация"])
        
        with tab1:
            st.markdown("### Вход в аккаунт")
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Пароль", type="password", key="login_password")
            
            if st.button("Войти", type="primary", use_container_width=True):
                if login_email and login_password:
                    user = login_user(login_email, login_password)
                    if user:
                        st.session_state.user_data = user
                        st.session_state.is_logged_in = True
                        
                        saved_links = load_quick_links()
                        if saved_links:
                            st.session_state.quick_links = saved_links
                        
                        st.success("✅ Вход выполнен!")
                        st.session_state.page = "Главная"
                        st.rerun()
                    else:
                        st.error("❌ Неверный email или пароль")
        
        with tab2:
            st.markdown("### Создать аккаунт")
            
            if st.session_state.registration_success:
                st.success(f"✅ {st.session_state.registration_message}")
                if st.button("➡️ Перейти ко входу", use_container_width=True):
                    st.session_state.registration_success = False
                    st.rerun()
            else:
                reg_email = st.text_input("Email", key="reg_email")
                reg_username = st.text_input("Никнейм", key="reg_username")
                reg_first_name = st.text_input("Имя", key="reg_first_name")
                reg_last_name = st.text_input("Фамилия", key="reg_last_name")
                reg_password = st.text_input("Пароль", type="password", key="reg_password")
                reg_password_confirm = st.text_input("Повторите пароль", type="password", key="reg_password_confirm")
                
                if st.button("Создать аккаунт", type="primary", use_container_width=True):
                    if not all([reg_email, reg_username, reg_first_name, reg_password, reg_password_confirm]):
                        st.error("❌ Заполните все обязательные поля")
                    elif reg_password != reg_password_confirm:
                        st.error("❌ Пароли не совпадают")
                    elif len(reg_password) < 6:
                        st.error("❌ Пароль должен быть не менее 6 символов")
                    else:
                        result = register_user(reg_email, reg_username, reg_first_name, reg_last_name, reg_password)
                        if result["success"]:
                            st.session_state.registration_success = True
                            st.session_state.registration_message = result["message"]
                            st.rerun()
                        else:
                            st.error(f"❌ {result['message']}")
        
        st.markdown('</div>', unsafe_allow_html=True)

# ================= ИНИЦИАЛИЗАЦИЯ =================
if __name__ == "__main__":
    init_db()
    
    # Создаем тестового пользователя
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        test_password = hashlib.sha256("test123".encode()).hexdigest()
        c.execute("INSERT INTO users (email, username, first_name, last_name, password_hash) VALUES (?, ?, ?, ?, ?)",
                 ("test@zornet.by", "test", "Тест", "Пользователь", test_password))
        conn.commit()
    conn.close()
