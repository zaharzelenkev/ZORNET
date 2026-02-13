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
if "watch_room" not in st.session_state:
    st.session_state.watch_room = None
if "user_data" not in st.session_state:
    st.session_state.user_data = {}
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

    /* КНОПКИ В САЙДБАРЕ */
    section[data-testid="stSidebar"] .stButton > button {
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 12px 20px !important;
        margin: 2px 0 !important;
        background: transparent !important;
        border: none !important;
        color: #1a1a1a !important;
        font-weight: 400 !important;
        border-radius: 0 25px 25px 0 !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #f8f9fa !important;
        border: 1px solid #DAA520 !important;
    }

    /* КНОПКИ НА ГЛАВНОЙ */
    div.stButton > button {
        background: #f8f9fa !important;
        border: 1px solid #dee2e6 !important;
        color: #1a1a1a !important;
        padding: 20px !important; 
        border-radius: 12px !important;
        font-weight: bold !important;
        width: 100% !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        height: 80px !important;
        line-height: 1.3 !important;
        white-space: pre-line !important;
        text-align: center !important;
    }

    div.stButton > button:hover {
        border-color: #DAA520 !important;
        box-shadow: 0 4px 12px rgba(218, 165, 32, 0.2) !important;
    }

/* ИДЕАЛЬНЫЕ БЕЛЫЕ ОВАЛЫ */
.quick-link-card {
    position: relative;
    background: white !important;
    border-radius: 50px !important; /* Идеальный овал */
    border: 2px solid #DAA520;
    padding: 30px 20px !important;
    margin: 10px 0;
    text-align: center;
    transition: all 0.3s ease;
    min-height: 180px;
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
    font-size: 3.5rem !important;
    margin-bottom: 15px !important;
    text-shadow: 0 2px 5px rgba(0,0,0,0.1);
    transition: transform 0.3s ease;
    display: block !important;
}

.quick-link-card:hover .quick-link-icon {
    transform: scale(1.1) rotate(5deg);
}

.quick-link-name {
    font-weight: 700 !important;
    font-size: 1.2rem !important;
    color: #333 !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1.4 !important;
    font-family: 'Helvetica Neue', sans-serif;
    display: block !important;
    text-align: center !important;
}

/* Круглые кнопки */
.quick-link-open, .quick-link-delete {
    border-radius: 40px !important;
    padding: 8px 16px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
    border: none !important;
}

.quick-link-open {
    background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%) !important;
    color: white !important;
}

.quick-link-open:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(218, 165, 32, 0.4) !important;
}

.quick-link-delete {
    background: #ff4444 !important;
    color: white !important;
}

