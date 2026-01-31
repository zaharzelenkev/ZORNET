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
from duckduckgo_search import DDGS
from huggingface_hub import InferenceClient
import streamlit.components.v1 as components
import uuid  # ДОБАВЛЕНО ДЛЯ ГЕНЕРАЦИИ ID
import re    # ДОБАВЛЕНО ДЛЯ РАБОТЫ С YOUTUBE ССЫЛКАМИ

# ================= НАСТРОЙКИ =================
st.set_page_config(
    page_title="ZORNET",
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

# 🔴 ИСПРАВЛЕННАЯ ЧАСТЬ - Правильная инициализация авторизации
if "auth_step" not in st.session_state:
    st.session_state.auth_step = "login_start"  # "login_start", "info_form", "logged_in"
if "user_data" not in st.session_state:
    st.session_state.user_data = {}
if "user_photo" not in st.session_state:
    st.session_state.user_photo = None
if "disk_current_path" not in st.session_state:
    st.session_state.disk_current_path = "zornet_cloud"
if "disk_action" not in st.session_state:
    st.session_state.disk_action = "view"

# 🔴 НОВОЕ: Флаг авторизации (заменяем auth_status)
if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False  # Изначально не авторизован

# ================= ОБНОВЛЕННЫЕ CSS СТИЛИ =================
st.markdown("""
<style>
    /* 1. Делаем хедер прозрачным, чтобы он не мешал, но кнопка в нем жила */
    [data-testid="stHeader"] {
        background: rgba(0,0,0,0) !important;
        color: white !important;
    }

    /* 2. Находим родную кнопку сайдбара и переносим её вправо */
    button[data-testid="stSidebarCollapse"] {
        position: fixed !important;
        right: 20px !important;
        top: 15px !important;
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

    button[data-testid="stSidebarCollapse"] svg {
        display: none !important;
    }
    
    button[data-testid="stSidebarCollapse"]::after {
        content: "☰" !important;
        color: white !important;
        font-size: 24px !important;
        font-weight: bold !important;
    }

    [data-testid="stSidebar"] button[data-testid="stSidebarCollapse"] {
        right: auto !important;
        left: 10px !important;
        top: 10px !important;
        position: relative !important;
    }

    div[data-testid="stVerticalBlock"] > div:has(div.stMarkdown) {
        padding: 0 !important;
        margin: 0 !important;
    }

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

    div.stButton > button {
        background: #f8f9fa !important;
        border: 1px solid #dee2e6 !important;
        color: #1a1a1a !important;
        padding: 20px !important; 
        border-radius: 12px !important;
        font-weight: bold !important;
        width: 100% !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
    }

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

    .search-result {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border-left: 4px solid #DAA520;
    }

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
        padding: 10px 20px !important;
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
    
    .user-avatar-main {
        width: 180px;
        height: 180px;
        border-radius: 40px;
        object-fit: cover;
        border: 4px solid #DAA520;
        margin-bottom: 20px;
    }
    
    .stFileUploader section {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= САЙДБАР =================
with st.sidebar:
    st.markdown("<h3 style='color:#DAA520;'>🇧🇾 ZORNET</h3>", unsafe_allow_html=True)
    
    pages = [
        ("🏠", "ГЛАВНАЯ", "Главная"),
        ("💬", "МЕССЕНДЖЕР", "Мессенджер"),
        ("🎬", "СОВМЕСТНЫЙ ПРОСМОТР", "Совместный просмотр"),
        ("🎵", "МУЗЫКА", "Музыка"),
        ("📰", "НОВОСТИ", "Новости"),
        ("🌤️", "ПОГОДА", "Погода"),
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

def get_weather_by_coords(lat, lon):
    API_KEY = "20ebdd8243b8a3a29abe332fefdadb44"
    
    try:
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
        else:
            st.error(f"Ошибка API: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Ошибка получения погоды: {e}")
        return None

def get_weather_by_city(city_name):
    API_KEY = "20ebdd8243b8a3a29abe332fefdadb44"
    
    try:
        geocode_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={API_KEY}"
        geocode_response = requests.get(geocode_url, timeout=10)
        
        if geocode_response.status_code == 200 and geocode_response.json():
            city_data = geocode_response.json()[0]
            lat = city_data["lat"]
            lon = city_data["lon"]
            
            return get_weather_by_coords(lat, lon)
        else:
            st.error("Город не найден")
            return None
    except Exception as e:
        st.error(f"Ошибка: {e}")
        return None

# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ДИСКА =================
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

# ================= НАСТРОЙКИ AI =================
HF_API_KEY = st.secrets.get("HF_API_KEY", "")
CHAT_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
API_URL = "https://router.huggingface.co/api/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {HF_API_KEY}",
    "Content-Type": "application/json"
} if HF_API_KEY else {}

def ask_hf_ai(prompt: str) -> str:
    if not HF_API_KEY:
        return "⚠️ API ключ не настроен. Добавьте HF_API_KEY в secrets.toml"
    
    payload = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": "Ты ZORNET AI — умный помощник. Отвечай по‑русски кратко и понятно."},
            {"role": "user", "content": prompt}
        ],
        "max_new_tokens": 300,
        "temperature": 0.7
    }
    
    try:
        r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
        
        if r.status_code == 503:
            return "⏳ ZORNET AI загружается — попробуйте через несколько секунд."
        
        if r.status_code != 200:
            return "⚠️ ZORNET AI временно недоступен."
        
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        return text.strip()
    
    except Exception:
        return "⚠️ Ошибка соединения с ZORNET AI."

# ================= ФУНКЦИИ ПОИСКА =================
def search_zornet(query, num_results=5):
    results = []
    
    try:
        with DDGS() as ddgs:
            ddgs_results = list(ddgs.text(query, max_results=num_results, region='wt-wt'))
            
            if ddgs_results:
                for r in ddgs_results[:num_results]:
                    results.append({
                        "title": r.get("title", query),
                        "url": r.get("href", f"https://www.google.com/search?q={query}"),
                        "snippet": r.get("body", f"Результаты по запросу: {query}")[:180] + "...",
                    })
                return results
    except Exception as e:
        st.error(f"Ошибка поиска: {e}")
    
    fallback_results = [
        {
            "title": f"{query} - поиск в Google",
            "url": f"https://www.google.com/search?q={query}",
            "snippet": f"Нажмите для поиска '{query}' в Google."
        },
        {
            "title": f"{query} в Википедии",
            "url": f"https://ru.wikipedia.org/wiki/{query}",
            "snippet": f"Ищите информацию о '{query}' в Википедии."
        },
    ]
    
    return fallback_results[:num_results]

# ================= БАЗА ДАННЫХ =================
def init_db():
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_user_count():
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

# ================= ДИСК ФУНКЦИИ =================
def init_disk_db():
    conn = sqlite3.connect("zornet_disk.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            size INTEGER,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_disk_files():
    conn = sqlite3.connect("zornet_disk.db")
    c = conn.cursor()
    c.execute("SELECT name, size, uploaded_at FROM files ORDER BY uploaded_at DESC LIMIT 10")
    files = c.fetchall()
    conn.close()
    return files

def save_file_to_db(filename, size):
    conn = sqlite3.connect("zornet_disk.db")
    c = conn.cursor()
    c.execute("INSERT INTO files (name, size) VALUES (?, ?)", (filename, size))
    conn.commit()
    conn.close()

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
    
    # 🔴 ИНДИКАТОР АВТОРИЗАЦИИ
    if st.session_state.is_logged_in:
        user = st.session_state.user_data
        st.success(f"✅ Авторизован как: {user.get('first_name', 'Пользователь')} (@{user.get('nickname', 'user')})")
    else:
        st.warning("⚠️ Вы не авторизованы. Для доступа ко всем функциям войдите в ZORNET ID")
        if st.button("🆔 Войти", key="login_from_main"):
            st.session_state.page = "Профиль"
            st.rerun()
    
    current_time = datetime.datetime.now(pytz.timezone('Europe/Minsk'))
    
    with col1:
        st.button(f"🕒 {current_time.strftime('%H:%M')}\nМинск", use_container_width=True)
    with col2:
        if st.button("⛅ Погода", use_container_width=True):
            st.session_state.page = "Погода"
            st.rerun()
    with col3:
        st.button("💵 3.20\nBYN/USD", use_container_width=True)
    with col4:
        if st.button("🤖 ZORNET AI", use_container_width=True):
            st.session_state.page = "ZORNET AI"
            st.rerun()
    with col5:
        if st.button("💬 Мессенджер", use_container_width=True):
            st.session_state.page = "Мессенджер"
            st.rerun()
    with col6:
        if st.button("🎬 Совм. просмотр", use_container_width=True):
            st.session_state.page = "Совместный просмотр"
            st.rerun()
    with col7:
        if st.button("🎵 Музыка", use_container_width=True):
            st.session_state.page = "Музыка"
            st.rerun()
    
    st.markdown("---")
    
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

# ================= СТРАНИЦА МЕССЕНДЖЕРА =================
elif st.session_state.page == "Мессенджер":
    st.markdown('<div class="gold-title">💬 МЕССЕНДЖЕР</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📨 Личные сообщения", "👥 Группы", "📹 Видеозвонки"])
    
    with tab1:
        st.markdown("### 💬 Личные сообщения")
        
        chats = [
            {"name": "Алексей", "last_msg": "Привет! Как дела?", "time": "12:30", "unread": 3},
            {"name": "Мария", "last_msg": "Отправила тебе файл", "time": "11:45", "unread": 0},
            {"name": "Команда ZORNET", "last_msg": "Обновление системы", "time": "10:20", "unread": 1},
            {"name": "Иван Петров", "last_msg": "Давай созвонимся", "time": "Вчера", "unread": 0},
        ]
        
        for chat in chats:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"""
                <div style="padding: 10px; border-radius: 10px; background: #f8f9fa; margin: 5px 0;">
                    <b>{chat['name']}</b><br>
                    <span style="color: #666; font-size: 0.9em;">{chat['last_msg']}</span>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.text(chat['time'])
                if chat['unread'] > 0:
                    st.markdown(f"<div style='background: red; color: white; border-radius: 50%; width: 20px; height: 20px; text-align: center;'>{chat['unread']}</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        new_message = st.text_input("Написать сообщение:", placeholder="Введите текст...")
        if st.button("Отправить", type="primary"):
            if new_message:
                st.success("Сообщение отправлено!")
    
    with tab2:
        st.markdown("### 👥 Групповые чаты")
        
        groups = [
            {"name": "Работа", "members": 12, "last": "Обсуждение проекта"},
            {"name": "Друзья", "members": 8, "last": "Встреча в субботу"},
            {"name": "Семья", "members": 5, "last": "Фото с отпуска"},
        ]
        
        for group in groups:
            with st.expander(f"📢 {group['name']} ({group['members']} участников)"):
                st.text(f"Последнее: {group['last']}")
                if st.button(f"Присоединиться к {group['name']}", key=f"join_{group['name']}"):
                    st.success(f"Вы присоединились к {group['name']}!")
        
        st.markdown("---")
        st.markdown("#### Создать новую группу")
        new_group = st.text_input("Название группы:")
        if st.button("Создать группу"):
            if new_group:
                st.success(f"Группа '{new_group}' создана!")
    
    with tab3:
        st.markdown("### 📹 Видеозвонки")
        
        room_name = st.text_input("Название комнаты:", placeholder="моя-комната-123")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎥 Создать комнату", use_container_width=True):
                if room_name:
                    jitsi_url = f"https://meet.jit.si/zornet-{room_name}"
                    st.success(f"Комната создана!")
                    st.markdown(f"[Перейти в комнату]({jitsi_url})")
        
        with col2:
            if st.button("🔗 Присоединиться", use_container_width=True):
                if room_name:
                    jitsi_url = f"https://meet.jit.si/zornet-{room_name}"
                    st.markdown(f"[Присоединиться к комнате]({jitsi_url})")
        
        st.markdown("---")
        st.markdown("#### Прямой доступ к видеокомнате")
        st.info("Совет: Для лучшего качества используйте наушники")
        
        components.html(f"""
        <iframe 
            allow="camera; microphone; fullscreen; display-capture"
            src="https://meet.jit.si/zornet-meet-demo"
            style="height: 500px; width: 100%; border: none; border-radius: 10px;"
            allowfullscreen>
        </iframe>
        """, height=550)

# ================= СТРАНИЦА СОВМЕСТНОГО ПРОСМОТРА =================
elif st.session_state.page == "Совместный просмотр":
    st.markdown('<div class="gold-title">🎬 СОВМЕСТНЫЙ ПРОСМОТР</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Создать комнату для просмотра")
        
        video_url = st.text_input(
            "Ссылка на YouTube видео:",
            placeholder="https://www.youtube.com/watch?v=...",
            help="Вставьте ссылку на YouTube видео"
        )
        
        room_name = st.text_input(
            "Название комнаты:",
            placeholder="Например: Фильм с друзьями",
            value="Моя комната"
        )
        
        room_password = st.text_input(
            "Пароль (опционально):",
            type="password",
            placeholder="Оставьте пустым для публичной комнаты"
        )
        
        if st.button("🎥 Создать комнату", type="primary", use_container_width=True):
            if video_url and room_name:
                room_id = str(uuid.uuid4())[:8]
                
                st.session_state.rooms.append({
                    "id": room_id,
                    "name": room_name,
                    "url": video_url,
                    "password": room_password,
                    "owner": st.session_state.get("user_email", "Гость"),
                    "created": datetime.datetime.now().strftime("%H:%M")
                })
                
                st.success(f"Комната '{room_name}' создана!")
                
                watch_url = f"{st.experimental_get_query_params().get('base_url', [''])[0]}/watch/{room_id}"
                st.markdown(f"**Ссылка для друзей:** `{watch_url}`")
                
                if st.button("▶️ Перейти в комнату"):
                    st.session_state.watch_room = room_id
                    st.rerun()
    
    with col2:
        st.markdown("### Активные комнаты")
        
        if st.session_state.rooms:
            for room in st.session_state.rooms[-5:]:
                st.markdown(f"""
                <div style="background: #f8f9fa; padding: 10px; border-radius: 8px; margin: 5px 0; border-left: 3px solid #DAA520;">
                    <b>{room['name']}</b><br>
                    <small>Создал: {room['owner']}</small><br>
                    <small>В {room['created']}</small>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Присоединиться", key=f"join_{room['id']}", use_container_width=True):
                    st.session_state.watch_room = room['id']
                    st.rerun()
        else:
            st.info("🎬 Пока нет активных комнат. Создайте первую!")
    
    if st.session_state.get("watch_room"):
        st.markdown("---")
        st.markdown("### 🎥 Комната для совместного просмотра")
        
        current_room = None
        for room in st.session_state.rooms:
            if room["id"] == st.session_state.watch_room:
                current_room = room
                break
        
        if current_room:
            st.markdown(f"**Комната:** {current_room['name']}")
            st.markdown(f"**Владелец:** {current_room['owner']}")
            
            video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', current_room['url'])
            
            if video_id_match:
                video_id = video_id_match.group(1)
                
                components.html(f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{ 
                            margin: 0; 
                            padding: 20px; 
                            background: #0f0f0f; 
                            font-family: Arial, sans-serif;
                        }}
                        .player-container {{
                            max-width: 1000px;
                            margin: 0 auto;
                            background: black;
                            border-radius: 15px;
                            overflow: hidden;
                            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                        }}
                    </style>
                </head>
                <body>
                    <div class="player-container">
                        <iframe 
                            width="100%" 
                            height="500" 
                            src="https://www.youtube.com/embed/{video_id}?autoplay=1&controls=1"
                            frameborder="0" 
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                            allowfullscreen>
                        </iframe>
                        
                        <div style="padding: 20px; background: #1a1a1a; color: white;">
                            <h3 style="margin: 0 0 10px 0;">💬 Чат комнаты</h3>
                            <div id="chat" style="height: 200px; overflow-y: auto; background: #2a2a2a; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                                <div>👤 Система: Добро пожаловать в комнату!</div>
                                <div>👤 {current_room['owner']}: Привет всем!</div>
                            </div>
                            <input type="text" id="message" placeholder="Введите сообщение..." style="width: 70%; padding: 8px; border-radius: 5px; border: none;">
                            <button onclick="sendMessage()" style="padding: 8px 15px; background: #DAA520; color: white; border: none; border-radius: 5px; margin-left: 10px;">Отправить</button>
                        </div>
                    </div>
                    
                    <script>
                        function sendMessage() {{
                            var msg = document.getElementById('message').value;
                            if (msg.trim() !== '') {{
                                var chat = document.getElementById('chat');
                                chat.innerHTML += '<div>👤 Вы: ' + msg + '</div>';
                                document.getElementById('message').value = '';
                                chat.scrollTop = chat.scrollHeight;
                            }}
                        }}
                        
                        document.getElementById('message').focus();
                    </script>
                </body>
                </html>
                """, height=650)
            else:
                st.error("Неверная ссылка на YouTube видео")
        
        if st.button("← Выйти из комнаты"):
            st.session_state.watch_room = None
            st.rerun()

# ================= СТРАНИЦА МУЗЫКИ =================
elif st.session_state.page == "Музыка":
    st.markdown('<div class="gold-title">🎵 МУЗЫКА</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🎧 Совместное прослушивание", "📻 Радиостанции", "🎼 Моя музыка"])
    
    with tab1:
        st.markdown("### 🎧 Создать музыкальную комнату")
        
        col1, col2 = st.columns(2)
        
        with col1:
            room_name = st.text_input("Название комнаты:", value="Моя музыкальная комната")
            
            stations = {
                "Европа Плюс": "https://ep128.hostingradio.ru:8052/ep128",
                "Русское Радио": "http://online-1.gkvr.ru:8000/rus_radio_64.aac",
                "Рекорд": "http://air2.radiorecord.ru:805/rr_320",
                "Relax FM": "http://ic6.101.ru:8000/v1_1",
                "Наше Радио": "http://nashe1.hostingradio.ru:80/nashe-128.mp3",
            }
            
            selected_station = st.selectbox("Выберите радиостанцию:", list(stations.keys()))
            
            if st.button("🎵 Создать комнату", use_container_width=True, type="primary"):
                room_id = str(uuid.uuid4())[:8]
                
                st.session_state.music_rooms.append({
                    "id": room_id,
                    "name": room_name,
                    "station": selected_station,
                    "stream_url": stations[selected_station],
                    "owner": st.session_state.get("user_email", "Гость"),
                    "listeners": 1
                })
                
                st.success(f"Музыкальная комната создана!")
                st.session_state.current_music_room = room_id
        
        with col2:
            st.markdown("#### Активные комнаты")
            
            if st.session_state.music_rooms:
                for room in st.session_state.music_rooms:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                color: white; padding: 15px; border-radius: 10px; margin: 10px 0;">
                        <b>{room['name']}</b><br>
                        <small>🎵 {room['station']}</small><br>
                        <small>👥 {room['listeners']} слушателей</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Присоединиться", key=f"music_join_{room['id']}", use_container_width=True):
                        st.session_state.current_music_room = room['id']
                        st.rerun()
            else:
                st.info("Создайте первую музыкальную комнату!")
        
        if st.session_state.get("current_music_room"):
            current_room = None
            for room in st.session_state.music_rooms:
                if room["id"] == st.session_state.current_music_room:
                    current_room = room
                    break
            
            if current_room:
                st.markdown("---")
                st.markdown(f"### 🎵 Слушаем: {current_room['station']}")
                
                components.html(f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{ 
                            margin: 0; 
                            padding: 20px; 
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                            font-family: Arial, sans-serif;
                        }}
                        .music-player {{
                            max-width: 600px;
                            margin: 0 auto;
                            background: rgba(255,255,255,0.1);
                            backdrop-filter: blur(10px);
                            border-radius: 20px;
                            padding: 30px;
                            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                            text-align: center;
                        }}
                        .album-art {{
                            width: 200px;
                            height: 200px;
                            background: linear-gradient(45deg, #DAA520, #FFD700);
                            border-radius: 20px;
                            margin: 0 auto 20px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 60px;
                        }}
                        .controls button {{
                            background: rgba(255,255,255,0.2);
                            border: none;
                            color: white;
                            padding: 15px;
                            margin: 5px;
                            border-radius: 50%;
                            font-size: 20px;
                            cursor: pointer;
                            width: 50px;
                            height: 50px;
                        }}
                    </style>
                </head>
                <body>
                    <div class="music-player">
                        <div class="album-art">🎵</div>
                        <h2>{current_room['name']}</h2>
                        <p>{current_room['station']}</p>
                        
                        <audio id="audioPlayer" controls autoplay style="width: 100%; margin: 20px 0;">
                            <source src="{current_room['stream_url']}" type="audio/mpeg">
                            Ваш браузер не поддерживает аудиоплеер.
                        </audio>
                        
                        <div class="controls">
                            <button onclick="document.getElementById('audioPlayer').play()">▶️</button>
                            <button onclick="document.getElementById('audioPlayer').pause()">⏸️</button>
                            <button onclick="document.getElementById('audioPlayer').volume += 0.1">🔊</button>
                            <button onclick="document.getElementById('audioPlayer').volume -= 0.1">🔉</button>
                        </div>
                        
                        <div style="margin-top: 20px; background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px;">
                            <h4>👥 Сейчас слушают:</h4>
                            <p>{current_room['owner']} (создатель)</p>
                            <p id="otherListeners">Вы</p>
                        </div>
                    </div>
                    
                    <script>
                        document.getElementById('audioPlayer').play();
                    </script>
                </body>
                </html>
                """, height=550)
                
                if st.button("← Выйти из комнаты"):
                    st.session_state.current_music_room = None
                    st.rerun()
    
    with tab2:
        st.markdown("### 📻 Радиостанции Беларуси")
        
        belarus_radio = [
            ("Радио Би-Эй", "Популярная музыка", "http://stream.belarusradio.by:8000/radio"),
            ("Радио Минск", "Новости и музыка", "http://radio.minsk.by:8000/minsk"),
            ("Радио Сталіца", "Белорусские хиты", "http://radiostalica.by:8000/stalica"),
            ("Радио UNISTAR", "Танцевальная музыка", "http://unistar.by:8000/unistar"),
            ("Пилот FM", "Рок и альтернатива", "http://pilotfm.by:8000/pilot"),
        ]
        
        for name, desc, url in belarus_radio:
            with st.expander(f"📻 {name}"):
                st.write(desc)
                st.audio(url, format="audio/mp3")
    
    with tab3:
        st.markdown("### 🎼 Моя музыка (из Диска)")
        
        if st.session_state.get("auth_status") == "logged_in":
            user_email = st.session_state.user_data['email']
            user_folder_name = "".join(filter(str.isalnum, user_email))
            music_path = os.path.join("zornet_storage", user_folder_name)
            
            if os.path.exists(music_path):
                audio_extensions = ['.mp3', '.wav', '.ogg', '.m4a']
                audio_files = []
                
                for root, dirs, files in os.walk(music_path):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in audio_extensions):
                            audio_files.append(os.path.join(root, file))
                
                if audio_files:
                    for audio_file in audio_files[:5]:
                        filename = os.path.basename(audio_file)
                        st.write(f"🎵 {filename}")
                        st.audio(audio_file, format="audio/mp3")
                else:
                    st.info("Загрузите аудиофайлы в ваш Диск (MP3, WAV)")
            else:
                st.info("У вас еще нет своего хранилища")
        else:
            st.warning("Войдите в систему, чтобы видеть свою музыку")

# ================= СТРАНИЦА НОВОСТЕЙ =================
elif st.session_state.page == "Новости":
    st.markdown('<div class="gold-title">📰 НОВОСТИ</div>', unsafe_allow_html=True)
    
    with st.spinner("Загружаю новости..."):
        news = get_belta_news()
        
        for item in news:
            st.markdown(f"""
            <div style="
                background: #f8f9fa;
                border-left: 4px solid #DAA520;
                padding: 15px;
                margin-bottom: 15px;
                border-radius: 8px;
            ">
                <a href="{item.link}" target="_blank" 
                   style="color:#DAA520; font-size:1.2rem; font-weight:bold; text-decoration:none;">
                    {item.title}
                </a>
                <p style="color:#1a1a1a; margin-top:10px;">{item.summary[:200]}...</p>
            </div>
            """, unsafe_allow_html=True)

# ================= СТРАНИЦА ПОГОДЫ =================
elif st.session_state.page == "Погода":
    st.markdown('<div class="gold-title">🌤️ ПОГОДА</div>', unsafe_allow_html=True)
    
    default_city = "Минск"
    
    col1, col2 = st.columns([3, 1])
    with col1:
        city_input = st.text_input(
            "🔍 Введите ваш город",
            placeholder="Например: Минск, Гомель, Брест...",
            key="weather_city_input"
        )
    
    with col2:
        search_clicked = st.button("Найти", type="primary", use_container_width=True)
    
    city_to_show = default_city
    if search_clicked and city_input:
        city_to_show = city_input
    elif 'user_city' in st.session_state:
        city_to_show = st.session_state.user_city
    
    with st.spinner(f"Получаю погоду для {city_to_show}..."):
        weather_data = get_weather_by_city(city_to_show)
        
        if not weather_data:
            st.error(f"Город '{city_to_show}' не найден. Показываю погоду в Минске.")
            weather_data = get_weather_by_city(default_city)
            city_to_show = default_city
        
        if weather_data:
            current = weather_data["current"]
            
            st.session_state.user_city = city_to_show
            st.session_state.weather_data = weather_data
            
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
                    <div style="
                        background: #f8f9fa;
                        padding: 12px;
                        border-radius: 8px;
                        margin-bottom: 10px;
                    ">
                        <div style="color: #666; font-size: 0.9rem;">{name}</div>
                        <div style="font-size: 1.2rem; font-weight: bold;">{value}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                if i + 1 < len(details):
                    with col2:
                        name, value = details[i + 1]
                        st.markdown(f"""
                        <div style="
                            background: #f8f9fa;
                            padding: 12px;
                            border-radius: 8px;
                            margin-bottom: 10px;
                        ">
                            <div style="color: #666; font-size: 0.9rem;">{name}</div>
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
                        <div style="
                            background: linear-gradient(135deg, #6ecbf5 0%, #059be5 100%);
                            border-radius: 8px;
                            padding: 12px;
                            text-align: center;
                            color: white;
                        ">
                            <div style="font-weight: bold; margin-bottom: 8px;">{day_name}</div>
                            <div style="font-size: 2rem; margin: 8px 0;">
                                {get_weather_icon(day['weather'][0]['icon'])}
                            </div>
                            <div style="font-size: 1.2rem; font-weight: bold;">
                                {round(day['main']['temp'])}°C
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🇧🇾 Города Беларуси")
    
    belarus_cities = [
        ("Минск", "Столица"),
        ("Гомель", "Второй по величине"),
        ("Витебск", "Город фестивалей"),
        ("Могилёв", "Исторический центр"),
        ("Брест", "Город-герой"),
        ("Гродно", "Западные ворота"),
        ("Бобруйск", "Промышленный центр"),
        ("Барановичи", "Крупный транспортный узел"),
        ("Борисов", "Древний город"),
        ("Орша", "Восточные ворота"),
        ("Пинск", "Столица Полесья"),
        ("Мозырь", "Нефтяная столица"),
        ("Солигорск", "Город шахтёров"),
        ("Новополоцк", "Нефтехимический центр"),
        ("Лида", "Замковый город")
    ]
    
    cols = st.columns(3)
    for idx, (city, description) in enumerate(belarus_cities):
        with cols[idx % 3]:
            if st.button(f"**{city}**", key=f"city_{city}", help=description, use_container_width=True):
                st.session_state.user_city = city
                st.rerun()

# ================= СТРАНИЦА ДИСКА =================
# ================= СТРАНИЦА ДИСКА (ИСПРАВЛЕННАЯ ПРОВЕРКА) =================
elif st.session_state.page == "Диск":
    st.markdown('<div class="gold-title">💾 ДИСК</div>', unsafe_allow_html=True)
    
    # 🔴 ИСПРАВЛЕННАЯ ПРОВЕРКА АВТОРИЗАЦИИ
    if not st.session_state.is_logged_in:
        st.warning("""
        ⚠️ **Требуется авторизация**
        
        Чтобы пользоваться облачным диском, войдите в ZORNET ID.
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🆔 Войти в ZORNET ID", type="primary", use_container_width=True):
                st.session_state.page = "Профиль"
                st.rerun()
        with col2:
            if st.button("🏠 На главную", use_container_width=True):
                st.session_state.page = "Главная"
                st.rerun()
        st.stop()
    
    # Если дошли сюда, значит пользователь авторизован
    user_email = st.session_state.user_data.get('email', 'anonymous@zornet.by')
    
    # Создаем безопасное имя папки из email
    import re
    safe_email = re.sub(r'[^a-zA-Z0-9]', '_', user_email)
    user_base_path = os.path.join("zornet_storage", safe_email)
    
    # Инициализация пути
    if "disk_current_path" not in st.session_state:
        st.session_state.disk_current_path = user_base_path
    elif not st.session_state.disk_current_path.startswith(user_base_path):
        # Если путь не принадлежит пользователю, сбрасываем к его корневой папке
        st.session_state.disk_current_path = user_base_path
    
    # Создаем папку пользователя, если не существует
    os.makedirs(st.session_state.disk_current_path, exist_ok=True)
    
    # Показываем информацию о пользователе
    st.info(f"👤 **Пользователь:** {st.session_state.user_data.get('first_name', 'Пользователь')} | 💾 **Хранилище:** {user_base_path}")
    
    st.markdown('<div class="gold-title">💾 ДИСК</div>', unsafe_allow_html=True)
    
    if st.session_state.get("auth_status") != "logged_in":
        st.warning("⚠️ Чтобы пользоваться диском войдите в ZORNET ID")
        if st.button("Перейти в профиль для входа"):
            st.session_state.page = "Профиль"
            st.rerun()
        st.stop()
    
    user_email = st.session_state.user_data['email']
    user_folder_name = "".join(filter(str.isalnum, user_email))
    user_base_path = os.path.join("zornet_storage", user_folder_name)
    
    if "disk_current_path" not in st.session_state or not st.session_state.disk_current_path.startswith(user_base_path):
        st.session_state.disk_current_path = user_base_path
    
    os.makedirs(st.session_state.disk_current_path, exist_ok=True)
    
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
        
        for root, dirs, files in os.walk(st.session_state.disk_current_path):
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
    
    st.markdown("### 🛠 Панель инструментов")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        btn_upload_class = "disk-btn-active" if st.session_state.disk_action == "upload" else "disk-btn"
        if st.button("📤 Загрузить", key="btn_upload", use_container_width=True):
            st.session_state.disk_action = "upload"
            st.rerun()
    
    with col2:
        btn_folder_class = "disk-btn-active" if st.session_state.disk_action == "new_folder" else "disk-btn"
        if st.button("📁 Новая папка", key="btn_new_folder", use_container_width=True):
            st.session_state.disk_action = "new_folder"
            st.rerun()
    
    with col3:
        btn_search_class = "disk-btn-active" if st.session_state.disk_action == "search" else "disk-btn"
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
        
        col_back1, col_back2 = st.columns(2)
        with col_back1:
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
                    icon = "📁" if item['is_dir'] else get_icon(Path(item['name']))
                    size = format_file_size(item['size']) if not item['is_dir'] else "Папка"
                    
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.markdown(f"{icon} **{item['name']}**")
                    with col2:
                        st.text(size)
                    with col3:
                        if not item['is_dir']:
                            with open(item['path'], 'rb') as f:
                                st.download_button(
                                    "📥",
                                    f.read(),
                                    item['name'],
                                    key=f"dl_search_{item['name']}"
                                )
            else:
                st.info("Ничего не найдено")
        
        if st.button("← Назад к файлам"):
            st.session_state.disk_action = "view"
            st.rerun()
    
    else:
        st.markdown("### 📁 Файлы и папки")
        
        quick_upload = st.file_uploader(
            "Загрузить файлы (можно перетащить)",
            accept_multiple_files=True,
            key="quick_upload"
        )
        
        if quick_upload:
            for file in quick_upload:
                file_path = os.path.join(st.session_state.disk_current_path, file.name)
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
            st.success(f"✅ Загружено {len(quick_upload)} файлов!")
            st.rerun()
        
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
            items.sort(
                key=lambda x: (not os.path.isdir(os.path.join(st.session_state.disk_current_path, x)), x.lower()))
            
            cols = st.columns(3)
            for idx, item in enumerate(items):
                with cols[idx % 3]:
                    item_path = os.path.join(st.session_state.disk_current_path, item)
                    is_dir = os.path.isdir(item_path)
                    icon = "📁" if is_dir else get_icon(Path(item))
                    
                    if is_dir:
                        st.markdown(f"""
                        <div class="folder-card">
                            <div style="font-size: 2.5rem; text-align: center;">{icon}</div>
                            <div style="text-align: center; font-weight: 600; margin-top: 10px;">{item}</div>
                            <div style="text-align: center; color: #666; font-size: 0.9em;">Папка</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button(f"Открыть", key=f"open_{item}", use_container_width=True):
                            st.session_state.disk_current_path = item_path
                            st.rerun()
                    
                    else:
                        file_size = os.path.getsize(item_path)
                        st.markdown(f"""
                        <div class="file-card">
                            <div style="font-size: 2.5rem; text-align: center;">{icon}</div>
                            <div style="text-align: center; font-weight: 600; margin-top: 10px;">{item}</div>
                            <div style="text-align: center; color: #666; font-size: 0.9em;">{format_file_size(file_size)}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            with open(item_path, 'rb') as f:
                                st.download_button(
                                    "📥 Скачать",
                                    f.read(),
                                    item,
                                    key=f"dl_{item}",
                                    use_container_width=True
                                )
                        with col2:
                            if st.button("👁️ Просмотр", key=f"view_{item}", use_container_width=True):
                                if item.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                                    try:
                                        image = Image.open(item_path)
                                        st.image(image, caption=item, use_column_width=True)
                                    except:
                                        st.error("Не удалось открыть изображение")
                                elif item.lower().endswith('.txt'):
                                    try:
                                        with open(item_path, 'r', encoding='utf-8') as f:
                                            content = f.read()
                                        st.text_area("Содержимое файла", content, height=200)
                                    except:
                                        st.error("Не удалось открыть файл")
                                elif item.lower().endswith('.pdf'):
                                    st.info(f"PDF файл: {item}")
                                    with open(item_path, 'rb') as f:
                                        st.download_button("Скачать PDF", f.read(), item)

# ================= СТРАНИЦА ПРОФИЛЯ (ИСПРАВЛЕННАЯ ВЕРСИЯ) =================
elif st.session_state.page == "Профиль":
    
    st.markdown("""
    <style>
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

        [data-testid="stVerticalBlock"] > div:has(div.stMarkdown) {
            padding: 0 !important;
            gap: 0 !important;
        }
        
        .profile-container {
            background: white;
            border-radius: 32px;
            padding: 40px;
            border: 1px solid #f0f0f0;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.1);
            text-align: center;
        }

        .user-avatar-main {
            width: 180px;
            height: 180px;
            border-radius: 40px;
            object-fit: cover;
            border: 4px solid #DAA520;
            margin-bottom: 20px;
        }

        .stFileUploader section {
            background-color: transparent !important;
            border: none !important;
            padding: 0 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Если уже авторизован, показываем профиль
    if st.session_state.is_logged_in and st.session_state.auth_step == "logged_in":
        user = st.session_state.user_data
        
        col_left, col_right = st.columns([1, 2])
        
        with col_left:
            st.markdown(f"""
            <div style="width:100%; aspect-ratio:1/1; background:#DAA520; border-radius:40px; display:flex; align-items:center; justify-content:center; font-size:80px; color:white; font-weight:bold;">
                {user.get('first_name', 'П')[0]}
            </div>
            """, unsafe_allow_html=True)
            
            uploaded_img = st.file_uploader("Загрузить фото", type=['jpg','png'], label_visibility="collapsed")
            if uploaded_img:
                st.session_state.user_photo = uploaded_img
                st.rerun()
        
        with col_right:
            st.markdown(f"""
            <div style="text-align:left;">
                <h1 style="margin:10px 0 0 0;">{user.get('first_name', 'Пользователь')} {user.get('last_name', '')}</h1>
                <p style="color:#666; font-size:18px;">@{user.get('nickname', 'user')}</p>
                <hr style="margin:20px 0;">
                <p><b>Email:</b> {user.get('email', 'Не указан')}</p>
                <p><b>ID пользователя:</b> ZRN-{user.get('nickname', 'USER').upper()}-2024</p>
                <p><b>Статус:</b> ✅ Авторизован</p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Перейти в Диск", use_container_width=True):
                    st.session_state.page = "Диск"
                    st.rerun()
            with col2:
                if st.button("🚪 Выйти", type="secondary", use_container_width=True):
                    # 🔴 ВАЖНО: Сбрасываем все данные авторизации
                    st.session_state.auth_step = "login_start"
                    st.session_state.is_logged_in = False
                    st.session_state.user_data = {}
                    st.session_state.user_photo = None
                    st.success("Вы вышли из системы")
                    st.rerun()
    
    else:
        # Показываем форму входа/регистрации
        st.markdown('<h1 class="giant-id-title">🆔 ZORNET ID</h1>', unsafe_allow_html=True)
        
        if st.session_state.auth_step == "login_start":
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown("""
                <div style="background:white; border:1px solid #dadce0; border-radius:8px; padding:40px; text-align:center;">
                    <img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg" width="80" style="margin-bottom:20px;">
                    <h2 style="font-weight:400; margin-bottom:10px;">Вход в ZORNET</h2>
                    <p style="color:#202124; margin-bottom:30px;">Для доступа ко всем функциям</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Простая форма входа (без реального Google API)
                email = st.text_input("Email:", placeholder="ваш@email.com")
                password = st.text_input("Пароль:", type="password", placeholder="Введите пароль")
                
                if st.button("Войти в аккаунт", use_container_width=True, type="primary"):
                    if email and password:
                        # 🔴 ИМИТАЦИЯ УСПЕШНОГО ВХОДА
                        st.session_state.user_data["email"] = email
                        st.session_state.auth_step = "info_form"
                        st.rerun()
                    else:
                        st.error("Введите email и пароль")
                
                st.markdown("---")
                st.caption("Нет аккаунта? Используйте тестовые данные:")
                if st.button("Войти как тестовый пользователь", use_container_width=True):
                    st.session_state.user_data["email"] = "test@zornet.by"
                    st.session_state.auth_step = "info_form"
                    st.rerun()
        
        elif st.session_state.auth_step == "info_form":
            with st.container():
                st.markdown('<div class="profile-container">', unsafe_allow_html=True)
                st.subheader("🆕 Завершите регистрацию")
                st.caption(f"Email: {st.session_state.user_data.get('email', 'Не указан')}")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    f_name = st.text_input("Ваше Имя", placeholder="Иван")
                    n_name = st.text_input("Придумайте Никнейм", placeholder="ivan_zornet")
                with col_b:
                    l_name = st.text_input("Ваша Фамилия", placeholder="Иванов")
                
                if st.button("✅ Завершить регистрацию", use_container_width=True, type="primary"):
                    if f_name and l_name and n_name:
                        # 🔴 СОХРАНЯЕМ ДАННЫЕ И АВТОРИЗУЕМ
                        st.session_state.user_data.update({
                            "first_name": f_name, 
                            "last_name": l_name, 
                            "nickname": n_name,
                            "email": st.session_state.user_data.get("email", f"{n_name}@zornet.by")
                        })
                        st.session_state.auth_step = "logged_in"
                        st.session_state.is_logged_in = True  # 🔴 КЛЮЧЕВОЙ ФЛАГ
                        st.success("✅ Регистрация завершена! Теперь вы можете использовать все функции ZORNET.")
                        st.rerun()
                    else:
                        st.error("Заполните все поля")
                
                if st.button("← Назад", use_container_width=True):
                    st.session_state.auth_step = "login_start"
                    st.rerun()
                    
                st.markdown('</div>', unsafe_allow_html=True)

# ================= ИНИЦИАЛИЗАЦИЯ =================
if __name__ == "__main__":
    init_db()
    init_disk_db()
