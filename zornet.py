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

# Загружаем состояние входа
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
    /* ОСНОВНЫЕ НАСТРОЙКИ */
    .main {
        background: #ffffff;
    }
    
    .stApp {
        background: #ffffff;
    }

    /* ГЛАВНЫЙ ЗАГОЛОВОК */
    .gold-title {
        font-family: 'Google Sans', 'Helvetica Neue', sans-serif;
        font-size: 3.5rem;
        font-weight: 500;
        text-align: center;
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
        margin: 20px 0 30px 0;
    }

    /* КНОПКИ НАВИГАЦИИ В САЙДБАРЕ */
    section[data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: none !important;
        color: #5f6368 !important;
        font-weight: 400 !important;
        text-align: left !important;
        padding: 12px 20px !important;
        margin: 2px 0 !important;
        border-radius: 0 25px 25px 0 !important;
        transition: all 0.2s ease !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #f1f3f4 !important;
        color: #DAA520 !important;
    }
    
    /* КНОПКИ НА ГЛАВНОЙ */
    div.stButton > button {
        background: #ffffff !important;
        border: 1px solid #e8eaed !important;
        color: #3c4043 !important;
        padding: 16px !important;
        border-radius: 12px !important;
        font-weight: 400 !important;
        font-size: 14px !important;
        width: 100% !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
        transition: all 0.2s ease !important;
    }

    div.stButton > button:hover {
        border-color: #DAA520 !important;
        box-shadow: 0 4px 12px rgba(218, 165, 32, 0.15) !important;
        background: #ffffff !important;
    }

    /* КАРТОЧКИ БЫСТРЫХ ССЫЛОК */
    .quick-link-card {
        background: #ffffff;
        border: 1px solid #f1f3f4;
        border-radius: 16px;
        padding: 20px 16px;
        margin: 8px 0;
        transition: all 0.2s ease;
        position: relative;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    
    .quick-link-card:hover {
        border-color: #DAA520;
        box-shadow: 0 8px 20px rgba(0,0,0,0.05);
        transform: translateY(-2px);
    }
    
    .quick-link-icon {
        font-size: 32px;
        text-align: center;
        margin-bottom: 12px;
        color: #DAA520;
    }
    
    .quick-link-name {
        font-weight: 500;
        font-size: 14px;
        color: #3c4043;
        text-align: center;
        margin-bottom: 4px;
    }
    
    .quick-link-url {
        font-size: 11px;
        color: #80868b;
        text-align: center;
        word-break: break-all;
        margin-bottom: 12px;
    }
    
    /* ПОЛЕ ВВОДА ГОРОДА */
    .city-input {
        border: 1px solid #e8eaed !important;
        border-radius: 24px !important;
        padding: 12px 20px !important;
        font-size: 16px !important;
        transition: all 0.2s ease !important;
    }
    
    .city-input:focus {
        border-color: #DAA520 !important;
        box-shadow: 0 4px 12px rgba(218, 165, 32, 0.15) !important;
        outline: none !important;
    }
    
    /* КНОПКА ПОИСКА ПОГОДЫ */
    .weather-search-btn {
        background: linear-gradient(135deg, #DAA520, #B8860B) !important;
        border: none !important;
        color: white !important;
        border-radius: 24px !important;
        padding: 12px 24px !important;
        font-weight: 500 !important;
        font-size: 16px !important;
        width: 100% !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 12px rgba(218, 165, 32, 0.2) !important;
    }
    
    .weather-search-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(218, 165, 32, 0.3) !important;
    }

    /* КАРТОЧКА ПОГОДЫ */
    .weather-card {
        background: linear-gradient(135deg, #f8f9fa, #ffffff);
        border-radius: 24px;
        padding: 30px;
        margin: 20px 0;
        border: 1px solid #e8eaed;
        box-shadow: 0 4px 20px rgba(0,0,0,0.02);
    }
    
    .weather-temp {
        font-size: 64px;
        font-weight: 300;
        color: #202124;
        line-height: 1;
    }
    
    .weather-desc {
        font-size: 20px;
        color: #5f6368;
        margin-top: 8px;
    }
    
    .weather-detail-item {
        background: #f8f9fa;
        border-radius: 16px;
        padding: 16px;
        border: 1px solid #e8eaed;
    }
    
    /* КАРТОЧКИ ПРОГНОЗА */
    .forecast-card {
        background: linear-gradient(135deg, #f8f9fa, #ffffff);
        border-radius: 20px;
        padding: 20px 12px;
        text-align: center;
        border: 1px solid #e8eaed;
        transition: all 0.2s ease;
    }
    
    .forecast-card:hover {
        border-color: #DAA520;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    
    /* ГОРОДА БЕЛАРУСИ */
    .city-btn {
        background: #ffffff !important;
        border: 1px solid #e8eaed !important;
        color: #3c4043 !important;
        padding: 12px !important;
        border-radius: 12px !important;
        font-weight: 400 !important;
        margin: 4px 0 !important;
        transition: all 0.2s ease !important;
    }
    
    .city-btn:hover {
        border-color: #DAA520 !important;
        background: #f8f9fa !important;
        transform: translateY(-1px);
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }

    /* МЕССЕНДЖЕР */
    .chat-header {
        background: #ffffff;
        padding: 16px;
        border-radius: 12px;
        border: 1px solid #e8eaed;
        margin-bottom: 16px;
    }
    
    .message-you {
        background: #f1f3f4;
        color: #202124;
        padding: 12px 18px;
        border-radius: 20px 20px 4px 20px;
        max-width: 70%;
        margin-left: auto;
        margin-bottom: 8px;
    }
    
    .message-other {
        background: #ffffff;
        color: #202124;
        padding: 12px 18px;
        border-radius: 20px 20px 20px 4px;
        max-width: 70%;
        margin-right: auto;
        margin-bottom: 8px;
        border: 1px solid #e8eaed;
    }

    /* ДИСК */
    .disk-stats {
        background: #f8f9fa;
        border-radius: 20px;
        padding: 20px;
        border: 1px solid #e8eaed;
        margin: 20px 0;
    }
    
    .file-card {
        background: #ffffff;
        border: 1px solid #e8eaed;
        border-radius: 16px;
        padding: 16px;
        transition: all 0.2s ease;
    }
    
    .file-card:hover {
        border-color: #DAA520;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        transform: translateY(-2px);
    }
    
    .folder-card {
        background: #f8f9fa;
        border: 1px solid #e8eaed;
        border-radius: 16px;
        padding: 16px;
        transition: all 0.2s ease;
    }
    
    .folder-card:hover {
        border-color: #DAA520;
        transform: translateY(-2px);
    }

    /* НОВОСТИ */
    .news-item {
        background: #ffffff;
        border: 1px solid #e8eaed;
        border-radius: 20px;
        padding: 20px;
        margin-bottom: 16px;
        transition: all 0.2s ease;
    }
    
    .news-item:hover {
        border-color: #DAA520;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        transform: translateY(-2px);
    }
    
    .news-title {
        color: #1a73e8;
        font-size: 18px;
        font-weight: 500;
        text-decoration: none;
    }
    
    .news-title:hover {
        color: #DAA520;
    }

    /* ПРОФИЛЬ */
    .profile-card {
        background: #ffffff;
        border-radius: 32px;
        padding: 48px;
        border: 1px solid #e8eaed;
        text-align: center;
        max-width: 500px;
        margin: 0 auto;
        box-shadow: 0 10px 30px rgba(0,0,0,0.02);
    }
    
    .profile-name {
        font-size: 28px;
        font-weight: 400;
        color: #202124;
        margin: 16px 0 8px;
    }
    
    .profile-username {
        color: #5f6368;
        font-size: 16px;
        margin-bottom: 16px;
    }
    
    .profile-email {
        color: #80868b;
        font-size: 14px;
        padding: 12px;
        background: #f8f9fa;
        border-radius: 12px;
        border: 1px solid #e8eaed;
    }

    /* ЛОГИН */
    .login-container {
        max-width: 400px;
        margin: 40px auto;
        padding: 40px;
        background: #ffffff;
        border-radius: 32px;
        border: 1px solid #e8eaed;
        box-shadow: 0 10px 40px rgba(0,0,0,0.02);
    }

    /* РАЗДЕЛИТЕЛИ */
    hr {
        margin: 32px 0;
        border: none;
        border-top: 1px solid #e8eaed;
    }
    
    /* ЗАГОЛОВКИ СЕКЦИЙ */
    .section-title {
        color: #202124;
        font-size: 20px;
        font-weight: 400;
        margin: 24px 0 16px;
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
    except:
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
    st.markdown("<h3 style='color:#DAA520; font-weight:400; margin-bottom:20px;'>ZORNET</h3>", unsafe_allow_html=True)
    
    if st.session_state.is_logged_in:
        user = st.session_state.user_data
        st.markdown(f"""
        <div style="padding:12px; background:#f8f9fa; border-radius:12px; margin-bottom:16px;">
            <div style="font-weight:500;">👤 {user.get('first_name', '')} {user.get('last_name', '')}</div>
            <div style="color:#5f6368; font-size:13px;">@{user.get('username', '')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    pages = [
        ("🏠", "Главная", "Главная"),
        ("📰", "Новости", "Новости"),
        ("🌤️", "Погода", "Погода"),
        ("💬", "Мессенджер", "Мессенджер"),
        ("🎬", "Кинотеатр", "Кинотеатр"),
        ("💾", "Диск", "Диск"),
        ("👤", "Профиль", "Профиль"),
    ]
    
    for icon, text, page in pages:
        if st.button(f"{icon} {text}", key=f"nav_{page}", use_container_width=True):
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
    except:
        return None
    
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
        response = requests.get("https://www.belta.by/ru/rss", headers=headers, timeout=10)
        feed = feedparser.parse(response.content)
        return feed.entries[:5]
    except:
        return [
            {"title": "Новости Беларуси", "link": "#", "summary": "Следите за обновлениями на портале"},
            {"title": "Экономические новости", "link": "#", "summary": "Развитие экономики страны"},
            {"title": "Спортивные события", "link": "#", "summary": "Последние спортивные новости"},
        ]

# ================= СТРАНИЦА ГЛАВНАЯ =================
if st.session_state.page == "Главная":
    st.markdown('<div class="gold-title">ZORNET</div>', unsafe_allow_html=True)
    
    current_time = datetime.datetime.now(pytz.timezone('Europe/Minsk')).strftime('%H:%M')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button(f"🕒 {current_time}\nМинск", key="time_btn", use_container_width=True):
            pass
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
    
    components.html("""
    <div style="display:flex; justify-content:center; margin:20px 0;">
        <form action="https://www.google.com/search" method="get" target="_blank" style="width:100%; max-width:600px;">
            <input type="text" name="q" placeholder="🔍 Поиск в Google" 
                   style="width:100%; padding:16px 24px; border:1px solid #e8eaed; border-radius:24px; 
                          font-size:16px; outline:none; transition:all 0.2s ease;"
                   onfocus="this.style.borderColor='#DAA520'; this.style.boxShadow='0 4px 12px rgba(218,165,32,0.15)'"
                   onblur="this.style.borderColor='#e8eaed'; this.style.boxShadow='none'">
        </form>
    </div>
    """, height=80)
    
    st.markdown("---")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<div class="section-title">📌 Быстрые ссылки</div>', unsafe_allow_html=True)
    with col2:
        if st.button("➕ Добавить", key="add_link_top", use_container_width=True):
            st.session_state.show_add_link = not st.session_state.show_add_link
            st.rerun()
    
    if st.session_state.quick_links:
        for i in range(0, len(st.session_state.quick_links), 4):
            cols = st.columns(4)
            for j, link in enumerate(st.session_state.quick_links[i:i+4]):
                with cols[j]:
                    st.markdown(f"""
                    <div class="quick-link-card">
                        <div class="quick-link-icon">{link.get('icon', '🔗')}</div>
                        <div class="quick-link-name">{link['name']}</div>
                        <div class="quick-link-url">{link['url'][:20]}...</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col_open, col_del = st.columns(2)
                    with col_open:
                        if st.button("🌐", key=f"open_{i}_{j}", help="Открыть"):
                            js_code = f'window.open("{link["url"]}", "_blank");'
                            components.html(f"<script>{js_code}</script>", height=0)
                    with col_del:
                        if st.button("✕", key=f"del_{i}_{j}", help="Удалить"):
                            st.session_state.quick_links.remove(link)
                            save_quick_links(st.session_state.quick_links)
                            st.rerun()
    else:
        st.info("📭 Нет быстрых ссылок. Нажмите 'Добавить', чтобы создать первую.")
    
    if st.session_state.show_add_link:
        st.markdown("---")
        st.markdown('<div class="section-title">📝 Новая ссылка</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([2, 3, 1])
        with col1:
            name = st.text_input("Название", placeholder="YouTube", key="new_name")
        with col2:
            url = st.text_input("URL", placeholder="https://youtube.com", key="new_url")
        with col3:
            icon = st.selectbox("Иконка", ["🔍", "📺", "📧", "🤖", "💻", "🌐", "🎮"], key="new_icon")
        
        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.button("💾 Сохранить", use_container_width=True):
                if name and url:
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                    st.session_state.quick_links.append({"name": name, "url": url, "icon": icon})
                    save_quick_links(st.session_state.quick_links)
                    st.session_state.show_add_link = False
                    st.rerun()
        with col_cancel:
            if st.button("✕ Отмена", use_container_width=True):
                st.session_state.show_add_link = False
                st.rerun()

# ================= СТРАНИЦА НОВОСТЕЙ =================
elif st.session_state.page == "Новости":
    st.markdown('<div class="gold-title">📰 НОВОСТИ</div>', unsafe_allow_html=True)
    
    with st.spinner("Загрузка новостей..."):
        news = get_belta_news()
        
        for item in news:
            st.markdown(f"""
            <div class="news-item">
                <a href="{item.link}" target="_blank" class="news-title">{item.title}</a>
                <p style="color:#5f6368; margin-top:8px;">{item.summary[:200]}...</p>
            </div>
            """, unsafe_allow_html=True)

# ================= СТРАНИЦА ПОГОДЫ =================
elif st.session_state.page == "Погода":
    st.markdown('<div class="gold-title">🌤️ ПОГОДА</div>', unsafe_allow_html=True)
    
    st.markdown('<div style="max-width:600px; margin:0 auto 30px;">', unsafe_allow_html=True)
    col1, col2 = st.columns([4, 1])
    
    with col1:
        city_input = st.text_input("Город", placeholder="🔍 Введите город...", 
                                   label_visibility="collapsed", key="city_search")
    with col2:
        search_clicked = st.button("🔍 Найти", key="search_weather", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    city_to_show = st.session_state.user_city if st.session_state.user_city else "Минск"
    
    if search_clicked and city_input:
        city_to_show = city_input
        st.session_state.user_city = city_input
    
    with st.spinner(f"Получение погоды для {city_to_show}..."):
        weather_data = get_weather_by_city(city_to_show)
        
        if not weather_data:
            st.error(f"❌ Город '{city_to_show}' не найден")
            weather_data = get_weather_by_city("Минск")
            if weather_data:
                st.info("Показана погода для Минска")
        
        if weather_data:
            current = weather_data["current"]
            st.session_state.user_city = current['city']
            
            st.markdown(f"""
            <div style="text-align:center; margin-bottom:20px;">
                <div style="font-size:32px; color:#202124;">{current['city']}, {current['country']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown(f"""
                <div style="text-align:center;">
                    <div style="font-size:80px; font-weight:300;">{current['temp']}°</div>
                    <div style="font-size:24px; color:#5f6368;">{get_weather_icon(current['icon'])} {current['description']}</div>
                    <div style="font-size:16px; color:#80868b;">Ощущается как {current['feels_like']}°</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="background:#f8f9fa; border-radius:24px; padding:20px;">
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                        <div><span style="color:#80868b;">💧 Влажность</span><br><span style="font-size:20px;">{current['humidity']}%</span></div>
                        <div><span style="color:#80868b;">💨 Ветер</span><br><span style="font-size:20px;">{current['wind_speed']} м/с</span></div>
                        <div><span style="color:#80868b;">📊 Давление</span><br><span style="font-size:20px;">{current['pressure']} гПа</span></div>
                        <div><span style="color:#80868b;">👁️ Видимость</span><br><span style="font-size:20px;">{current['visibility']} км</span></div>
                        <div><span style="color:#80868b;">🌅 Восход</span><br><span style="font-size:20px;">{current['sunrise']}</span></div>
                        <div><span style="color:#80868b;">🌇 Закат</span><br><span style="font-size:20px;">{current['sunset']}</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            if weather_data.get("forecast"):
                st.markdown('<div class="section-title" style="margin-top:40px;">📅 Прогноз на 5 дней</div>', unsafe_allow_html=True)
                
                forecast = weather_data["forecast"]["list"]
                days = {}
                for item in forecast:
                    date = item["dt_txt"].split(" ")[0]
                    if date not in days:
                        days[date] = item
                
                cols = st.columns(5)
                for idx, (date, day_data) in enumerate(list(days.items())[:5]):
                    with cols[idx]:
                        day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][
                            datetime.datetime.strptime(date, "%Y-%m-%d").weekday()
                        ]
                        st.markdown(f"""
                        <div class="forecast-card">
                            <div style="color:#5f6368;">{day_name}</div>
                            <div style="font-size:36px; margin:8px 0;">{get_weather_icon(day_data['weather'][0]['icon'])}</div>
                            <div style="font-size:20px;">{round(day_data['main']['temp'])}°</div>
                        </div>
                        """, unsafe_allow_html=True)
            
            st.markdown('<div class="section-title" style="margin-top:40px;">🇧🇾 Города Беларуси</div>', unsafe_allow_html=True)
            
            belarus_cities = ["Минск", "Гомель", "Витебск", "Могилёв", "Брест", "Гродно", 
                            "Бобруйск", "Барановичи", "Борисов", "Пинск", "Орша", "Мозырь"]
            
            cols = st.columns(4)
            for idx, city in enumerate(belarus_cities):
                with cols[idx % 4]:
                    if st.button(city, key=f"city_{city}", use_container_width=True):
                        st.session_state.user_city = city
                        st.rerun()

# ================= МЕССЕНДЖЕР =================
elif st.session_state.page == "Мессенджер":
    st.markdown('<div class="gold-title">💬 МЕССЕНДЖЕР</div>', unsafe_allow_html=True)
    
    if not st.session_state.is_logged_in:
        st.warning("⚠️ Войдите в систему для использования мессенджера")
        if st.button("🔑 Войти", use_container_width=True):
            st.session_state.page = "Профиль"
            st.rerun()
    else:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown('<div class="section-title">🔍 Поиск</div>', unsafe_allow_html=True)
            search = st.text_input("Никнейм", placeholder="@username", label_visibility="collapsed")
            
            if st.button("🔍 Найти", use_container_width=True) and search:
                if search == st.session_state.user_data.get("username"):
                    st.error("Нельзя написать самому себе")
                else:
                    user = get_user_by_username(search)
                    if user:
                        st.session_state.chat_partner = user
                        st.rerun()
                    else:
                        st.error("Пользователь не найден")
            
            st.markdown('<div class="section-title" style="margin-top:20px;">📞 Контакты</div>', unsafe_allow_html=True)
            
            contacts = [
                {"username": "alex", "first_name": "Алексей"},
                {"username": "marina", "first_name": "Марина"},
                {"username": "dmitry", "first_name": "Дмитрий"},
            ]
            
            for contact in contacts:
                if st.button(f"👤 {contact['first_name']}\n@{contact['username']}", 
                           key=f"contact_{contact['username']}", use_container_width=True):
                    st.session_state.chat_partner = {"username": contact['username'], 
                                                     "first_name": contact['first_name']}
                    st.rerun()
        
        with col2:
            if st.session_state.chat_partner:
                partner = st.session_state.chat_partner
                
                st.markdown(f"""
                <div class="chat-header">
                    <div style="display:flex; align-items:center; gap:12px;">
                        <div style="width:40px; height:40px; border-radius:50%; 
                                  background:linear-gradient(135deg,#DAA520,#B8860B); 
                                  display:flex; align-items:center; justify-content:center;
                                  color:white; font-weight:500;">
                            {partner.get('first_name', '?')[0]}
                        </div>
                        <div>
                            <div style="font-weight:500;">{partner.get('first_name', '')}</div>
                            <div style="color:#5f6368;">@{partner.get('username', '')}</div>
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
                        if msg.get("sender") == current_user:
                            st.markdown(f"""
                            <div class="message-you">
                                {msg['text']}
                                <div style="font-size:10px; color:#80868b; text-align:right;">{msg['time'][11:16]}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="message-other">
                                {msg['text']}
                                <div style="font-size:10px; color:#80868b; text-align:right;">{msg['time'][11:16]}</div>
                            </div>
                            """, unsafe_allow_html=True)
                
                col_input, col_send = st.columns([5, 1])
                with col_input:
                    new_msg = st.text_input("Сообщение", placeholder="Введите сообщение...", 
                                          label_visibility="collapsed", key="new_msg")
                with col_send:
                    if st.button("📤", use_container_width=True) and new_msg:
                        save_chat_message(current_user, partner_user, new_msg)
                        st.session_state.messages[chat_key].append({
                            "sender": current_user, "text": new_msg,
                            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                        st.rerun()
            else:
                st.info("👈 Выберите пользователя для начала общения")

# ================= КИНОТЕАТР =================
elif st.session_state.page == "Кинотеатр":
    st.markdown('<div class="gold-title">🎬 КИНОТЕАТР</div>', unsafe_allow_html=True)
    
    if not st.session_state.is_logged_in:
        st.warning("⚠️ Войдите в систему для создания комнат")
        if st.button("🔑 Войти", use_container_width=True):
            st.session_state.page = "Профиль"
            st.rerun()
    elif st.session_state.get("watch_room"):
        room_id = st.session_state.watch_room
        room_data = None
        
        for room in st.session_state.rooms:
            if room["id"] == room_id:
                room_data = room
                break
        
        if room_data:
            video_url = room_data.get("youtube_url", "")
            video_id = None
            
            patterns = [
                r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([0-9A-Za-z_-]{11})',
                r'youtube\.com\/embed\/([0-9A-Za-z_-]{11})'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, video_url)
                if match:
                    video_id = match.group(1)
                    break
            
            st.markdown(f"""
            <div style="margin-bottom:20px;">
                <div style="font-size:24px;">🎥 {room_data['name']}</div>
                <div style="color:#5f6368;">ID: {room_id} · Создатель: @{room_data['owner']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if video_id:
                components.html(f"""
                <iframe width="100%" height="500" 
                        src="https://www.youtube.com/embed/{video_id}?autoplay=1"
                        frameborder="0" allowfullscreen style="border-radius:16px;">
                </iframe>
                """, height=520)
            
            st.markdown('<div class="section-title">💬 Чат комнаты</div>', unsafe_allow_html=True)
            
            room_chat = f"room_{room_id}"
            if room_chat not in st.session_state.room_messages:
                st.session_state.room_messages[room_chat] = []
            
            chat_container = st.container(height=200)
            with chat_container:
                for msg in st.session_state.room_messages[room_chat]:
                    st.markdown(f"""
                    <div style="margin:8px 0;">
                        <span style="font-weight:500;">{msg['username']}:</span> {msg['message']}
                        <span style="color:#80868b; font-size:11px; margin-left:8px;">{msg['timestamp']}</span>
                    </div>
                    """, unsafe_allow_html=True)
            
            col_msg, col_send = st.columns([5, 1])
            with col_msg:
                room_msg = st.text_input("Сообщение", placeholder="Ваше сообщение...", 
                                       label_visibility="collapsed", key="room_msg")
            with col_send:
                if st.button("📤", use_container_width=True) and room_msg:
                    username = st.session_state.user_data.get("username", "Гость")
                    save_room_message(room_chat, username, room_msg)
                    save_room_message_to_db(room_id, username, room_msg)
                    st.rerun()
            
            if st.button("← Выйти из комнаты", use_container_width=True):
                st.session_state.watch_room = None
                st.rerun()
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="section-title">🎥 Создать комнату</div>', unsafe_allow_html=True)
            name = st.text_input("Название", placeholder="Моя комната", key="room_name")
            url = st.text_input("YouTube ссылка", placeholder="https://youtube.com/watch?v=...", key="room_url")
            password = st.text_input("Пароль", type="password", key="room_pass")
            
            if st.button("Создать", use_container_width=True) and name and url and password:
                room_id = str(uuid.uuid4())[:8]
                owner = st.session_state.user_data.get("username", "Гость")
                
                if create_watch_room(room_id, name, url, password, owner):
                    st.session_state.rooms.append({
                        "id": room_id, "name": name, "youtube_url": url,
                        "password": password, "owner": owner
                    })
                    st.session_state.watch_room = room_id
                    st.rerun()
        
        with col2:
            st.markdown('<div class="section-title">🔗 Присоединиться</div>', unsafe_allow_html=True)
            join_id = st.text_input("ID комнаты", placeholder="XXXXXXXX", key="join_id")
            join_pass = st.text_input("Пароль", type="password", key="join_pass")
            
            if st.button("Присоединиться", use_container_width=True) and join_id and join_pass:
                room = get_watch_room(join_id, join_pass)
                if room:
                    st.session_state.watch_room = room["id"]
                    st.rerun()
                else:
                    st.error("❌ Комната не найдена или неверный пароль")

# ================= ДИСК =================
elif st.session_state.page == "Диск":
    st.markdown('<div class="gold-title">💾 ДИСК</div>', unsafe_allow_html=True)
    
    os.makedirs(st.session_state.disk_current_path, exist_ok=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📤 Загрузить", key="disk_upload", use_container_width=True):
            st.session_state.disk_action = "upload"
    with col2:
        if st.button("📁 Новая папка", key="disk_folder", use_container_width=True):
            st.session_state.disk_action = "new_folder"
    with col3:
        if st.button("🔍 Поиск", key="disk_search", use_container_width=True):
            st.session_state.disk_action = "search"
    with col4:
        if st.button("🔄 Обновить", key="disk_refresh", use_container_width=True):
            st.rerun()
    
    stats = get_disk_stats()
    used_gb = stats['total_size'] / (1024 * 1024 * 1024)
    used_percent = min(100, (used_gb / 1.0) * 100)
    
    st.markdown(f"""
    <div class="disk-stats">
        <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
            <span>Использовано: {format_file_size(stats['total_size'])}</span>
            <span>Лимит: 1.0 GB</span>
        </div>
        <div style="height:6px; background:#e8eaed; border-radius:3px;">
            <div style="width:{used_percent}%; height:100%; background:linear-gradient(90deg,#DAA520,#B8860B); border-radius:3px;"></div>
        </div>
        <div style="display:flex; gap:20px; margin-top:12px; color:#5f6368;">
            <span>📁 {stats['folder_count']} папок</span>
            <span>📄 {stats['file_count']} файлов</span>
            <span>📊 Свободно: {format_file_size(1073741824 - stats['total_size'])}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.disk_action == "upload":
        st.markdown('<div class="section-title">📤 Загрузка файлов</div>', unsafe_allow_html=True)
        files = st.file_uploader("Выберите файлы", accept_multiple_files=True, label_visibility="collapsed")
        
        if files:
            for file in files:
                path = os.path.join(st.session_state.disk_current_path, file.name)
                with open(path, "wb") as f:
                    f.write(file.getbuffer())
            st.success(f"✅ Загружено {len(files)} файлов")
            st.session_state.disk_action = "view"
            st.rerun()
        
        if st.button("← Назад", use_container_width=True):
            st.session_state.disk_action = "view"
            st.rerun()
    
    elif st.session_state.disk_action == "new_folder":
        st.markdown('<div class="section-title">📁 Новая папка</div>', unsafe_allow_html=True)
        folder = st.text_input("Название папки", placeholder="Моя папка", key="new_folder_name")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Создать", use_container_width=True) and folder:
                path = os.path.join(st.session_state.disk_current_path, folder)
                os.makedirs(path, exist_ok=True)
                st.session_state.disk_action = "view"
                st.rerun()
        with col2:
            if st.button("← Назад", use_container_width=True):
                st.session_state.disk_action = "view"
                st.rerun()
    
    elif st.session_state.disk_action == "search":
        st.markdown('<div class="section-title">🔍 Поиск</div>', unsafe_allow_html=True)
        query = st.text_input("Что ищем?", placeholder="Название файла...", key="search_query")
        
        if query:
            found = []
            for root, dirs, files in os.walk(st.session_state.disk_current_path):
                for name in dirs + files:
                    if query.lower() in name.lower():
                        found.append({"name": name, "path": os.path.join(root, name)})
            
            if found:
                for item in found[:10]:
                    st.markdown(f"📄 {item['name']}")
            else:
                st.info("Ничего не найдено")
        
        if st.button("← Назад", use_container_width=True):
            st.session_state.disk_action = "view"
            st.rerun()
    
    else:
        st.markdown('<div class="section-title">📁 Текущая папка</div>', unsafe_allow_html=True)
        
        if st.session_state.disk_current_path != "zornet_cloud":
            parts = st.session_state.disk_current_path.split(os.sep)
            path_parts = []
            current = ""
            for part in parts:
                if part:
                    current = os.path.join(current, part) if current else part
                    path_parts.append((part, current))
            
            cols = st.columns(len(path_parts) * 2 - 1)
            for i, (name, path) in enumerate(path_parts):
                with cols[i*2]:
                    if st.button(name, key=f"path_{i}"):
                        st.session_state.disk_current_path = path
                        st.rerun()
                if i < len(path_parts) - 1:
                    with cols[i*2 + 1]:
                        st.markdown("›")
        
        items = os.listdir(st.session_state.disk_current_path) if os.path.exists(st.session_state.disk_current_path) else []
        
        if not items:
            st.info("📭 Папка пуста")
        else:
            items.sort(key=lambda x: (not os.path.isdir(os.path.join(st.session_state.disk_current_path, x)), x.lower()))
            
            cols = st.columns(3)
            for idx, item in enumerate(items):
                with cols[idx % 3]:
                    path = os.path.join(st.session_state.disk_current_path, item)
                    is_dir = os.path.isdir(path)
                    
                    if is_dir:
                        st.markdown(f"""
                        <div class="folder-card" style="text-align:center;">
                            <div style="font-size:32px;">📁</div>
                            <div style="font-weight:500;">{item}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button("📂 Открыть", key=f"open_{item}", use_container_width=True):
                            st.session_state.disk_current_path = path
                            st.rerun()
                    else:
                        size = os.path.getsize(path)
                        st.markdown(f"""
                        <div class="file-card" style="text-align:center;">
                            <div style="font-size:32px;">📄</div>
                            <div style="font-weight:500;">{item}</div>
                            <div style="color:#5f6368; font-size:12px;">{format_file_size(size)}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        with open(path, 'rb') as f:
                            st.download_button("📥 Скачать", f.read(), item, use_container_width=True)

# ================= ПРОФИЛЬ =================
elif st.session_state.page == "Профиль":
    if st.session_state.is_logged_in:
        st.markdown('<div class="gold-title">👤 ПРОФИЛЬ</div>', unsafe_allow_html=True)
        
        user = st.session_state.user_data
        
        st.markdown(f"""
        <div class="profile-card">
            <div style="width:80px; height:80px; border-radius:50%; background:linear-gradient(135deg,#DAA520,#B8860B); 
                       margin:0 auto; display:flex; align-items:center; justify-content:center; color:white; font-size:32px;">
                {user.get('first_name', '?')[0]}
            </div>
            <div class="profile-name">{user.get('first_name', '')} {user.get('last_name', '')}</div>
            <div class="profile-username">@{user.get('username', '')}</div>
            <div class="profile-email">✉️ {user.get('email', '')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚪 Выйти", use_container_width=True):
            save_quick_links(st.session_state.quick_links)
            st.session_state.is_logged_in = False
            st.session_state.user_data = {}
            st.session_state.page = "Главная"
            
            storage = load_storage()
            if "current_auth" in storage:
                storage["current_auth"]["is_logged_in"] = False
                storage["current_auth"]["user_data"] = {}
                save_storage(storage)
            
            st.rerun()
    
    else:
        st.markdown('<div class="gold-title">🔑 ВХОД</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Вход", "Регистрация"])
        
        with tab1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Пароль", type="password", key="login_password")
            
            if st.button("Войти", use_container_width=True):
                if email and password:
                    user = login_user(email, password)
                    if user:
                        st.session_state.user_data = user
                        st.session_state.is_logged_in = True
                        
                        saved = load_quick_links()
                        if saved:
                            st.session_state.quick_links = saved
                        
                        storage = load_storage()
                        storage["current_auth"] = {"is_logged_in": True, "user_data": user}
                        save_storage(storage)
                        
                        st.session_state.page = "Главная"
                        st.rerun()
                    else:
                        st.error("❌ Неверный email или пароль")
        
        with tab2:
            if st.session_state.registration_success:
                st.markdown(f"""
                <div style="background:#f1f3f4; padding:20px; border-radius:16px; text-align:center;">
                    <div style="font-size:24px; margin-bottom:16px;">✅</div>
                    <div style="font-weight:500; margin-bottom:8px;">{st.session_state.registration_message}</div>
                    <div style="color:#5f6368; margin-bottom:16px;">Теперь войдите в аккаунт</div>
                    <div style="background:white; padding:12px; border-radius:12px;">
                        <div>📧 {st.session_state.new_user_email}</div>
                        <div>👤 @{st.session_state.new_user_username}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("➡️ Перейти ко входу", use_container_width=True):
                    st.session_state.registration_success = False
                    st.rerun()
            else:
                email = st.text_input("Email", key="reg_email")
                username = st.text_input("Никнейм", key="reg_username")
                first_name = st.text_input("Имя", key="reg_first")
                last_name = st.text_input("Фамилия (необязательно)", key="reg_last")
                password = st.text_input("Пароль", type="password", key="reg_pass")
                password2 = st.text_input("Повторите пароль", type="password", key="reg_pass2")
                
                if st.button("Создать аккаунт", use_container_width=True):
                    if not all([email, username, first_name, password, password2]):
                        st.error("❌ Заполните все обязательные поля")
                    elif password != password2:
                        st.error("❌ Пароли не совпадают")
                    elif len(password) < 6:
                        st.error("❌ Пароль должен быть не менее 6 символов")
                    else:
                        result = register_user(email, username, first_name, last_name, password)
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
        test_pass = hashlib.sha256("test123".encode()).hexdigest()
        c.execute("INSERT INTO users (email, username, first_name, last_name, password_hash) VALUES (?, ?, ?, ?, ?)",
                 ("test@zornet.by", "test", "Тест", "Пользователь", test_pass))
        conn.commit()
    conn.close()