.quick-link-delete:hover {
    background: #cc0000 !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(255, 68, 68, 0.4) !important;
}

    /* Круглые кнопки */
    .stButton > button {
        border-radius: 30px !important;
    }

    /* КНОПКА ДОБАВЛЕНИЯ */
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

    /* СТИЛИ ДЛЯ ПОГОДЫ */
    .weather-temp {
        font-size: 4rem;
        font-weight: 800;
        color: #1a1a1a;
    }

    .weather-desc {
        font-size: 1.5rem;
        color: #666;
    }

    .weather-detail-item {
        background: #f8f9fa;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
    }

    .forecast-day {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }

    /* Стили для диска */
    .disk-stats {
        background: white;
        padding: 15px;
        border-radius: 10px;
        margin: 15px 0;
        border: 1px solid #e0e0e0;
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
    
    .file-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #DAA520;
        transition: all 0.3s ease;
        text-align: center;
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
        text-align: center;
    }

    /* Стили для профиля */
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
    }

    /* Мессенджер стили */
    .chat-header {
        background: white;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin-bottom: 15px;
    }
    
    .message-you {
        background: #DCF8C6;
        padding: 10px 15px;
        border-radius: 18px;
        margin: 5px 0;
        margin-left: auto;
        max-width: 70%;
        border-bottom-right-radius: 4px;
    }
    
    .message-other {
        background: white;
        padding: 10px 15px;
        border-radius: 18px;
        margin: 5px 0;
        margin-right: auto;
        max-width: 70%;
        border-bottom-left-radius: 4px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Логин контейнер */
    .login-container {
        max-width: 500px;
        margin: 50px auto;
        padding: 40px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
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
    <div style="display:flex; justify-content:center; margin:20px 0;">
        <form action="https://www.google.com/search" method="get" target="_blank" style="width:100%; max-width:600px;">
            <input type="text" name="q" placeholder="🔍 Поиск в Google" 
                   style="width:100%; padding:16px 24px; border:1px solid #e0e0e0; border-radius:30px; 
                          font-size:16px; outline:none; transition:all 0.2s ease;"
                   onfocus="this.style.borderColor='#DAA520'; this.style.boxShadow='0 4px 12px rgba(218,165,32,0.15)'"
                   onblur="this.style.borderColor='#e0e0e0'; this.style.boxShadow='none'">
        </form>
    </div>
    """, height=80)
    
    st.markdown("---")

# БЫСТРЫЕ ССЫЛКИ - ИДЕАЛЬНЫЕ БЕЛЫЕ ОВАЛЫ
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
    # Показываем ссылки в сетке 4 колонки
    for i in range(0, len(quick_links), 4):
        cols = st.columns(4)
        for j, link in enumerate(quick_links[i:i+4]):
            with cols[j]:
                # ИДЕАЛЬНЫЙ БЕЛЫЙ ОВАЛ
                st.markdown(f"""
                <div class="quick-link-card">
                    <div class="quick-link-icon">{link.get('icon', '🔗')}</div>
                    <div class="quick-link-name">{link['name']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Круглые кнопки
                col_open, col_del = st.columns([2, 1])
                with col_open:
                    if st.button("🌐 Открыть", key=f"open_{i}_{j}", use_container_width=True):
                        js_code = f'window.open("{link["url"]}", "_blank");'
                        components.html(f"<script>{js_code}</script>", height=0)
                with col_del:
                    if st.button("✕", key=f"del_{i}_{j}", use_container_width=True):
                        st.session_state.quick_links.remove(link)
                        save_quick_links(st.session_state.quick_links)
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
            
            st.markdown(f"### Погода в {current['city']}, {current['country']}")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown(f"""
                <div style="text-align:center;">
                    <div class="weather-temp">{current['temp']}°C</div>
                    <div class="weather-desc">{get_weather_icon(current['icon'])} {current['description']}</div>
                    <div style="color:#888;">Ощущается как {current['feels_like']}°C</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="background:#f8f9fa; border-radius:16px; padding:20px;">
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <div>💧 Влажность<br><b>{current['humidity']}%</b></div>
                        <div>💨 Ветер<br><b>{current['wind_speed']} м/с</b></div>
                        <div>📊 Давление<br><b>{current['pressure']} гПа</b></div>
                        <div>👁️ Видимость<br><b>{current['visibility']} км</b></div>
                        <div>🌅 Восход<br><b>{current['sunrise']}</b></div>
                        <div>🌇 Закат<br><b>{current['sunset']}</b></div>
                    </div>
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
                
                cols = st.columns(5)
                for idx, (date, day) in enumerate(list(days.items())[:5]):
                    with cols[idx]:
                        day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][
                            datetime.datetime.strptime(date, "%Y-%m-%d").weekday()
                        ]
                        st.markdown(f"""
                        <div style="background:#f8f9fa; border-radius:12px; padding:15px; text-align:center;">
                            <div style="font-weight:bold;">{day_name}</div>
                            <div style="font-size:2rem;">{get_weather_icon(day['weather'][0]['icon'])}</div>
                            <div style="font-size:1.2rem;">{round(day['main']['temp'])}°C</div>
                        </div>
                        """, unsafe_allow_html=True)
            
            st.markdown("### 🇧🇾 Города Беларуси")
            cities = ["Минск", "Гомель", "Витебск", "Могилёв", "Брест", "Гродно"]
            cols = st.columns(3)
            for idx, city in enumerate(cities):
                with cols[idx % 3]:
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
            st.markdown("### Найти пользователя")
            search = st.text_input("Никнейм", placeholder="@username", label_visibility="collapsed", key="search_user")
            
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
            
            st.markdown("### Контакты")
            contacts = [
                {"username": "alex", "first_name": "Алексей"},
                {"username": "marina", "first_name": "Марина"},
            ]
            
            for contact in contacts:
                if st.button(f"👤 {contact['first_name']}\n@{contact['username']}", 
                           key=f"contact_{contact['username']}", use_container_width=True):
                    st.session_state.chat_partner = contact
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
                                  color:white; font-weight:bold;">
                            {partner.get('first_name', '?')[0]}
                        </div>
                        <div>
                            <div style="font-weight:600;">{partner.get('first_name', '')}</div>
                            <div style="color:#666;">@{partner.get('username', '')}</div>
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
                        time_display = msg['time'][11:16] if len(msg['time']) > 16 else msg['time'][:5]
                        
                        if msg.get("sender") == current_user:
                            st.markdown(f"""
                            <div class="message-you">
                                <div>{msg['text']}</div>
                                <div style="font-size:11px; color:#666; text-align:right;">{time_display}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="message-other">
                                <div>{msg['text']}</div>
                                <div style="font-size:11px; color:#666; text-align:right;">{time_display}</div>
                            </div>
                            """, unsafe_allow_html=True)
                
                col_input, col_send = st.columns([5, 1])
                with col_input:
                    new_msg = st.text_input("", placeholder="Введите сообщение...", key="new_msg")
                with col_send:
                    if st.button("📤", use_container_width=True) and new_msg:
                        save_chat_message(current_user, partner_user, new_msg)
                        st.session_state.messages[chat_key].append({
                            "sender": current_user, "text": new_msg,
                            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.rerun()
            else:
                st.info("👈 Выберите пользователя")

# ================= КИНОТЕАТР =================
elif st.session_state.page == "Кинотеатр":
    st.markdown('<div class="gold-title">🎬 КИНОТЕАТР</div>', unsafe_allow_html=True)
    
    if not st.session_state.is_logged_in:
        st.warning("⚠️ Войдите в систему")
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
            ]
            
            for pattern in patterns:
                match = re.search(pattern, video_url)
                if match:
                    video_id = match.group(1)
                    break
            
            st.markdown(f"### 🎥 {room_data['name']}")
            
            if video_id:
                components.html(f"""
                <iframe width="100%" height="400" 
                        src="https://www.youtube.com/embed/{video_id}?autoplay=1"
                        frameborder="0" allowfullscreen>
                </iframe>
                """, height=420)
            
            st.markdown("### 💬 Чат")
            
            room_chat = f"room_{room_id}"
            if room_chat not in st.session_state.room_messages:
                st.session_state.room_messages[room_chat] = []
            
            chat_container = st.container(height=200)
            with chat_container:
                for msg in st.session_state.room_messages[room_chat]:
                    st.markdown(f"**{msg['username']}:** {msg['message']}")
            
            col_msg, col_send = st.columns([5, 1])
            with col_msg:
                room_msg = st.text_input("", placeholder="Сообщение...", key="room_msg")
            with col_send:
                if st.button("📤", use_container_width=True) and room_msg:
                    username = st.session_state.user_data.get("username", "Гость")
                    save_room_message(room_chat, username, room_msg)
                    st.rerun()
            
            if st.button("← Выйти", use_container_width=True):
                st.session_state.watch_room = None
                st.rerun()
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Создать комнату")
            name = st.text_input("Название", value="Моя комната", key="room_name")
            url = st.text_input("YouTube ссылка", key="room_url")
            password = st.text_input("Пароль", type="password", key="room_pass")
            
            if st.button("🎥 Создать", use_container_width=True) and name and url and password:
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
            st.markdown("### Присоединиться")
            join_id = st.text_input("ID комнаты", key="join_id")
            join_pass = st.text_input("Пароль", type="password", key="join_pass")
            
            if st.button("🔗 Присоединиться", use_container_width=True) and join_id and join_pass:
                room = get_watch_room(join_id, join_pass)
                if room:
                    st.session_state.watch_room = room["id"]
                    st.rerun()
                else:
                    st.error("❌ Комната не найдена")

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
    used_percent = min(100, (stats['total_size'] / 1073741824) * 100)
    
    st.markdown(f"""
    <div class="disk-stats">
        <div style="display:flex; justify-content:space-between;">
            <span>Использовано: {format_file_size(stats['total_size'])}</span>
            <span>Лимит: 1 GB</span>
        </div>
        <div class="storage-bar">
            <div class="storage-fill" style="width:{used_percent}%;"></div>
        </div>
        <div>📁 {stats['folder_count']} папок · 📄 {stats['file_count']} файлов</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.disk_action == "upload":
        files = st.file_uploader("Выберите файлы", accept_multiple_files=True)
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
    
    elif st.session_state.disk_action == "new_folder":
        folder = st.text_input("Название папки")
        if st.button("✅ Создать", use_container_width=True) and folder:
            path = os.path.join(st.session_state.disk_current_path, folder)
            os.makedirs(path, exist_ok=True)
            st.session_state.disk_action = "view"
            st.rerun()
        
        if st.button("← Назад", use_container_width=True):
            st.session_state.disk_action = "view"
    
    elif st.session_state.disk_action == "search":
        query = st.text_input("Поиск")
        if query:
            found = []
            for root, dirs, files in os.walk(st.session_state.disk_current_path):
                for name in dirs + files:
                    if query.lower() in name.lower():
                        found.append(name)
            for item in found[:10]:
                st.markdown(f"📄 {item}")
        
        if st.button("← Назад", use_container_width=True):
            st.session_state.disk_action = "view"
    
    else:
        items = os.listdir(st.session_state.disk_current_path) if os.path.exists(st.session_state.disk_current_path) else []
        
        if not items:
            st.info("📭 Папка пуста")
        else:
            cols = st.columns(3)
            for idx, item in enumerate(items):
                with cols[idx % 3]:
                    path = os.path.join(st.session_state.disk_current_path, item)
                    is_dir = os.path.isdir(path)
                    
                    if is_dir:
                        st.markdown(f"""
                        <div class="folder-card">
                            <div style="font-size:2.5rem;">📁</div>
                            <div>{item}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button("📂 Открыть", key=f"open_{item}", use_container_width=True):
                            st.session_state.disk_current_path = path
                            st.rerun()
                    else:
                        size = os.path.getsize(path)
                        st.markdown(f"""
                        <div class="file-card">
                            <div style="font-size:2.5rem;">📄</div>
                            <div>{item}</div>
                            <div style="color:#666;">{format_file_size(size)}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        with open(path, 'rb') as f:
                            st.download_button("📥 Скачать", f.read(), item, use_container_width=True)

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
        
        if st.button("🚪 Выйти", type="primary", use_container_width=True):
            save_quick_links(st.session_state.quick_links)
            st.session_state.is_logged_in = False
            st.session_state.user_data = {}
            st.session_state.page = "Главная"
            
            storage = load_storage()
            if "current_auth" in storage:
                storage["current_auth"]["is_logged_in"] = False
                save_storage(storage)
            
            st.rerun()
    
    else:
        st.markdown('<div class="giant-id-title">ZORNET ID</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Вход", "Регистрация"])
        
        with tab1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Пароль", type="password", key="login_password")
            
            if st.button("Войти", use_container_width=True) and email and password:
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
                st.markdown(f"✅ {st.session_state.registration_message}")
                if st.button("➡️ Войти", use_container_width=True):
                    st.session_state.registration_success = False
                    st.rerun()
            else:
                reg_email = st.text_input("Email", key="reg_email")
                reg_username = st.text_input("Никнейм", key="reg_username")
                reg_first = st.text_input("Имя", key="reg_first")
                reg_pass = st.text_input("Пароль", type="password", key="reg_pass")
                reg_pass2 = st.text_input("Повторите пароль", type="password", key="reg_pass2")
                
                if st.button("Создать аккаунт", use_container_width=True):
                    if not all([reg_email, reg_username, reg_first, reg_pass, reg_pass2]):
                        st.error("❌ Заполните все поля")
                    elif reg_pass != reg_pass2:
                        st.error("❌ Пароли не совпадают")
                    elif len(reg_pass) < 6:
                        st.error("❌ Пароль слишком короткий")
                    else:
                        result = register_user(reg_email, reg_username, reg_first, "", reg_pass)
                        if result["success"]:
                            st.session_state.registration_success = True
                            st.session_state.registration_message = result["message"]
                            st.session_state.new_user_email = result["email"]
                            st.session_state.new_user_username = result["username"]
                            st.rerun()
                        else:
                            st.error(f"❌ {result['message']}")
        
        st.markdown('</div>', unsafe_allow_html=True)

# ================= ИНИЦИАЛИЗАЦИЯ =================
if __name__ == "__main__":
    init_db()
