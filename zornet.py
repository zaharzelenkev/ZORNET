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
import uuid
import re
import hashlib
import streamlit.components.v1 as components

# ================= ПЕРСИСТЕНТНОЕ ХРАНЕНИЕ =================
def load_storage():
    storage_file = Path("zornet_storage.json")
    if storage_file.exists():
        try:
            with open(storage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_storage(data):
    storage_file = Path("zornet_storage.json")
    with open(storage_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_quick_links(links):
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

storage = load_storage()
if "current_auth" in storage and storage["current_auth"]["is_logged_in"]:
    st.session_state.is_logged_in = True
    st.session_state.user_data = storage["current_auth"]["user_data"]

if "quick_links" not in st.session_state:
    if st.session_state.is_logged_in:
        saved_links = load_quick_links()
        if saved_links:
            st.session_state.quick_links = saved_links
        else:
            st.session_state.quick_links = [
                {"name": "YouTube", "url": "https://www.youtube.com", "icon": "📺"},
                {"name": "Gmail", "url": "https://mail.google.com", "icon": "📧"},
            ]
    else:
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

# ================= ПРОФЕССИОНАЛЬНЫЙ CSS =================
st.markdown("""
<style>
    /* ОСНОВНОЙ ФОН (чуть затемненный градиент, чтобы стекло работало) */
    .stApp {
        background: linear-gradient(135deg, #f0f4f8 0%, #f9fbfd 100%) !important;
    }

    /* САЙДБАР - делаем панель стеклянной */
    section[data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.4) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.6) !important;
    }

    /* КНОПКИ В САЙДБАРЕ (Стеклянные овалы) */
    section[data-testid="stSidebar"] .stButton > button {
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 12px 20px !important;
        margin: 6px auto !important;
        width: 90% !important;
        
        /* Эффект Liquid Glass */
        background: rgba(255, 255, 255, 0.5) !important; /* Полупрозрачность */
        backdrop-filter: blur(12px) !important; /* Размытие фона под кнопкой */
        -webkit-backdrop-filter: blur(12px) !important; /* Для Safari/iOS */
        border: 1px solid rgba(255, 255, 255, 0.8) !important; /* Блик по краям */
        
        color: #1a1a1a !important;
        font-weight: 600 !important;
        border-radius: 30px !important;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.03) !important; /* Нежная тень */
    }
    
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255, 255, 255, 0.85) !important;
        border: 1px solid rgba(218, 165, 32, 0.6) !important; /* Мягкое желто-золотое обрамление */
        transform: scale(1.03) !important;
        box-shadow: 0 8px 20px rgba(218, 165, 32, 0.12), inset 0 0 10px rgba(255,255,255,0.5) !important;
        z-index: 1 !important;
    }

    /* ОСНОВНЫЕ КНОПКИ (На главной странице) - тоже стеклянные */
    div.stButton > button {
        background: rgba(255, 255, 255, 0.5) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.8) !important;
        color: #1a1a1a !important;
        padding: 20px !important; 
        border-radius: 18px !important; /* Смягченные углы */
        font-weight: bold !important;
        width: 100% !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03) !important;
        /* ... центрирование ... */
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        height: 80px !important;
    }

    div.stButton > button:hover {
        background: rgba(255, 255, 255, 0.9) !important;
        border-color: rgba(218, 165, 32, 0.6) !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(218, 165, 32, 0.15) !important;
    }
    
    /* КАРТОЧКИ БЫСТРЫХ ССЫЛОК (Овалы) - тоже под стекло */
    .quick-link-card {
        background: rgba(255, 255, 255, 0.5) !important;
        backdrop-filter: blur(15px) !important;
        -webkit-backdrop-filter: blur(15px) !important;
        border-radius: 60px !important;
        border: 1px solid rgba(218, 165, 32, 0.5) !important; /* Тонкая золотая рамка */
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04) !important;
        /* остальной твой код без изменений... */
    }

    /* ЗОЛОТАЯ КНОПКА AI */
    .gold-btn {
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%) !important;
        border: none !important;
        color: white !important;
        border-radius: 12px !important;
        padding: 14px 28px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        box-shadow: 0 4px 15px rgba(218, 165, 32, 0.3) !important;
    }

    /* ВРЕМЯ В ЗОЛОТОЙ РАМКЕ */
    .time-widget {
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
        border-radius: 12px;
        padding: 12px 15px;
        text-align: center;
        color: white;
        font-weight: 600;
        font-size: 16px;
        box-shadow: 0 4px 15px rgba(218, 165, 32, 0.3);
    }

    /* РЕЗУЛЬТАТЫ ПОИСКА */
    .search-result {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border-left: 4px solid #DAA520;
    }

    /* ЧАТ AI */
    .user-message {
        background: #f0f0f0;
        padding: 12px 18px;
        border-radius: 18px;
        max-width: 70%;
        margin-left: auto;
        margin-bottom: 15px;
    }

    .ai-message {
        background: #f9f9f9;
        padding: 12px 18px;
        border-radius: 18px;
        max-width: 70%;
        margin-right: auto;
        margin-bottom: 15px;
        border-left: 4px solid #DAA520;
    }

    /* СТИЛИ ДЛЯ ПОГОДЫ */
    .weather-widget {
        background: linear-gradient(135deg, #6ecbf5 0%, #059be5 100%);
        border-radius: 15px;
        padding: 20px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(6, 147, 227, 0.3);
    }

    .weather-temp {
        font-size: 3.5rem;
        font-weight: 800;
        line-height: 1;
    }

    .weather-description {
        font-size: 1.2rem;
        margin-bottom: 15px;
    }

    .weather-details {
        background: rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        padding: 15px;
        margin-top: 15px;
    }

    .weather-icon {
        font-size: 4rem;
        text-align: center;
        margin-bottom: 10px;
    }

    .forecast-day {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }

    /* Стили для диска */
    .disk-container {
        background: white;
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }
    
    .disk-header {
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
        border-radius: 12px;
        padding: 25px;
        color: white;
        margin-bottom: 20px;
    }
    
    .disk-btn {
        background: white !important;
        border: 2px solid #DAA520 !important;
        color: #B8860B !important;
        padding: 10px 15px !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    .disk-btn:hover {
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%) !important;
        color: white !important;
        border-color: transparent !important;
    }
    
    .disk-btn-active {
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%) !important;
        color: white !important;
        border-color: transparent !important;
    }
    
    .file-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #DAA520;
        transition: all 0.3s ease;
    }
    
    .file-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    
    .folder-card {
        background: linear-gradient(135deg, #fff9e6 0%, #ffe699 100%);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border: 2px solid #ffd966;
    }
    
    .storage-bar {
        height: 8px;
        background: #e9ecef;
        border-radius: 4px;
        overflow: hidden;
        margin: 10px 0;
    }
    
    .storage-fill {
        height: 100%;
        background: linear-gradient(90deg, #DAA520, #FFD700);
        border-radius: 4px;
    }
    
    /* Стили для профиля - GOOGLE STYLE */
    .giant-id-title {
        font-size: 5rem !important;
        font-weight: 900 !important;
        text-align: center;
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 20px 0 40px 0 !important;
        letter-spacing: -2px;
    }
    
    .profile-container {
        background: white;
        border-radius: 32px;
        padding: 40px;
        border: 1px solid #f0f0f0;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.1);
        text-align: center;
        max-width: 500px;
        margin: 0 auto;
    }
    
    .user-avatar-main {
        width: 180px;
        height: 180px;
        border-radius: 40px;
        object-fit: cover;
        border: 4px solid #DAA520;
        margin-bottom: 20px;
    }
    
    /* GOOGLE STYLE LOGIN */
    .login-container {
        max-width: 450px;
        margin: 30px auto;
        padding: 48px 40px;
        background: white;
        border-radius: 28px;
        border: 1px solid #e8eaed;
        box-shadow: 0 10px 40px rgba(0,0,0,0.05);
    }
    
    .google-input {
        border: 1px solid #dadce0 !important;
        border-radius: 24px !important;
        padding: 14px 18px !important;
        font-size: 16px !important;
        transition: all 0.2s ease !important;
    }
    
    .google-input:focus {
        border-color: #DAA520 !important;
        box-shadow: 0 1px 6px rgba(218, 165, 32, 0.3) !important;
    }
    
    .google-button {
        background: #DAA520 !important;
        color: white !important;
        border: none !important;
        border-radius: 24px !important;
        padding: 14px 24px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 8px rgba(218, 165, 32, 0.3) !important;
    }
    
    .google-button:hover {
        background: #B8860B !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(218, 165, 32, 0.4) !important;
    }
    
    .google-tabs {
        margin-bottom: 24px;
        border-bottom: 1px solid #e8eaed;
    }
    
    .google-tabs button {
        background: transparent !important;
        border: none !important;
        color: #5f6368 !important;
        font-weight: 500 !important;
        padding: 12px 24px !important;
        margin-right: 8px !important;
        border-radius: 24px 24px 0 0 !important;
    }
    
    .google-tabs button[aria-selected="true"] {
        color: #DAA520 !important;
        border-bottom: 3px solid #DAA520 !important;
    }

    /* Стили для карточек быстрых ссылок - ИДЕАЛЬНЫЕ БЕЛЫЕ ОВАЛЫ */
    .quick-link-card {
        position: relative;
        background: white !important;
        border-radius: 60px !important;
        border: 3px solid #DAA520;
        padding: 30px 15px !important;
        margin: 10px 0;
        text-align: center;
        transition: all 0.3s ease;
        min-height: 200px;
        display: flex !important;
        flex-direction: column;
        justify-content: center !important;
        align-items: center !important;
        box-shadow: 0 4px 15px rgba(218, 165, 32, 0.15);
        width: 100%;
        box-sizing: border-box;
    }

    .quick-link-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(218, 165, 32, 0.25);
        border-color: #B8860B;
        background: white !important;
    }

    .quick-link-icon {
        font-size: 4rem !important;
        margin-bottom: 15px !important;
        text-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
        display: block !important;
    }

    .quick-link-card:hover .quick-link-icon {
        transform: scale(1.1) rotate(5deg);
    }

    .quick-link-name {
        font-weight: 800 !important;
        font-size: 1.3rem !important;
        color: #333 !important;
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.4 !important;
        font-family: 'Helvetica Neue', sans-serif;
        display: block !important;
        text-align: center !important;
        word-break: break-word;
    }

    /* Круглые кнопки */
    .stButton > button {
        border-radius: 40px !important;
    }
    
    button[key="add_link_btn"] {
        background: white !important;
        border: 2px solid #DAA520 !important;
        color: #DAA520 !important;
        border-radius: 40px !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }

    button[key="add_link_btn"]:hover {
        background: #DAA520 !important;
        color: white !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(218, 165, 32, 0.3) !important;
    }

    /* Мессенджер стили */
    .messenger-container {
        display: flex;
        height: 700px;
        background: white;
        border-radius: 16px;
        border: 1px solid #e0e0e0;
        overflow: hidden;
    }
    
    .contacts-sidebar {
        width: 350px;
        border-right: 1px solid #e0e0e0;
        background: #f8f9fa;
        overflow-y: auto;
    }
    
    .chat-area {
        flex: 1;
        display: flex;
        flex-direction: column;
    }
    
    .chat-header {
        padding: 16px 20px;
        border-bottom: 1px solid #e0e0e0;
        background: white;
    }
    
    .messages-container {
        flex: 1;
        padding: 20px;
        overflow-y: auto;
        background: #f0f2f5;
    }
    
    .message-input-area {
        padding: 16px 20px;
        border-top: 1px solid #e0e0e0;
        background: white;
    }
    
    .contact-item {
        padding: 12px 16px;
        border-bottom: 1px solid #e0e0e0;
        cursor: pointer;
        transition: background 0.2s;
    }
    
    .contact-item:hover {
        background: #e9ecef;
    }
    
    .contact-item.active {
        background: #e3f2fd;
        border-left: 3px solid #DAA520;
    }
    
    .message-bubble {
        max-width: 70%;
        padding: 10px 14px;
        border-radius: 18px;
        margin-bottom: 8px;
        word-wrap: break-word;
    }
    
    .message-bubble.you {
        background: #DCF8C6;
        margin-left: auto;
        border-bottom-right-radius: 4px;
    }
    
    .message-bubble.other {
        background: white;
        margin-right: auto;
        border-bottom-left-radius: 4px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Новости */
    .news-item {
        background: #f8f9fa;
        border-left: 4px solid #DAA520;
        padding: 15px;
        margin-bottom: 15px;
        border-radius: 8px;
    }
    
    .news-title {
        color: #DAA520;
        font-size: 1.2rem;
        font-weight: bold;
        text-decoration: none;
    }
    
    .news-title:hover {
        text-decoration: underline;
    }

    /* Стили для сообщения об успешной регистрации */
    .success-message {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin: 15px 0;
        border-left: 5px solid #2E7D32;
    }
</style>
""", unsafe_allow_html=True)

# ================= БАЗА ДАННЫХ =================
def init_db():
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
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
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_username TEXT NOT NULL,
            receiver_username TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
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
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    try:
        c.execute("SELECT email FROM users WHERE LOWER(email) = LOWER(?)", (email,))
        if c.fetchone():
            return {"success": False, "message": "Email уже используется"}
        
        c.execute("SELECT username FROM users WHERE LOWER(username) = LOWER(?)", (username,))
        if c.fetchone():
            return {"success": False, "message": "Никнейм уже занят"}
        
        if len(password) < 6:
            return {"success": False, "message": "Пароль должен быть не менее 6 символов"}
        
        if '@' not in email or '.' not in email:
            return {"success": False, "message": "Неверный формат email"}
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        c.execute("""
            INSERT INTO users (email, username, first_name, last_name, password_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (email.strip(), username.strip(), first_name.strip(), 
              last_name.strip() if last_name else "", password_hash))
        
        conn.commit()
        
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
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO chat_messages (sender_username, receiver_username, message)
        VALUES (?, ?, ?)
    """, (sender, receiver, message))
    
    conn.commit()
    conn.close()

def save_room_message_to_db(room_id, username, message):
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO room_messages (room_id, username, message)
        VALUES (?, ?, ?)
    """, (room_id, username, message))
    
    conn.commit()
    conn.close()

def save_room_message(room_id, username, message):
    if room_id not in st.session_state.room_messages:
        st.session_state.room_messages[room_id] = []
    
    st.session_state.room_messages[room_id].append({
        "username": username,
        "message": message,
        "timestamp": datetime.datetime.now().strftime("%H:%M")
    })

def get_chat_history(user1, user2):
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
    st.markdown("<h3 style='color:#DAA520; text-align:center;'>ZORNET</h3>", unsafe_allow_html=True)
    
    if st.session_state.is_logged_in:
        user = st.session_state.user_data
        st.markdown(f"**👤 {user.get('first_name', '')} {user.get('last_name', '')}**")
        st.markdown(f"*@{user.get('username', '')}*")
        st.markdown("---")
    
    pages = [
        ("🏠", "ГЛАВНАЯ", "Главная"),
        ("📰", "НОВОСТИ", "Новости"),
        ("🌤️", "ПОГОДА", "Погода"),
        ("💬", "МЕССЕНДЖЕР", "Мессенджер"),
        ("🎬", "КИНОТЕАТР", "Кинотеатр"),
        ("💾", "ДИСК", "Диск"),
        ("👤", "ПРОФИЛЬ", "Профиль"),
    ]
    
    for i, (icon, text, page) in enumerate(pages):
        if st.button(f"{icon} {text}", key=f"nav_{i}_{page}", use_container_width=True):
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

def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def get_disk_stats():
    total_size = 0
    file_count = 0
    folder_count = 0
    
    root_path = st.session_state.disk_current_path
    if os.path.exists(root_path):
        for root, dirs, files in os.walk(root_path):
            folder_count += len(dirs)
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
                    file_count += 1
    
    return {
        'total_size': total_size,
        'file_count': file_count,
        'folder_count': folder_count
    }

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
    st.markdown('<div class="gold-title">ZORNET</div>', unsafe_allow_html=True)
    
    current_time = datetime.datetime.now(pytz.timezone('Europe/Minsk')).strftime('%H:%M')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.button(f"🕒 {current_time}\nМинск", key="time_btn", use_container_width=True)
    with col2:
        if st.button("⛅ Погода", key="weather_btn", use_container_width=True):
            st.session_state.page = "Погода"
            st.rerun()
    with col3:
        if st.button("💬 Мессенджер", key="messenger_btn", use_container_width=True):
            st.session_state.page = "Мессенджер"
            st.rerun()
    with col4:
        if st.button("📰 Новости", key="news_btn", use_container_width=True):
            st.session_state.page = "Новости"
            st.rerun()
    
    st.markdown("---")
    
    if not st.session_state.is_logged_in:
        st.warning("⚠️ Вы не авторизованы. Перейдите в профиль для входа.")
    
    components.html("""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {
            margin: 0;
            padding: 0;
            background-color: transparent;
            font-family: 'Helvetica Neue', sans-serif;
            display: flex;
            justify-content: center;
        }
        
        .search-container {
            width: 100%;
            max-width: 600px;
            padding: 10px;
            box-sizing: border-box;
            text-align: center;
        }

        input[type="text"] {
            width: 100%;
            padding: 18px 25px;
            font-size: 18px;
            border: 2px solid #e0e0e0;
            border-radius: 30px;
            outline: none;
            transition: all 0.3s ease;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
            background-color: #ffffff;
            color: #333;
            box-sizing: border-box;
            -webkit-appearance: none;
        }

        input[type="text"]:focus {
            border-color: #DAA520;
            box-shadow: 0 0 15px rgba(218, 165, 32, 0.2);
        }

        button {
            margin-top: 20px;
            background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
            color: white;
            border: none;
            padding: 14px 40px;
            border-radius: 25px;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(218, 165, 32, 0.4);
            transition: transform 0.2s, box-shadow 0.2s;
            text-transform: uppercase;
            letter-spacing: 1px;
            -webkit-appearance: none;
            width: 100%;
            max-width: 250px;
        }

        button:hover {
            transform: scale(1.03);
            box-shadow: 0 6px 20px rgba(218, 165, 32, 0.6);
        }
        
        button:active {
            transform: scale(0.98);
        }
    </style>
    </head>
    <body>
        <div class="search-container">
            <form action="https://www.google.com/search" method="get" target="_top">
                <input type="text" name="q" placeholder="🔍 Введите запрос..." required autocomplete="off">
                <br>
                <button type="submit">ИСКАТЬ</button>
            </form>
        </div>
    </body>
    </html>
    """, height=220)
    
    st.markdown("---")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 📌 Быстрые ссылки")
    with col2:
        if st.button("➕ Добавить", key="add_link_btn", use_container_width=True):
            st.session_state.show_add_link = not st.session_state.show_add_link
            st.rerun()

    quick_links = st.session_state.quick_links

    if not quick_links:
        st.info("📭 Нет быстрых ссылок. Нажмите 'Добавить', чтобы создать первую!")
    else:
        for i in range(0, len(quick_links), 4):
            cols = st.columns(4)
            for j, link in enumerate(quick_links[i:i+4]):
                with cols[j]:
                    st.markdown(f"""
                    <div class="quick-link-card">
                        <div class="quick-link-icon">{link.get('icon', '🔗')}</div>
                        <div class="quick-link-name">{link['name']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col_open, col_del = st.columns([2, 1])
                    with col_open:
                        if st.button("🌐", key=f"open_{i}_{j}", use_container_width=True):
                            js_code = f'window.open("{link["url"]}", "_blank");'
                            components.html(f"<script>{js_code}</script>", height=0)
                    with col_del:
                        if st.button("✕", key=f"del_{i}_{j}", use_container_width=True):
                            st.session_state.quick_links.remove(link)
                            save_quick_links(st.session_state.quick_links)
                            st.rerun()

    st.markdown("---")
    
    if st.session_state.show_add_link:
        st.markdown("#### 📝 Добавить новую ссылку")
        
        col_name, col_url, col_icon = st.columns([2, 3, 1])
        
        with col_name:
            new_link_name = st.text_input("Название", placeholder="Например: Facebook", key="new_name")
        
        with col_url:
            new_link_url = st.text_input("URL", placeholder="https://facebook.com", key="new_url")
        
        with col_icon:
            new_link_icon = st.selectbox(
                "Иконка",
                ["🔍", "📺", "📧", "🤖", "💻", "👥", "🌐", "🎮", "📚", "🎵", "🛒", "💼", "🎨", "📱", "🔧"],
                index=0,
                key="new_icon"
            )
        
        col_save, col_cancel = st.columns(2)
        
        with col_save:
            if st.button("💾 Сохранить", type="primary", use_container_width=True):
                if new_link_name and new_link_url:
                    if not new_link_url.startswith(('http://', 'https://')):
                        new_link_url = 'https://' + new_link_url
                    
                    existing_urls = [link['url'] for link in st.session_state.quick_links]
                    if new_link_url in existing_urls:
                        st.error("Эта ссылка уже добавлена!")
                    else:
                        st.session_state.quick_links.append({
                            "name": new_link_name,
                            "url": new_link_url,
                            "icon": new_link_icon
                        })
                        save_quick_links(st.session_state.quick_links)
                        st.session_state.show_add_link = False
                        st.success(f"Ссылка '{new_link_name}' добавлена!")
                        st.rerun()
                else:
                    st.error("Заполните название и URL")
        
        with col_cancel:
            if st.button("❌ Отмена", use_container_width=True):
                st.session_state.show_add_link = False
                st.rerun()

# ================= СТРАНИЦА НОВОСТЕЙ =================
elif st.session_state.page == "Новости":
    st.markdown('<div class="gold-title">📰 НОВОСТИ</div>', unsafe_allow_html=True)
    
    with st.spinner("Загружаю новости..."):
        news = get_belta_news()
        
        for item in news:
            st.markdown(f"""
            <div class="news-item">
                <a href="{item.link}" target="_blank" class="news-title">{item.title}</a>
                <p style="color:#1a1a1a; margin-top:10px;">{item.summary[:200]}...</p>
            </div>
            """, unsafe_allow_html=True)

# ================= СТРАНИЦА ПОГОДЫ =================
elif st.session_state.page == "Погода":
    st.markdown('<div class="gold-title">🌤️ ПОГОДА</div>', unsafe_allow_html=True)
    
    st.markdown("### Введите город для поиска погоды")
    
    col_search, col_btn = st.columns([3, 1])
    
    with col_search:
        city_input = st.text_input(
            "Город:",
            placeholder="Например: Минск, Гродно, Москва...",
            label_visibility="collapsed",
            key="city_search"
        )
    
    with col_btn:
        search_clicked = st.button("🔍 Найти", type="primary", use_container_width=True)
    
    city_to_show = st.session_state.user_city if st.session_state.user_city else "Минск"
    
    if search_clicked and city_input:
        city_to_show = city_input
        st.session_state.user_city = city_input
    
    with st.spinner(f"Получаю погоду для {city_to_show}..."):
        weather_data = get_weather_by_city(city_to_show)
        
        if not weather_data:
            st.error(f"Не удалось найти город: {city_to_show}")
            weather_data = get_weather_by_city("Минск")
            if weather_data:
                city_to_show = "Минск"
                st.info("Показываю погоду для Минска")
        
        if weather_data:
            current = weather_data["current"]
            st.session_state.user_city = city_to_show

            st.markdown(f"### 🌤️ Погода в {current['city']}, {current['country']}")

            col_temp, col_icon = st.columns([2, 1])

            with col_temp:
                st.markdown(f"""
                <div style="text-align: center;">
                    <div style="font-size: 4rem; font-weight: 800;">{current['temp']}°C</div>
                    <div style="font-size: 1.5rem;">{get_weather_icon(current['icon'])} {current['description']}</div>
                    <div style="font-size: 1rem; color: #888;">💁 Ощущается как {current['feels_like']}°C</div>
                </div>
                """, unsafe_allow_html=True)

            with col_icon:
                st.markdown(f"""
                <div style="text-align: center; padding-top: 15px;">
                    <div style="font-size: 5rem;">{get_weather_icon(current['icon'])}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("#### 📊 Детали")

            details = [
                ("💧 Влажность", f"{current['humidity']}%"),
                ("💨 Ветер", f"{current['wind_speed']} м/с"),
                ("🧭 Направление", get_wind_direction(current['wind_deg'])),
                ("📊 Давление", f"{current['pressure']} гПа"),
                ("👁️ Видимость", f"{current['visibility']} км"),
                ("☁️ Облачность", f"{current['clouds']}%"),
                ("🌅 Восход", current['sunrise']),
                ("🌇 Закат", current['sunset'])
            ]

            for i in range(0, len(details), 2):
                col1, col2 = st.columns(2)
                
                with col1:
                    name, value = details[i]
                    st.markdown(f"""
                    <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 10px;">
                        <div style="color: #666;">{name}</div>
                        <div style="font-size: 1.2rem; font-weight: bold;">{value}</div>
                    </div>
                    """, unsafe_allow_html=True)

                if i + 1 < len(details):
                    with col2:
                        name, value = details[i + 1]
                        st.markdown(f"""
                        <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 10px;">
                            <div style="color: #666;">{name}</div>
                            <div style="font-size: 1.2rem; font-weight: bold;">{value}</div>
                        </div>
                        """, unsafe_allow_html=True)

            if weather_data.get("forecast"):
                st.markdown("#### 📅 Прогноз на 5 дней")

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
                        <div style="background: #f8f9fa; border-radius: 10px; padding: 15px; text-align: center;">
                            <div style="font-weight: bold;">{day_name}</div>
                            <div style="font-size: 2rem;">{get_weather_icon(day['weather'][0]['icon'])}</div>
                            <div style="font-size: 1.2rem; font-weight: bold;">{round(day['main']['temp'])}°C</div>
                        </div>
                        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🇧🇾 Города Беларуси")

    belarus_cities = [
        "Минск", "Гомель", "Витебск", "Могилёв", "Брест", "Гродно",
        "Бобруйск", "Барановичи", "Борисов", "Пинск", "Орша", "Мозырь"
    ]

    cols = st.columns(3)
    for idx, city in enumerate(belarus_cities):
        with cols[idx % 3]:
            if st.button(city, key=f"city_{city}", use_container_width=True):
                st.session_state.user_city = city
                st.rerun()

# ================= МЕССЕНДЖЕР =================
elif st.session_state.page == "Мессенджер":
    st.markdown('<div class="gold-title">💬 МЕССЕНДЖЕР</div>', unsafe_allow_html=True)
    
    if not st.session_state.is_logged_in:
        st.warning("⚠️ Для использования мессенджера войдите в систему")
        if st.button("Перейти к входу", use_container_width=True):
            st.session_state.page = "Профиль"
            st.rerun()
    else:
        col_search, col_chat = st.columns([1, 2])
        
        with col_search:
            st.markdown("### Найти пользователя")
            search_username = st.text_input("Введите никнейм:", placeholder="@username", key="search_user")
            
            if st.button("🔍 Найти", use_container_width=True):
                if search_username:
                    if search_username == st.session_state.user_data.get("username"):
                        st.error("Нельзя написать самому себе")
                    else:
                        user = get_user_by_username(search_username)
                        if user:
                            st.session_state.chat_partner = user
                            st.success(f"Найден: {user['first_name']} {user['last_name']}")
                        else:
                            st.error("Пользователь не найден")
            
            st.markdown("---")
            st.markdown("### Контакты")
            
            contacts = [
                {"id": 2, "username": "alex", "first_name": "Алексей", "last_name": "Петров"},
                {"id": 3, "username": "marina", "first_name": "Марина", "last_name": "Иванова"},
            ]
            
            for contact in contacts:
                if st.button(f"💬 {contact['first_name']} {contact['last_name']}\n@{contact['username']}", 
                            key=f"contact_{contact['id']}", use_container_width=True):
                    st.session_state.chat_partner = contact
                    st.rerun()

        with col_chat:
            if st.session_state.chat_partner:
                partner = st.session_state.chat_partner

                st.markdown(f"""
                <div style="background: white; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 15px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #DAA520, #B8860B); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                            {partner.get("first_name", "?")[0]}
                        </div>
                        <div>
                            <div style="font-weight: 600; font-size: 18px;">
                                {partner.get("first_name", "")} {partner.get("last_name", "")}
                            </div>
                            <div style="font-size: 14px; color: #666;">
                                @{partner.get("username", "")}
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                current_user = st.session_state.user_data.get("username", "")
                partner_user = partner.get("username", "")
                chat_key = f"{current_user}_{partner_user}"

                if chat_key not in st.session_state.messages:
                    db_messages = get_chat_history(current_user, partner_user)
                    st.session_state.messages[chat_key] = []
                    for msg in db_messages:
                        st.session_state.messages[chat_key].append({
                            "sender": msg[0], "text": msg[2], "time": msg[3]
                        })

                chat_container = st.container(height=400)
                with chat_container:
                    for msg in st.session_state.messages.get(chat_key, []):
                        time_display = msg['time'].split(" ")[1][:5] if " " in msg['time'] else msg['time'][:5]
                        
                        if msg.get("sender") == current_user:
                            st.markdown(f"""
                            <div style="background: #DCF8C6; padding: 10px 15px; border-radius: 18px; margin: 5px 0; margin-left: auto; max-width: 70%; border-bottom-right-radius: 4px;">
                                <div>{msg['text']}</div>
                                <div style="font-size: 11px; color: #666; text-align: right;">{time_display}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style="background: white; padding: 10px 15px; border-radius: 18px; margin: 5px 0; margin-right: auto; max-width: 70%; border-bottom-left-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                                <div>{msg['text']}</div>
                                <div style="font-size: 11px; color: #666; text-align: right;">{time_display}</div>
                            </div>
                            """, unsafe_allow_html=True)
                
                col_input, col_send = st.columns([5, 1])
                with col_input:
                    new_message = st.text_input("", placeholder="Введите сообщение...", key="new_msg")
                with col_send:
                    if st.button("📤", use_container_width=True, type="primary") and new_message:
                        save_chat_message(current_user, partner_user, new_message)
                        st.session_state.messages[chat_key].append({
                            "sender": current_user, "text": new_message,
                            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.rerun()
            else:
                st.info("👈 Выберите пользователя для начала общения")

# ================= КИНОТЕАТР =================
elif st.session_state.page == "Кинотеатр":
    st.markdown('<div class="gold-title">🎬 КИНОТЕАТР</div>', unsafe_allow_html=True)
    
    if not st.session_state.is_logged_in:
        st.warning("⚠️ Для создания комнат войдите в систему")
        if st.button("Перейти к входу", use_container_width=True):
            st.session_state.page = "Профиль"
            st.rerun()
    else:
        if st.session_state.get("watch_room"):
            room_id = st.session_state.watch_room
            room_data = None
            
            for room in st.session_state.rooms:
                if room["id"] == room_id:
                    room_data = room
                    break
            
            if not room_data:
                db_rooms = get_all_watch_rooms()
                for room in db_rooms:
                    if room["id"] == room_id:
                        room_data = room
                        if room not in st.session_state.rooms:
                            st.session_state.rooms.append(room)
                        break
            
            if room_data:
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
                
                st.markdown(f"### 🎥 {room_data['name']}")
                st.markdown(f"**ID комнаты:** `{room_id}` | **Создатель:** @{room_data['owner']}")
                
                if video_id:
                    components.html(f"""
                    <iframe width="100%" height="500" 
                            src="https://www.youtube.com/embed/{video_id}?autoplay=1&controls=1&modestbranding=1"
                            frameborder="0" 
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                            allowfullscreen>
                    </iframe>
                    """, height=550)
                else:
                    st.warning("Некорректная ссылка на YouTube видео")
                
                st.markdown("### 💬 Чат комнаты")
                
                room_chat_key = f"room_{room_id}"
                if room_chat_key not in st.session_state.room_messages:
                    st.session_state.room_messages[room_chat_key] = [{
                        "username": "Система",
                        "message": f"Добро пожаловать в комнату!",
                        "timestamp": datetime.datetime.now().strftime("%H:%M")
                    }]
                
                chat_container = st.container(height=200)
                with chat_container:
                    for msg in st.session_state.room_messages[room_chat_key]:
                        if msg["username"] == "Система":
                            st.markdown(f'''
                            <div style="background: #e3f2fd; padding: 10px 15px; border-radius: 10px; margin: 8px 0; border-left: 4px solid #DAA520;">
                                <div><strong>{msg["username"]}:</strong> {msg["message"]}</div>
                                <div style="font-size: 11px; color: #666; text-align: right;">{msg["timestamp"]}</div>
                            </div>
                            ''', unsafe_allow_html=True)
                        else:
                            st.markdown(f'''
                            <div style="background: white; padding: 10px 15px; border-radius: 10px; margin: 8px 0; border: 1px solid #e0e0e0;">
                                <div><strong>{msg["username"]}:</strong> {msg["message"]}</div>
                                <div style="font-size: 11px; color: #666; text-align: right;">{msg["timestamp"]}</div>
                            </div>
                            ''', unsafe_allow_html=True)

                col_msg, col_send = st.columns([5, 1])
                with col_msg:
                    room_message = st.text_input("", placeholder="Ваше сообщение...", key="room_msg")
                with col_send:
                    if st.button("Отпр.", use_container_width=True) and room_message:
                        username = st.session_state.user_data.get("username", "Гость")
                        save_room_message(room_chat_key, username, room_message)
                        save_room_message_to_db(room_id, username, room_message)
                        st.rerun()

                if st.button("← Выйти из комнаты", type="primary", use_container_width=True):
                    st.session_state.watch_room = None
                    st.rerun()
        else:
            col_create, col_join = st.columns(2)

            with col_create:
                st.markdown("### Создать комнату")
                room_name = st.text_input("Название комнаты:", value="Моя комната", key="room_name")
                youtube_url = st.text_input("YouTube ссылка:", placeholder="https://www.youtube.com/watch?v=...", key="youtube_url")
                room_password = st.text_input("Пароль комнаты:", type="password", key="room_password")
                
                if st.button("🎥 Создать комнату", type="primary", use_container_width=True):
                    if room_name and youtube_url and room_password:
                        room_id = str(uuid.uuid4())[:8]
                        owner = st.session_state.user_data.get("username", "Гость")
                        
                        if create_watch_room(room_id, room_name, youtube_url, room_password, owner):
                            st.session_state.rooms.append({
                                "id": room_id, "name": room_name, "youtube_url": youtube_url,
                                "password": room_password, "owner": owner,
                                "created": datetime.datetime.now().strftime("%H:%M")
                            })
                            st.session_state.watch_room = room_id
                            st.success(f"✅ Комната создана! ID: `{room_id}`")
                            st.rerun()
                        else:
                            st.error("Ошибка создания комнаты")

            with col_join:
                st.markdown("### Присоединиться к комнате")
                join_id = st.text_input("ID комнаты:", placeholder="Введите ID комнаты", key="join_id")
                join_password = st.text_input("Пароль комнаты:", type="password", key="join_password")
                
                if st.button("🔗 Присоединиться", type="primary", use_container_width=True):
                    if join_id and join_password:
                        room_data = get_watch_room(join_id, join_password)
                        
                        if room_data:
                            st.session_state.watch_room = room_data["id"]
                            st.success(f"✅ Вы присоединились к комнате!")
                            st.rerun()
                        else:
                            st.error("❌ Комната не найдена или неверный пароль")

# ================= ПРОФЕССИОНАЛЬНЫЙ ОБЛАЧНЫЙ ДИСК ZORNET DISK =================
elif st.session_state.page == "Диск":
    st.markdown('<div class="gold-title">💾 ДИСК</div>', unsafe_allow_html=True)

    if "disk_current_path" not in st.session_state:
        st.session_state.disk_current_path = "zornet_cloud"
    if "disk_action" not in st.session_state:
        st.session_state.disk_action = "view"

    os.makedirs(st.session_state.disk_current_path, exist_ok=True)

    st.markdown("### 🛠 Панель инструментов")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📤 Загрузить", key="btn_upload", use_container_width=True):
            st.session_state.disk_action = "upload"
            st.rerun()
    with col2:
        if st.button("📁 Новая папка", key="btn_new_folder", use_container_width=True):
            st.session_state.disk_action = "new_folder"
            st.rerun()
    with col3:
        if st.button("🔍 Поиск", key="btn_search", use_container_width=True):
            st.session_state.disk_action = "search"
            st.rerun()
    with col4:
        if st.button("🔄 Обновить", key="btn_refresh", use_container_width=True):
            st.rerun()

    stats = get_disk_stats()
    used_gb = stats['total_size'] / (1024 * 1024 * 1024)
    used_percent = min(100, (used_gb / 1.0) * 100)

    st.markdown(f"""
    <div style="background: white; padding: 15px; border-radius: 10px; margin: 15px 0; border: 1px solid #e0e0e0;">
        <h4 style="margin: 0 0 10px 0;">📊 Использование хранилища</h4>
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span>Использовано: {format_file_size(stats['total_size'])}</span>
            <span>Лимит: 1.0 GB</span>
        </div>
        <div class="storage-bar">
            <div class="storage-fill" style="width: {used_percent}%;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 10px; font-size: 0.9rem;">
            <span>📁 Папок: {stats['folder_count']}</span>
            <span>📄 Файлов: {stats['file_count']}</span>
            <span>📊 Свободно: {format_file_size(1073741824 - stats['total_size'])}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.disk_action == "upload":
        st.markdown("### 📤 Загрузка файлов")

        uploaded_files = st.file_uploader(
            "Выберите файлы для загрузки",
            accept_multiple_files=True,
            key="file_uploader"
        )

        if uploaded_files:
            for uploaded_file in uploaded_files:
                file_path = os.path.join(st.session_state.disk_current_path, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            st.success(f"✅ Загружено {len(uploaded_files)} файлов!")
            st.session_state.disk_action = "view"
            st.rerun()

        if st.button("← Назад к файлам", use_container_width=True):
            st.session_state.disk_action = "view"
            st.rerun()

    elif st.session_state.disk_action == "new_folder":
        st.markdown("### 📁 Создание новой папки")

        folder_name = st.text_input("Введите название папки:")

        col_create, col_back = st.columns(2)

        with col_create:
            if st.button("✅ Создать папку", type="primary", use_container_width=True):
                if folder_name:
                    new_folder_path = os.path.join(st.session_state.disk_current_path, folder_name)
                    os.makedirs(new_folder_path, exist_ok=True)
                    st.success(f"Папка '{folder_name}' создана!")
                    st.session_state.disk_action = "view"
                    st.rerun()

        with col_back:
            if st.button("← Назад к файлам", use_container_width=True):
                st.session_state.disk_action = "view"
                st.rerun()

    elif st.session_state.disk_action == "search":
        st.markdown("### 🔍 Поиск файлов")

        search_query = st.text_input("Введите название файла или папки:")

        if search_query:
            found_items = []
            for root, dirs, files in os.walk(st.session_state.disk_current_path):
                for name in dirs + files:
                    if search_query.lower() in name.lower():
                        item_path = os.path.join(root, name)
                        found_items.append({
                            'name': name,
                            'path': item_path,
                            'is_dir': os.path.isdir(item_path),
                            'size': os.path.getsize(item_path) if os.path.isfile(item_path) else 0
                        })

            if found_items:
                st.markdown(f"**Найдено {len(found_items)} результатов:**")
                for item in found_items[:10]:
                    icon = "📁" if item['is_dir'] else "📄"
                    st.markdown(f"{icon} **{item['name']}**")
            else:
                st.info("Ничего не найдено")

        if st.button("← Назад к файлам", use_container_width=True):
            st.session_state.disk_action = "view"
            st.rerun()

    else:
        st.markdown("### 📁 Файлы и папки")

        if st.session_state.disk_current_path != "zornet_cloud":
            current_parts = st.session_state.disk_current_path.split(os.sep)
            breadcrumb = []
            path_so_far = ""

            for part in current_parts:
                if part:
                    path_so_far = os.path.join(path_so_far, part) if path_so_far else part
                    breadcrumb.append((part, path_so_far))

            st.markdown("**Путь:** ", unsafe_allow_html=True)
            crumb_cols = st.columns(len(breadcrumb) * 2 - 1)

            for i, (name, path) in enumerate(breadcrumb):
                with crumb_cols[i * 2]:
                    if st.button(name, key=f"breadcrumb_{i}"):
                        st.session_state.disk_current_path = path
                        st.rerun()
                if i < len(breadcrumb) - 1:
                    with crumb_cols[i * 2 + 1]:
                        st.markdown("/", unsafe_allow_html=True)

        try:
            items = os.listdir(st.session_state.disk_current_path)
        except:
            items = []

        if not items:
            st.info("📭 Папка пуста. Загрузите файлы или создайте папку.")
        else:
            items.sort(key=lambda x: (not os.path.isdir(os.path.join(st.session_state.disk_current_path, x)), x.lower()))

            cols = st.columns(3)
            for idx, item in enumerate(items):
                with cols[idx % 3]:
                    item_path = os.path.join(st.session_state.disk_current_path, item)
                    is_dir = os.path.isdir(item_path)

                    if is_dir:
                        st.markdown(f"""
                        <div class="folder-card" style="text-align:center;">
                            <div style="font-size: 2.5rem;">📁</div>
                            <div style="font-weight: 600;">{item}</div>
                            <div style="color: #666;">Папка</div>
                        </div>
                        """, unsafe_allow_html=True)

                        if st.button(f"Открыть", key=f"open_{item}", use_container_width=True):
                            st.session_state.disk_current_path = item_path
                            st.rerun()
                    else:
                        file_size = os.path.getsize(item_path)
                        st.markdown(f"""
                        <div class="file-card" style="text-align:center;">
                            <div style="font-size: 2.5rem;">📄</div>
                            <div style="font-weight: 600;">{item}</div>
                            <div style="color: #666;">{format_file_size(file_size)}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        with open(item_path, 'rb') as f:
                            st.download_button("📥 Скачать", f.read(), item, use_container_width=True)

# ================= ПРОФИЛЬ =================
elif st.session_state.page == "Профиль":
    if st.session_state.is_logged_in:
        st.markdown('<div class="giant-id-title">ZORNET ID</div>', unsafe_allow_html=True)
        
        user = st.session_state.user_data
        st.markdown(f"""
        <div class="profile-container">
            <div style="width:120px; height:120px; border-radius:60px; background:linear-gradient(135deg,#DAA520,#B8860B); 
                       margin:0 auto 20px; display:flex; align-items:center; justify-content:center; color:white; font-size:48px;">
                {user.get('first_name', '?')[0]}
            </div>
            <h2 style="margin:0 0 8px 0;">{user.get('first_name', '')} {user.get('last_name', '')}</h2>
            <p style="color:#666; margin:0 0 16px 0;">@{user.get('username', '')}</p>
            <p style="background:#f8f9fa; padding:12px; border-radius:24px; color:#333;">✉️ {user.get('email', '')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚪 Выйти из аккаунта", type="primary", use_container_width=True):
            save_quick_links(st.session_state.quick_links)
            st.session_state.is_logged_in = False
            st.session_state.user_data = {}
            st.session_state.quick_links = [
                {"name": "YouTube", "url": "https://www.youtube.com", "icon": "📺"},
                {"name": "Gmail", "url": "https://mail.google.com", "icon": "📧"},
            ]
            st.session_state.page = "Главная"
            
            storage = load_storage()
            if "current_auth" in storage:
                storage["current_auth"]["is_logged_in"] = False
                save_storage(storage)
            
            st.rerun()
    
    else:
        st.markdown('<div class="giant-id-title">ZORNET ID</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        st.markdown("""
        <style>
            .stTabs [data-baseweb="tab-list"] {
                gap: 8px;
                background: white;
                padding: 4px;
                border-radius: 48px;
                border: 1px solid #e8eaed;
                margin-bottom: 32px;
            }
            .stTabs [data-baseweb="tab"] {
                border-radius: 40px;
                padding: 10px 24px;
                font-weight: 500;
                color: #5f6368;
            }
            .stTabs [aria-selected="true"] {
                background: linear-gradient(135deg, #DAA520, #B8860B) !important;
                color: white !important;
            }
            .stTextInput input {
                border: 1px solid #dadce0 !important;
                border-radius: 24px !important;
                padding: 14px 18px !important;
                font-size: 16px !important;
            }
            .stTextInput input:focus {
                border-color: #DAA520 !important;
                box-shadow: 0 1px 6px rgba(218, 165, 32, 0.3) !important;
            }
        </style>
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Вход", "Регистрация"])
        
        with tab1:
            st.markdown("### Вход в аккаунт")
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Пароль", type="password", key="login_password")
            
            if st.button("Войти", use_container_width=True):
                if login_email and login_password:
                    user = login_user(login_email, login_password)
                    if user:
                        st.session_state.user_data = user
                        st.session_state.is_logged_in = True
                        
                        saved_links = load_quick_links()
                        if saved_links:
                            st.session_state.quick_links = saved_links
                        
                        storage = load_storage()
                        storage["current_auth"] = {"is_logged_in": True, "user_data": user}
                        save_storage(storage)
                        
                        st.success("✅ Вход выполнен!")
                        st.session_state.page = "Главная"
                        st.rerun()
                    else:
                        st.error("❌ Неверный email или пароль")
        
        with tab2:
            st.markdown("### Регистрация")
            
            if st.session_state.registration_success:
                st.markdown(f"""
                <div style="background:#f1f3f4; padding:24px; border-radius:24px; text-align:center;">
                    <div style="font-size:48px; margin-bottom:16px;">✅</div>
                    <div style="font-size:20px; font-weight:500; margin-bottom:8px;">{st.session_state.registration_message}</div>
                    <div style="color:#5f6368; margin-bottom:24px;">Теперь войдите в аккаунт</div>
                    <div style="background:white; padding:16px; border-radius:16px;">
                        <div style="margin-bottom:8px;">📧 {st.session_state.new_user_email}</div>
                        <div>👤 @{st.session_state.new_user_username}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("➡️ Перейти ко входу", use_container_width=True):
                    st.session_state.registration_success = False
                    st.rerun()
            else:
                reg_email = st.text_input("Email", key="reg_email")
                reg_username = st.text_input("Никнейм", key="reg_username")
                reg_first_name = st.text_input("Имя", key="reg_first")
                reg_last_name = st.text_input("Фамилия (необязательно)", key="reg_last")
                reg_password = st.text_input("Пароль", type="password", key="reg_pass")
                reg_password_confirm = st.text_input("Повторите пароль", type="password", key="reg_pass2")
                
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
                            st.session_state.new_user_email = result["email"]
                            st.session_state.new_user_username = result["username"]
                            st.rerun()
                        else:
                            st.error(f"❌ {result['message']}")
        
        st.markdown('</div>', unsafe_allow_html=True)

# ================= ИНИЦИАЛИЗАЦИЯ БД =================
if __name__ == "__main__":
    init_db()
    
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE username = 'test'")
    if c.fetchone()[0] == 0:
        test_password = hashlib.sha256("test123".encode()).hexdigest()
        c.execute("INSERT INTO users (email, username, first_name, last_name, password_hash) VALUES (?, ?, ?, ?, ?)",
                 ("test@zornet.by", "test", "Тест", "Пользователь", test_password))
        conn.commit()
    conn.close()
