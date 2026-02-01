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

# ================= НАСТРОЙКИ =================
st.set_page_config(
    page_title="ZORNET",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None
)

# ================= СЕССИЯ =================
if "page" not in st.session_state:
    st.session_state.page = "Главная"
if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = []
if "weather_data" not in st.session_state:
    st.session_state.weather_data = None
if "user_city" not in st.session_state:
    st.session_state.user_city = "Минск"
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
if "chat_search_query" not in st.session_state:
    st.session_state.chat_search_query = ""
if "room_password" not in st.session_state:
    st.session_state.room_password = {}
if "weather_city_input" not in st.session_state:
    st.session_state.weather_city_input = ""

# ================= ИСПРАВЛЕННЫЕ CSS СТИЛИ =================
st.markdown("""
<style>
    /* ПОЛНОСТЬЮ УБИРАЕМ ХЕДЕР И БЕЛЫЙ ТРЕУГОЛЬНИК */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    .stApp {
        margin-top: -100px !important;
    }
    
    /* Кнопка сайдбара */
    [data-testid="collapsedControl"] {
        position: fixed !important;
        right: 20px !important;
        top: 20px !important;
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%) !important;
        border-radius: 8px !important;
        width: 45px !important;
        height: 45px !important;
        z-index: 10000 !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
    }

    /* ГЛАВНЫЙ ЗАГОЛОВОК */
    .gold-title {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 4rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(to bottom, #DAA520, #B8860B);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 4px;
        text-transform: uppercase;
        margin: 10px 0 30px 0;
    }

    /* КНОПКИ ГЛАВНОЙ */
    div.stButton > button {
        background: #f8f9fa !important;
        border: 1px solid #dee2e6 !important;
        color: #1a1a1a !important;
        padding: 20px !important; 
        border-radius: 12px !important;
        font-weight: bold !important;
        width: 100% !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
        height: 80px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        margin: 0 5px !important;
        font-size: 14px !important;
        line-height: 1.3 !important;
        white-space: pre-line !important;
        text-align: center !important;
    }

    /* ЗОЛОТАЯ КНОПКА */
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
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
        border-radius: 15px;
        padding: 20px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(218, 165, 32, 0.3);
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

    /* Диск */
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
    
    .file-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #DAA520;
    }
    
    .folder-card {
        background: linear-gradient(135deg, #fff9e6 0%, #ffe699 100%);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border: 2px solid #ffd966;
    }
    
    /* Профиль */
    .giant-id-title {
        font-size: 5rem !important;
        font-weight: 900 !important;
        text-align: center;
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 20px 0 40px 0 !important;
    }
    
    .profile-container {
        background: white;
        border-radius: 32px;
        padding: 40px;
        border: 1px solid #f0f0f0;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    
    /* Мессенджер */
    .messenger-container {
        display: flex;
        height: 700px;
        background: white;
        border-radius: 16px;
        border: 1px solid #e0e0e0;
        overflow: hidden;
    }
    
    .contacts-sidebar {
        width: 33.33%;
        border-right: 1px solid #e0e0e0;
        background: #f8f9fa;
        overflow-y: auto;
        padding: 10px;
    }
    
    .chat-area {
        width: 66.67%;
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
        border-radius: 8px;
        margin-bottom: 5px;
    }
    
    .contact-item:hover {
        background: #e9ecef;
    }
    
    .contact-item.active {
        background: #e3f2fd;
        border-left: 4px solid #DAA520;
    }
    
    .message-bubble {
        max-width: 70%;
        padding: 12px 16px;
        border-radius: 18px;
        margin-bottom: 8px;
    }
    
    .message-bubble.you {
        background: #DCF8C6;
        align-self: flex-end;
    }
    
    .message-bubble.other {
        background: white;
        align-self: flex-start;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .online-badge {
        width: 8px;
        height: 8px;
        background: #4CAF50;
        border-radius: 50%;
        display: inline-block;
        margin-left: 5px;
    }
    
    .offline-badge {
        width: 8px;
        height: 8px;
        background: #ccc;
        border-radius: 50%;
        display: inline-block;
        margin-left: 5px;
    }
    
    /* Логин */
    .login-container {
        max-width: 500px;
        margin: 50px auto;
        padding: 40px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
    }
    
    /* Исправление выравнивания */
    div[data-testid="column"] {
        align-items: center !important;
    }
    
    /* Скрываем все лишние элементы Streamlit */
    .st-emotion-cache-1dp5vir {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= БАЗА ДАННЫХ =================
def init_db():
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
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
            password_hash TEXT NOT NULL,
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
    """Регистрация пользователя"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
    c = conn.cursor()
    
    try:
        # Проверяем email
        c.execute("SELECT id FROM users WHERE email = ?", (email,))
        if c.fetchone():
            conn.close()
            return {"success": False, "message": "Email уже используется"}
        
        # Проверяем username
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        if c.fetchone():
            conn.close()
            return {"success": False, "message": "Никнейм уже занят"}
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        c.execute("""
            INSERT INTO users (email, username, first_name, last_name, password_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (email, username, first_name, last_name, password_hash))
        
        conn.commit()
        conn.close()
        return {"success": True, "message": "Аккаунт создан!"}
    except Exception as e:
        conn.close()
        return {"success": False, "message": f"Ошибка: {str(e)}"}

def login_user(email, password):
    """Вход пользователя"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
    c = conn.cursor()
    
    try:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        c.execute("""
            SELECT id, email, username, first_name, last_name
            FROM users 
            WHERE email = ? AND password_hash = ?
        """, (email, password_hash))
        
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
    except:
        conn.close()
        return None

def get_user_by_username(username):
    """Поиск пользователя по никнейму"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
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

def get_all_users_except(current_username):
    """Получить всех пользователей кроме текущего"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
    c = conn.cursor()
    
    c.execute("""
        SELECT id, username, first_name, last_name
        FROM users 
        WHERE username != ?
        ORDER BY username
    """, (current_username,))
    
    users = c.fetchall()
    conn.close()
    
    return [
        {
            "id": user[0],
            "username": user[1],
            "first_name": user[2],
            "last_name": user[3]
        }
        for user in users
    ]

def save_chat_message(sender, receiver, message):
    """Сохранение сообщения в чате"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO chat_messages (sender_username, receiver_username, message)
        VALUES (?, ?, ?)
    """, (sender, receiver, message))
    
    conn.commit()
    conn.close()

def get_chat_history(user1, user2):
    """Получение истории чата"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
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

# ================= САЙДБАР =================
with st.sidebar:
    st.markdown("<h3 style='color:#DAA520;'>ZORNET</h3>", unsafe_allow_html=True)
    
    if st.session_state.is_logged_in:
        user = st.session_state.user_data
        st.markdown(f"**👤 {user.get('first_name', '')} {user.get('last_name', '')}**")
        st.markdown(f"*@{user.get('username', '')}*")
        st.markdown("---")
    
    pages = [
        ("🏠", "ГЛАВНАЯ", "Главная"),
        ("💬", "МЕССЕНДЖЕР", "Мессенджер"),
        ("🎬", "СОВМЕСТНЫЙ ПРОСМОТР", "Совместный просмотр"),
        ("💾", "ДИСК", "Диск"),
        ("📰", "НОВОСТИ", "Новости"),
        ("🌤️", "ПОГОДА", "Погода"),
        ("👤", "ПРОФИЛЬ", "Профиль"),
    ]
    
    for i, (icon, text, page) in enumerate(pages):
        if st.button(f"{icon} {text}", key=f"nav_{i}", use_container_width=True):
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
        st.markdown(f'<div class="time-widget">🕒 {current_time}<br>Минск</div>', unsafe_allow_html=True)
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
        st.warning("⚠️ Вы не авторизованы. Перейдите в профиль для входа.")
    
    # ПОИСК КАК НА ГЛАВНОЙ (ТОЛЬКО ЗДЕСЬ!)
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

# ================= МЕССЕНДЖЕР =================
elif st.session_state.page == "Мессенджер":
    st.markdown('<div class="gold-title">💬 МЕССЕНДЖЕР</div>', unsafe_allow_html=True)
    
    if not st.session_state.is_logged_in:
        st.warning("⚠️ Для использования мессенджера войдите в систему")
        if st.button("Перейти к входу"):
            st.session_state.page = "Профиль"
            st.rerun()
        st.stop()
    
    st.markdown('<div class="messenger-container">', unsafe_allow_html=True)
    
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.markdown("### 🔍 Найти пользователя")
        search_username = st.text_input("Введите никнейм:", placeholder="@username", key="messenger_search")
        
        if st.button("🔍 Найти", use_container_width=True):
            if search_username:
                if search_username == st.session_state.user_data.get("username"):
                    st.error("Нельзя написать самому себе")
                else:
                    user = get_user_by_username(search_username)
                    if user:
                        st.session_state.chat_partner = user
                        st.session_state.current_chat_id = user["id"]
                        st.success(f"Найден: {user['first_name']} {user['last_name']}")
                        st.rerun()
                    else:
                        st.error("Пользователь не найден")
        
        st.markdown("---")
        st.markdown("### 👥 Контакты")
        
        all_users = get_all_users_except(st.session_state.user_data.get("username", ""))
        
        if not all_users:
            st.info("👤 Других пользователей пока нет")
        else:
            for user in all_users:
                is_active = (st.session_state.get('chat_partner') and 
                           st.session_state.chat_partner.get('id') == user['id'])
                
                contact_class = "contact-item active" if is_active else "contact-item"
                
                st.markdown(f"""
                <div class="{contact_class}">
                    <div style="font-weight: 600;">{user['first_name']} {user['last_name']}</div>
                    <div style="font-size: 0.9em; color: #666;">@{user['username']} <span class="offline-badge"></span></div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("💬 Написать", key=f"contact_{user['id']}", use_container_width=True):
                    st.session_state.chat_partner = user
                    st.session_state.current_chat_id = user["id"]
                    st.rerun()
    
    with col_right:
        if st.session_state.chat_partner:
            partner = st.session_state.chat_partner
            
            st.markdown(f"""
            <div class="chat-header">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #DAA520, #B8860B); 
                         display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                        {partner['first_name'][0]}
                    </div>
                    <div>
                        <div style="font-weight: 600; font-size: 18px;">
                            {partner['first_name']} {partner['last_name']}
                        </div>
                        <div style="font-size: 14px; color: #666;">
                            @{partner['username']} <span class="offline-badge"></span>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            chat_container = st.container(height=400)
            with chat_container:
                chat_history = get_chat_history(
                    st.session_state.user_data['username'],
                    partner['username']
                )
                
                if not chat_history:
                    st.markdown("""
                    <div style="text-align: center; padding: 50px; color: #666;">
                        <div style="font-size: 3rem;">💬</div>
                        <div style="font-size: 1.2rem; margin-top: 20px;">
                            Начните общение
                        </div>
                        <div style="margin-top: 10px;">
                            Напишите первое сообщение ниже
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                for msg in chat_history:
                    sender = msg[0]
                    message = msg[2]
                    time = msg[3].split(' ')[1][:5] if msg[3] else ""
                    
                    if sender == st.session_state.user_data['username']:
                        st.markdown(f"""
                        <div class="message-bubble you">
                            <div>{message}</div>
                            <div style="font-size: 11px; color: #666; text-align: right;">{time}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="message-bubble other">
                            <div>{message}</div>
                            <div style="font-size: 11px; color: #666; text-align: right;">{time}</div>
                        </div>
                        """, unsafe_allow_html=True)
            
            col_input, col_send = st.columns([5, 1])
            with col_input:
                new_message = st.text_input("Введите сообщение...", key="new_message", label_visibility="collapsed")
            with col_send:
                if st.button("➤", type="primary", use_container_width=True):
                    if new_message:
                        save_chat_message(
                            st.session_state.user_data['username'],
                            partner['username'],
                            new_message
                        )
                        st.rerun()
        
        else:
            st.markdown("""
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; 
                 height: 600px; text-align: center; color: #666;">
                <div style="font-size: 5rem;">💭</div>
                <div style="font-size: 1.5rem; margin-top: 20px;">
                    Выберите чат или найдите пользователя
                </div>
                <div style="margin-top: 10px;">
                    Введите никнейм в поле поиска слева
                </div>
            </div>
            """, unsafe_allow_html=True)

# ================= СОВМЕСТНЫЙ ПРОСМОТР =================
elif st.session_state.page == "Совместный просмотр":
    st.markdown('<div class="gold-title">🎬 СОВМЕСТНЫЙ ПРОСМОТР</div>', unsafe_allow_html=True)
    
    if not st.session_state.is_logged_in:
        st.warning("⚠️ Для создания комнат войдите в систему")
        if st.button("Перейти к входу"):
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
            
            if room_data:
                video_url = room_data.get("youtube_url", "")
                video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', video_url)
                video_id = video_id_match.group(1) if video_id_match else ""
                
                st.markdown(f"### 🎥 {room_data['name']}")
                st.markdown(f"**ID комнаты:** `{room_id}` | **Пароль:** `{room_data['password']}`")
                
                if video_id:
                    components.html(f"""
                    <iframe width="100%" height="500" src="https://www.youtube.com/embed/{video_id}?autoplay=1&controls=1"
                            frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; 
                            gyroscope; picture-in-picture" allowfullscreen>
                    </iframe>
                    """, height=550)
                
                st.markdown("### 💬 Чат комнаты")
                
                room_chat_key = f"room_chat_{room_id}"
                if room_chat_key not in st.session_state:
                    st.session_state[room_chat_key] = [{
                        "sender": "Система",
                        "message": f"Добро пожаловать в комнату '{room_data['name']}'! ID: {room_id}, Пароль: {room_data['password']}",
                        "time": datetime.datetime.now().strftime("%H:%M")
                    }]
                
                chat_container = st.container(height=200)
                with chat_container:
                    for msg in st.session_state[room_chat_key]:
                        if msg["sender"] == "Система":
                            st.markdown(f"""
                            <div style="background: #e3f2fd; padding: 10px; border-radius: 10px; margin: 5px 0; border-left: 4px solid #DAA520;">
                                <div><strong>{msg['sender']}:</strong> {msg['message']}</div>
                                <div style="font-size: 11px; color: #666; text-align: right;">{msg['time']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style="background: #f8f9fa; padding: 10px; border-radius: 10px; margin: 5px 0;">
                                <div><strong>{msg['sender']}:</strong> {msg['message']}</div>
                                <div style="font-size: 11px; color: #666; text-align: right;">{msg['time']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                
                col_msg, col_send = st.columns([5, 1])
                with col_msg:
                    room_message = st.text_input("Сообщение...", key=f"room_msg", label_visibility="collapsed")
                with col_send:
                    if st.button("Отправить", use_container_width=True):
                        if room_message:
                            username = st.session_state.user_data.get("username", "Гость")
                            st.session_state[room_chat_key].append({
                                "sender": username,
                                "message": room_message,
                                "time": datetime.datetime.now().strftime("%H:%M")
                            })
                            st.rerun()
                
                if st.button("← Выйти из комнаты", use_container_width=True):
                    st.session_state.watch_room = None
                    st.rerun()
                
                st.stop()
    
    col_create, col_join = st.columns(2)
    
    with col_create:
        st.markdown("### Создать комнату")
        room_name = st.text_input("Название комнаты:", value="Моя комната")
        youtube_url = st.text_input("YouTube ссылка:", placeholder="https://www.youtube.com/watch?v=...")
        room_password = st.text_input("Пароль:", type="password")
        
        if st.button("🎥 Создать комнату", type="primary", use_container_width=True):
            if room_name and youtube_url and room_password:
                room_id = str(uuid.uuid4())[:8]
                st.session_state.rooms.append({
                    "id": room_id,
                    "name": room_name,
                    "youtube_url": youtube_url,
                    "password": room_password,
                    "owner": st.session_state.user_data.get("username", "Гость"),
                    "created": datetime.datetime.now().strftime("%H:%M")
                })
                st.session_state.watch_room = room_id
                st.rerun()
    
    with col_join:
        st.markdown("### Присоединиться к комнате")
        join_id = st.text_input("ID комнаты:", placeholder="Введите ID")
        join_password = st.text_input("Пароль для входа:", type="password")
        
        if st.button("🔗 Присоединиться", use_container_width=True):
            if join_id and join_password:
                room_found = False
                for room in st.session_state.rooms:
                    if room["id"] == join_id and room["password"] == join_password:
                        st.session_state.watch_room = room["id"]
                        st.rerun()
                        room_found = True
                        break
                if not room_found:
                    st.error("Комната не найдена или неверный пароль")

# ================= ДИСК =================
elif st.session_state.page == "Диск":
    st.markdown('<div class="gold-title">💾 ДИСК</div>', unsafe_allow_html=True)
    
    if "disk_current_path" not in st.session_state:
        st.session_state.disk_current_path = "zornet_cloud"
    if "disk_action" not in st.session_state:
        st.session_state.disk_action = "view"
    
    os.makedirs(st.session_state.disk_current_path, exist_ok=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📤 Загрузить", use_container_width=True):
            st.session_state.disk_action = "upload"
            st.rerun()
    with col2:
        if st.button("📁 Новая папка", use_container_width=True):
            st.session_state.disk_action = "new_folder"
            st.rerun()
    with col3:
        if st.button("🔍 Поиск", use_container_width=True):
            st.session_state.disk_action = "search"
            st.rerun()
    with col4:
        if st.button("🔄 Обновить", use_container_width=True):
            st.rerun()
    
    if st.session_state.disk_action == "upload":
        st.markdown("### 📤 Загрузка файлов")
        uploaded_files = st.file_uploader("Выберите файлы", accept_multiple_files=True)
        if uploaded_files:
            for uploaded_file in uploaded_files:
                file_path = os.path.join(st.session_state.disk_current_path, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            st.session_state.disk_action = "view"
            st.rerun()
        if st.button("← Назад"):
            st.session_state.disk_action = "view"
            st.rerun()
    
    elif st.session_state.disk_action == "new_folder":
        st.markdown("### 📁 Создание новой папки")
        folder_name = st.text_input("Введите название папки:")
        if st.button("✅ Создать", type="primary") and folder_name:
            new_folder_path = os.path.join(st.session_state.disk_current_path, folder_name)
            os.makedirs(new_folder_path, exist_ok=True)
            st.session_state.disk_action = "view"
            st.rerun()
        if st.button("← Назад"):
            st.session_state.disk_action = "view"
            st.rerun()
    
    else:
        st.markdown("### 📁 Файлы и папки")
        
        try:
            items = os.listdir(st.session_state.disk_current_path)
            items.sort(key=lambda x: (not os.path.isdir(os.path.join(st.session_state.disk_current_path, x)), x.lower()))
        except:
            items = []
        
        if not items:
            st.info("📭 Папка пуста")
        else:
            cols = st.columns(3)
            for idx, item in enumerate(items):
                with cols[idx % 3]:
                    item_path = os.path.join(st.session_state.disk_current_path, item)
                    is_dir = os.path.isdir(item_path)
                    
                    if is_dir:
                        st.markdown(f"""
                        <div class="folder-card">
                            <div style="font-size: 2.5rem; text-align: center;">📁</div>
                            <div style="text-align: center; font-weight: 600; margin-top: 10px;">{item}</div>
                            <div style="text-align: center; color: #666; font-size: 0.9em;">Папка</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("Открыть", key=f"open_{item}", use_container_width=True):
                            st.session_state.disk_current_path = item_path
                            st.rerun()
                    
                    else:
                        try:
                            file_size = os.path.getsize(item_path)
                            size_str = f"{file_size/1024:.1f} KB" if file_size < 1024*1024 else f"{file_size/(1024*1024):.1f} MB"
                        except:
                            size_str = "Неизвестно"
                        
                        st.markdown(f"""
                        <div class="file-card">
                            <div style="font-size: 2.5rem; text-align: center;">📄</div>
                            <div style="text-align: center; font-weight: 600; margin-top: 10px;">{item}</div>
                            <div style="text-align: center; color: #666; font-size: 0.9em;">{size_str}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if os.path.exists(item_path):
                                with open(item_path, 'rb') as f:
                                    st.download_button("📥 Скачать", f.read(), item, use_container_width=True)
                        with col2:
                            if st.button("👁️ Просмотр", key=f"view_{item}", use_container_width=True):
                                if item.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                                    try:
                                        image = Image.open(item_path)
                                        st.image(image, caption=item)
                                    except:
                                        st.error("Не удалось открыть")

# ================= НОВОСТИ =================
elif st.session_state.page == "Новости":
    st.markdown('<div class="gold-title">📰 НОВОСТИ</div>', unsafe_allow_html=True)
    
    with st.spinner("Загружаю новости..."):
        news = get_belta_news()
        
        for item in news:
            st.markdown(f"""
            <div style="background: #f8f9fa; border-left: 4px solid #DAA520; padding: 15px; margin-bottom: 15px; border-radius: 8px;">
                <a href="{item.link}" target="_blank" style="color:#DAA520; font-size:1.2rem; font-weight:bold; text-decoration:none;">
                    {item.title}
                </a>
                <p style="color:#1a1a1a; margin-top:10px;">{item.summary[:200]}...</p>
            </div>
            """, unsafe_allow_html=True)

# ================= ПОГОДА =================
elif st.session_state.page == "Погода":
    st.markdown('<div class="gold-title">🌤️ ПОГОДА</div>', unsafe_allow_html=True)
    
    # ЗОЛОТОЙ ПОИСК ДЛЯ ПОГОДЫ
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
        
        .weather-search-container {
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
        <div class="weather-search-container">
            <input type="text" id="cityInput" placeholder="🔍 Введите город..." autocomplete="off">
            <br>
            <button onclick="searchWeather()">ПОКАЗАТЬ ПОГОДУ</button>
        </div>
        
        <script>
        function searchWeather() {
            var city = document.getElementById('cityInput').value;
            if (city) {
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: city
                }, '*');
            }
        }
        
        document.getElementById('cityInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchWeather();
            }
        });
        </script>
    </body>
    </html>
    """, height=150)
    
    # Получаем город
    city_input = st.text_input("", key="weather_city_input", label_visibility="collapsed")
    
    # Определяем какой город показывать
    city_to_show = "Минск"
    if city_input:
        city_to_show = city_input
    elif st.session_state.user_city:
        city_to_show = st.session_state.user_city
    
    # Получаем погоду
    with st.spinner(f"Получаю погоду для {city_to_show}..."):
        weather_data = get_weather_by_city(city_to_show)
        
        if not weather_data:
            weather_data = get_weather_by_city("Минск")
            city_to_show = "Минск"
        
        if weather_data:
            current = weather_data["current"]
            st.session_state.user_city = city_to_show
            
            st.markdown(f"### 🌤️ Погода в {current['city']}, {current['country']}")
            
            col_temp, col_icon = st.columns([2, 1])
            with col_temp:
                st.markdown(f"""
                <div style="text-align: center;">
                    <div style="font-size: 4rem; font-weight: 800; color: #1a1a1a;">
                        {current['temp']}°C
                    </div>
                    <div style="font-size: 1.5rem; color: #666; margin-top: 10px;">
                        {get_weather_icon(current['icon'])} {current['description']}
                    </div>
                    <div style="font-size: 1rem; color: #888; margin-top: 5px;">
                        💁 Ощущается как {current['feels_like']}°C
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_icon:
                st.markdown(f"""
                <div style="text-align: center; padding-top: 15px;">
                    <div style="font-size: 5rem;">
                        {get_weather_icon(current['icon'])}
                    </div>
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
                        <div style="color: #666; font-size: 0.9rem;">{name}</div>
                        <div style="font-size: 1.2rem; font-weight: bold;">{value}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                if i + 1 < len(details):
                    with col2:
                        name, value = details[i + 1]
                        st.markdown(f"""
                        <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 10px;">
                            <div style="color: #666; font-size: 0.9rem;">{name}</div>
                            <div style="font-size: 1.2rem; font-weight: bold;">{value}</div>
                        </div>
                        """, unsafe_allow_html=True)

# ================= ПРОФИЛЬ =================
elif st.session_state.page == "Профиль":
    if st.session_state.is_logged_in:
        st.markdown('<div class="giant-id-title">ZORNET ID</div>', unsafe_allow_html=True)
        
        user = st.session_state.user_data
        st.markdown(f"""
        <div class="profile-container">
            <h2>{user.get('first_name', '')} {user.get('last_name', '')}</h2>
            <p>@{user.get('username', '')}</p>
            <p>✉️ {user.get('email', '')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚪 Выйти из аккаунта", type="primary", use_container_width=True):
            st.session_state.is_logged_in = False
            st.session_state.user_data = {}
            st.session_state.page = "Главная"
            st.rerun()
    
    else:
        st.markdown('<div class="giant-id-title">ZORNET ID</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Вход", "Регистрация"])
        
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
                        st.success("✅ Вход выполнен!")
                        st.session_state.page = "Главная"
                        st.rerun()
                    else:
                        st.error("Неверный email или пароль")
        
        with tab2:
            st.markdown("### Регистрация")
            reg_email = st.text_input("Email", key="reg_email")
            reg_username = st.text_input("Никнейм", key="reg_username")
            reg_first_name = st.text_input("Имя", key="reg_first_name")
            reg_last_name = st.text_input("Фамилия", key="reg_last_name")
            reg_password = st.text_input("Пароль", type="password", key="reg_password")
            reg_password_confirm = st.text_input("Повторите пароль", type="password", key="reg_password_confirm")
            
            if st.button("Создать аккаунт", type="primary", use_container_width=True):
                if not all([reg_email, reg_username, reg_first_name, reg_password, reg_password_confirm]):
                    st.error("Заполните все обязательные поля")
                elif reg_password != reg_password_confirm:
                    st.error("Пароли не совпадают")
                elif len(reg_password) < 6:
                    st.error("Пароль должен быть не менее 6 символов")
                else:
                    result = register_user(reg_email, reg_username, reg_first_name, reg_last_name, reg_password)
                    if result["success"]:
                        st.success("✅ Аккаунт создан! Теперь войдите в систему.")
                        st.rerun()
                    else:
                        st.error(result["message"])
        
        st.markdown('</div>', unsafe_allow_html=True)

# ================= ИНИЦИАЛИЗАЦИЯ БД =================
init_db()

# Создаем тестового пользователя если его нет
conn = sqlite3.connect("zornet.db", check_same_thread=False)
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM users WHERE username = 'test'")
if c.fetchone()[0] == 0:
    test_password = hashlib.sha256("test123".encode()).hexdigest()
    try:
        c.execute("INSERT INTO users (email, username, first_name, last_name, password_hash) VALUES (?, ?, ?, ?, ?)",
                 ("test@zornet.by", "test", "Тест", "Пользователь", test_password))
        conn.commit()
    except:
        pass
conn.close()
