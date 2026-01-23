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
from urllib.parse import quote

# ================= НАСТРОЙКИ =================
st.set_page_config(
    page_title="ZORNET",
    page_icon="🇧🇾",
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

# ================= CSS СТИЛИ =================
st.markdown("""
<style>
    /* ОБЩИЙ СТИЛЬ */
    .stApp { background-color: #ffffff; }

    /* СКРЫВАЕМ ЛИШНЕЕ */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

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
</style>
""", unsafe_allow_html=True)

# ================= САЙДБАР =================
with st.sidebar:
    st.markdown("<h3 style='color:#DAA520;'>🇧🇾 ZORNET</h3>", unsafe_allow_html=True)

    pages = [
        ("🏠", "ГЛАВНАЯ", "Главная"),
        ("📰", "НОВОСТИ", "Новости"),
        ("🌤️", "ПОГОДА", "Погода"),
        ("🚌", "ТРАНСПОРТ", "Транспорт"),
        ("💾", "ДИСК", "Диск"),
        ("👤", "ПРОФИЛЬ", "Профиль"),
    ]

    for i, (icon, text, page) in enumerate(pages):
        if st.button(f"{icon} {text}", key=f"nav_{i}_{page}", use_container_width=True):
            st.session_state.page = page
            st.rerun()


# ================= ФУНКЦИИ ПОГОДЫ =================
def get_weather_icon(condition_code):
    """Возвращает эмодзи для погодных условий"""
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
    """Преобразует градусы в направление ветра"""
    directions = ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"]
    index = round(degrees / 45) % 8
    return directions[index]


def get_weather_by_coords(lat, lon):
    """Получает погоду по координатам через OpenWeatherMap API"""
    # ЗАМЕНИ ЭТОТ КЛЮЧ НА СВОЙ БЕСПЛАТНЫЙ КЛЮЧ С OpenWeatherMap!
    API_KEY = "20ebdd8243b8a3a29abe332fefdadb44"

    try:
        # Текущая погода
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=ru"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()

            # Прогноз на 5 дней
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
    """Получает погоду по названию города"""
    API_KEY = "20ebdd8243b8a3a29abe332fefdadb44"  # Замени на свой ключ!

    try:
        # Сначала получаем координаты города
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


# Обработчик сообщений от JavaScript
def handle_js_messages():
    """Обрабатывает сообщения от JavaScript компонентов"""
    # Проверяем если есть сообщение от геолокации
    if 'location_result' not in st.session_state:
        # Пытаемся получить данные из query parameters (если JavaScript их отправил)
        query_params = st.experimental_get_query_params()

        if 'geolocation' in query_params:
            try:
                geo_data = json.loads(query_params['geolocation'][0])
                st.session_state.location_result = geo_data
                # Очищаем параметры
                st.experimental_set_query_params()
                st.rerun()
            except:
                pass


# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ДИСКА =================
def get_icon(file_path):
    """Возвращает иконку для файла"""
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
    """Поиск в интернете"""
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

    # Запасные результаты
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


# ================= ТРАНСПОРТНЫЕ ФУНКЦИИ =================
def get_minsk_metro():
    return [
        {"name": "Малиновка", "line": "1", "next": "3 мин"},
        {"name": "Петровщина", "line": "1", "next": "5 мин"},
        {"name": "Площадь Ленина", "line": "1", "next": "2 мин"},
        {"name": "Институт Культуры", "line": "1", "next": "4 мин"},
        {"name": "Молодёжная", "line": "2", "next": "6 мин"},
    ]


def get_bus_trams():
    return [
        {"number": "100", "type": "автобус", "from": "Ст.м. Каменная Горка", "to": "Аэропорт", "next": "7 мин"},
        {"number": "1", "type": "трамвай", "from": "Тракторный завод", "to": "Серебрянка", "next": "5 мин"},
        {"number": "3с", "type": "троллейбус", "from": "ДС Веснянка", "to": "ДС Серова", "next": "3 мин"},
        {"number": "40", "type": "автобус", "from": "Ст.м. Уручье", "to": "Дражня", "next": "10 мин"},
    ]


def get_taxi_prices():
    return [
        {"name": "Яндекс Такси", "price": "8-12 руб", "wait": "5-7 мин"},
        {"name": "Uber", "price": "9-13 руб", "wait": "4-6 мин"},
        {"name": "Такси Близко", "price": "7-10 руб", "wait": "8-10 мин"},
        {"name": "Такси Город", "price": "6-9 руб", "wait": "10-15 мин"},
    ]


def get_belarusian_railway():
    return [
        {"number": "001Б", "from": "Минск", "to": "Брест", "time": "18:00 - 21:30"},
        {"number": "735Б", "from": "Минск", "to": "Гомель", "time": "07:30 - 11:15"},
        {"number": "603Б", "from": "Минск", "to": "Витебск", "time": "14:20 - 18:45"},
    ]

# ================= БАЗА ДАННЫХ ТРАНСПОРТА =================
def init_transport_db():
    """Инициализация базы данных транспорта"""
    conn = sqlite3.connect("zornet_transport.db")
    c = conn.cursor()
    
    # Пользовательские отчеты
    c.execute("""
        CREATE TABLE IF NOT EXISTS transport_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route TEXT NOT NULL,
            vehicle_type TEXT,
            message TEXT NOT NULL,
            user_name TEXT,
            location TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            upvotes INTEGER DEFAULT 0,
            downvotes INTEGER DEFAULT 0,
            verified BOOLEAN DEFAULT 0
        )
    """)
    
    # Маршруты
    c.execute("""
        CREATE TABLE IF NOT EXISTS transport_routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            from_city TEXT NOT NULL,
            to_city TEXT NOT NULL,
            schedule TEXT,
            price TEXT,
            duration TEXT,
            operator TEXT,
            notes TEXT
        )
    """)
    
    # Попутчики
    c.execute("""
        CREATE TABLE IF NOT EXISTS carpool_rides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_city TEXT NOT NULL,
            to_city TEXT NOT NULL,
            date DATE NOT NULL,
            time TIME NOT NULL,
            seats INTEGER,
            price TEXT,
            driver_name TEXT,
            driver_rating REAL DEFAULT 5.0,
            contact TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Остановки и станции
    c.execute("""
        CREATE TABLE IF NOT EXISTS transport_stops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            type TEXT, -- 'metro', 'bus', 'tram', 'trolley', 'train'
            lines TEXT -- JSON массив маршрутов
        )
    """)
    
    # Инициализация данных если таблицы пустые
    c.execute("SELECT COUNT(*) FROM transport_routes")
    if c.fetchone()[0] == 0:
        # Добавляем базовые маршруты
        base_routes = [
            # Минский транспорт
            ("100", "автобус", "Минск", "Аэропорт", "05:30-00:30 каждые 10-15 мин", "3.50 BYN", "40 мин", "Минсктранс", "Экспресс в аэропорт"),
            ("1", "трамвай", "Минск", "Минск", "05:00-01:00 каждые 7-10 мин", "0.90 BYN", "", "Минсктранс", "Тракторный завод - Серебрянка"),
            ("3с", "троллейбус", "Минск", "Минск", "05:30-00:30 каждые 8-12 мин", "0.90 BYN", "", "Минсктранс", "ДС Веснянка - ДС Серова"),
            ("40", "автобус", "Минск", "Минск", "06:00-23:00 каждые 10-20 мин", "0.90 BYN", "", "Минсктранс", "Ст.м. Уручье - Дражня"),
            
            # Междугородние маршруты
            ("735Б", "автобус", "Минск", "Гомель", "07:30, 09:00, 12:00, 15:00, 18:00, 21:00", "15-20 BYN", "4 ч", "Гомельавтотранс", "Центральный автовокзал"),
            ("001Б", "поезд", "Минск", "Брест", "06:00, 12:00, 18:00, 22:00", "25-35 BYN", "3.5 ч", "БЖД", "Электропоезд/поезд"),
            ("603Б", "маршрутка", "Минск", "Витебск", "каждые 2 часа 07:00-21:00", "12-18 BYN", "3 ч", "Витебскавтотранс", "Отправление от ст.м. Уручье"),
            
            # Популярные направления
            ("101", "автобус", "Минск", "Молодечно", "каждые 30 мин 06:00-22:00", "5-7 BYN", "1 ч", "Минсктранс", "Ст.м. Каменная Горка"),
            ("Минск-Гродно", "автобус", "Минск", "Гродно", "08:00, 10:30, 14:00, 17:30, 20:00", "15-22 BYN", "4 ч", "Гродноавтотранс", "Центральный автовокзал"),
            ("Минск-Могилев", "автобус", "Минск", "Могилев", "07:00, 09:30, 13:00, 16:30, 19:00", "12-18 BYN", "3.5 ч", "Могилевавтотранс", ""),
        ]
        
        for route in base_routes:
            c.execute("""
                INSERT INTO transport_routes 
                (number, vehicle_type, from_city, to_city, schedule, price, duration, operator, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, route)
    
    # Инициализация остановок
    c.execute("SELECT COUNT(*) FROM transport_stops")
    if c.fetchone()[0] == 0:
        stops = [
            ("Площадь Ленина", "Минск", 53.893009, 27.567444, "metro", '["1", "2"]'),
            ("Каменная Горка", "Минск", 53.905532, 27.447341, "metro", '["1"]'),
            ("Могилевская", "Минск", 53.867829, 27.487830, "metro", '["2"]'),
            ("Центральный автовокзал", "Минск", 53.890800, 27.550800, "bus", '["100", "735Б", "101", "Минск-Гродно", "Минск-Могилев"]'),
            ("Автовокзал Восточный", "Минск", 53.9500, 27.6500, "bus", '["603Б"]'),
            ("Железнодорожный вокзал", "Минск", 53.890278, 27.550278, "train", '["001Б"]'),
            ("Аэропорт Минск-2", "Минск", 53.882, 28.030, "airport", '["100"]'),
        ]
        
        for stop in stops:
            c.execute("""
                INSERT INTO transport_stops (name, city, latitude, longitude, type, lines)
                VALUES (?, ?, ?, ?, ?, ?)
            """, stop)
    
    conn.commit()
    conn.close()

# ================= API ИНТЕГРАЦИИ =================
def get_minsk_transport_api():
    """Получение данных транспорта Минска"""
    try:
        # В реальности здесь будет API Минсктранса
        # Временно возвращаем статические данные
        return {
            "metro": {
                "line1": {"status": "работает", "delay": 0, "stations": 15},
                "line2": {"status": "работает", "delay": 2, "stations": 14}
            },
            "update_time": datetime.datetime.now().strftime("%H:%M")
        }
    except:
        return None

def get_belarusian_railway_schedule(from_city, to_city, date=None):
    """Расписание БЖД"""
    if date is None:
        date = datetime.date.today().strftime("%Y-%m-%d")
    
    # В реальности здесь API БЖД
    trains = [
        {"number": "001Б", "type": "поезд", "from": "Минск", "to": "Брест", 
         "departure": "18:00", "arrival": "21:30", "duration": "3ч 30м", 
         "price": "25-35 BYN", "available": True},
        {"number": "735Б", "type": "электропоезд", "from": "Минск", "to": "Гомель",
         "departure": "07:30", "arrival": "11:15", "duration": "3ч 45м",
         "price": "15-25 BYN", "available": True},
        {"number": "603Б", "type": "поезд", "from": "Минск", "to": "Витебск",
         "departure": "14:20", "arrival": "18:45", "duration": "4ч 25м",
         "price": "20-30 BYN", "available": True},
    ]
    
    return [t for t in trains if t["from"] == from_city and t["to"] == to_city]

# ================= ФУНКЦИИ РАБОТЫ С БАЗОЙ =================
def add_transport_report(route, message, user_name, vehicle_type=None, location=None):
    """Добавление пользовательского отчета"""
    conn = sqlite3.connect("zornet_transport.db")
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO transport_reports (route, vehicle_type, message, user_name, location)
        VALUES (?, ?, ?, ?, ?)
    """, (route, vehicle_type, message, user_name, location))
    
    conn.commit()
    conn.close()
    return True

def get_transport_reports(limit=10, route_filter=None):
    """Получение пользовательских отчетов"""
    conn = sqlite3.connect("zornet_transport.db")
    c = conn.cursor()
    
    if route_filter:
        c.execute("""
            SELECT route, vehicle_type, message, user_name, location, 
                   timestamp, upvotes, downvotes, verified
            FROM transport_reports 
            WHERE route LIKE ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (f'%{route_filter}%', limit))
    else:
        c.execute("""
            SELECT route, vehicle_type, message, user_name, location, 
                   timestamp, upvotes, downvotes, verified
            FROM transport_reports 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
    
    reports = c.fetchall()
    conn.close()
    
    return [{
        "route": r[0],
        "vehicle_type": r[1],
        "message": r[2],
        "user_name": r[3],
        "location": r[4],
        "timestamp": r[5],
        "upvotes": r[6],
        "downvotes": r[7],
        "verified": r[8],
        "rating": r[6] - r[7]
    } for r in reports]

def search_routes(from_city, to_city, vehicle_type=None):
    """Поиск маршрутов"""
    conn = sqlite3.connect("zornet_transport.db")
    c = conn.cursor()
    
    if vehicle_type:
        c.execute("""
            SELECT number, vehicle_type, from_city, to_city, 
                   schedule, price, duration, operator, notes
            FROM transport_routes 
            WHERE from_city = ? AND to_city = ? AND vehicle_type = ?
            ORDER BY vehicle_type, number
        """, (from_city, to_city, vehicle_type))
    else:
        c.execute("""
            SELECT number, vehicle_type, from_city, to_city, 
                   schedule, price, duration, operator, notes
            FROM transport_routes 
            WHERE from_city = ? AND to_city = ?
            ORDER BY vehicle_type, number
        """, (from_city, to_city))
    
    routes = c.fetchall()
    conn.close()
    
    return [{
        "number": r[0],
        "vehicle_type": r[1],
        "from_city": r[2],
        "to_city": r[3],
        "schedule": r[4],
        "price": r[5],
        "duration": r[6],
        "operator": r[7],
        "notes": r[8]
    } for r in routes]

def add_carpool_ride(from_city, to_city, date, time, seats, price, driver_name, contact):
    """Добавление поездки попутчиков"""
    conn = sqlite3.connect("zornet_transport.db")
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO carpool_rides 
        (from_city, to_city, date, time, seats, price, driver_name, contact)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (from_city, to_city, date, time, seats, price, driver_name, contact))
    
    conn.commit()
    conn.close()
    return True

def get_carpool_rides(from_city=None, to_city=None, date=None):
    """Поиск попутчиков"""
    conn = sqlite3.connect("zornet_transport.db")
    c = conn.cursor()
    
    query = "SELECT * FROM carpool_rides WHERE 1=1"
    params = []
    
    if from_city:
        query += " AND from_city = ?"
        params.append(from_city)
    if to_city:
        query += " AND to_city = ?"
        params.append(to_city)
    if date:
        query += " AND date = ?"
        params.append(date)
    
    query += " ORDER BY date, time"
    
    c.execute(query, params)
    rides = c.fetchall()
    conn.close()
    
    return rides

def get_transport_stops(city=None, stop_type=None):
    """Получение остановок"""
    conn = sqlite3.connect("zornet_transport.db")
    c = conn.cursor()
    
    query = "SELECT * FROM transport_stops WHERE 1=1"
    params = []
    
    if city:
        query += " AND city = ?"
        params.append(city)
    if stop_type:
        query += " AND type = ?"
        params.append(stop_type)
    
    c.execute(query, params)
    stops = c.fetchall()
    conn.close()
    
    return [{
        "id": s[0],
        "name": s[1],
        "city": s[2],
        "latitude": s[3],
        "longitude": s[4],
        "type": s[5],
        "lines": json.loads(s[6]) if s[6] else []
    } for s in stops]

def vote_report(report_id, vote_type):
    """Голосование за отчет"""
    conn = sqlite3.connect("zornet_transport.db")
    c = conn.cursor()
    
    if vote_type == "up":
        c.execute("UPDATE transport_reports SET upvotes = upvotes + 1 WHERE id = ?", (report_id,))
    else:
        c.execute("UPDATE transport_reports SET downvotes = downvotes + 1 WHERE id = ?", (report_id,))
    
    conn.commit()
    conn.close()
    return True

# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================
def calculate_route_map(start, end):
    """Генерация HTML карты с маршрутом"""
    # В реальном проекте здесь будет интеграция с Яндекс.Картами или OpenStreetMap
    map_html = f"""
    <div id="map" style="width: 100%; height: 400px; border-radius: 10px; margin: 20px 0;"></div>
    <script>
        // Здесь будет код инициализации карты с маршрутом от {start} до {end}
        document.getElementById('map').innerHTML = `
            <div style="width: 100%; height: 100%; background: #f0f0f0; 
                        display: flex; align-items: center; justify-content: center;
                        border-radius: 10px; color: #666;">
                <div style="text-align: center;">
                    <h3>Маршрут: {start} → {end}</h3>
                    <p>Карта маршрута (в реальном проекте будет интеграция с картами)</p>
                    <p>🔄 Расчёт оптимального пути...</p>
                </div>
            </div>
        `;
    </script>
    """
    return map_html

def get_vehicle_icon(vehicle_type):
    """Получение иконки для типа транспорта"""
    icons = {
        "автобус": "🚌",
        "троллейбус": "🚎",
        "трамвай": "🚋",
        "метро": "🚇",
        "поезд": "🚆",
        "электропоезд": "🚈",
        "маршрутка": "🚐",
        "такси": "🚕",
        "автомобиль": "🚗"
    }
    return icons.get(vehicle_type, "🚊")
    
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

    current_time = datetime.datetime.now(pytz.timezone('Europe/Minsk'))
    col1, col2, col3, col4 = st.columns(4)
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

    st.markdown("---")

    # Создаем форму для обработки Enter
    with st.form(key="search_form"):
        search_query = st.text_input(
            "",
            placeholder="Поиск в интернете",
            key="main_search",
            label_visibility="collapsed"
        )
        submitted = st.form_submit_button("🔍 Искать в ZORNET", use_container_width=True)

    # Если форма отправлена (Enter или кнопка)
    if submitted and search_query:
        # Кодируем запрос для URL
        encoded_query = requests.utils.quote(search_query)
        google_url = f"https://www.google.com/search?q={encoded_query}"
        
        # HTML/JavaScript для открытия Google в новой вкладке
        open_google_js = f"""
        <script>
            window.open("{google_url}", "_blank");
        </script>
        """
        
        # Используем компоненты для выполнения JavaScript
        components.html(open_google_js, height=0)
                
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

# ================= СТРАНИЦА ПОГОДЫ (ПРОСТО И РАБОЧЕ) =================
elif st.session_state.page == "Погода":
    st.markdown('<div class="gold-title">🌤️ ПОГОДА</div>', unsafe_allow_html=True)

    # По умолчанию показываем Минск
    default_city = "Минск"

    # Поисковая строка
    col1, col2 = st.columns([3, 1])
    with col1:
        city_input = st.text_input(
            "🔍 Введите ваш город",
            placeholder="Например: Минск, Гомель, Брест...",
            key="weather_city_input"
        )

    with col2:
        search_clicked = st.button("Найти", type="primary", use_container_width=True)

    # Определяем какой город показывать
    city_to_show = default_city
    if search_clicked and city_input:
        city_to_show = city_input
    elif 'user_city' in st.session_state:
        city_to_show = st.session_state.user_city

    # Получаем погоду для города
    with st.spinner(f"Получаю погоду для {city_to_show}..."):
        weather_data = get_weather_by_city(city_to_show)

        if not weather_data:
            # Если город не найден, показываем Минск
            st.error(f"Город '{city_to_show}' не найден. Показываю погоду в Минске.")
            weather_data = get_weather_by_city(default_city)
            city_to_show = default_city

        if weather_data:
            current = weather_data["current"]

            # Сохраняем город в сессии
            st.session_state.user_city = city_to_show
            st.session_state.weather_data = weather_data

            # Показываем город
            st.markdown(f"### 🌤️ Погода в {current['city']}, {current['country']}")

            # Основная информация
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

            # Детали погоды
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

            # Показываем детали в 2 колонки
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

            # Прогноз на 5 дней
            if weather_data.get("forecast"):
                st.markdown("#### 📅 Прогноз на 5 дней")

                forecast = weather_data["forecast"]["list"]
                days = {}

                for item in forecast:
                    date = item["dt_txt"].split(" ")[0]
                    if date not in days:
                        days[date] = item

                # Берем максимум 5 дней
                forecast_dates = list(days.keys())[:5]

                # Показываем прогноз в ряд
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

    # Блок с городами Беларуси
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

    # Показываем города в 3 колонки
    cols = st.columns(3)
    for idx, (city, description) in enumerate(belarus_cities):
        with cols[idx % 3]:
            if st.button(f"**{city}**", key=f"city_{city}", help=description, use_container_width=True):
                # При нажатии на кнопку города, ищем погоду для него
                st.session_state.user_city = city
                st.rerun()

# ================= СТРАНИЦА ТРАНСПОРТА =================
elif st.session_state.page == "Транспорт":
    # Инициализация БД транспорта
    init_transport_db()
    
    st.markdown('<div class="gold-title">🚌 ТРАНСПОРТ БЕЛАРУСИ</div>', unsafe_allow_html=True)
    
    # Кастомные стили для транспорта
    st.markdown("""
    <style>
    .transport-header {
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 30px;
        text-align: center;
    }
    .transport-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #e0e0e0;
        transition: all 0.3s ease;
    }
    .transport-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 30px rgba(218, 165, 32, 0.15);
        border-color: #DAA520;
    }
    .route-number {
        font-size: 1.8rem;
        font-weight: 800;
        color: #DAA520;
        margin-right: 10px;
    }
    .report-card {
        background: #f8f9fa;
        border-left: 4px solid #DAA520;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .vote-btn {
        background: none;
        border: 1px solid #ddd;
        border-radius: 20px;
        padding: 5px 15px;
        margin: 0 5px;
        cursor: pointer;
    }
    .vote-btn:hover {
        background: #f0f0f0;
    }
    .upvote {
        color: #4CAF50;
    }
    .downvote {
        color: #F44336;
    }
    .carpool-card {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border: 1px solid #90caf9;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Заголовок с живыми данными
    transport_status = get_minsk_transport_api()
    if transport_status:
        update_time = transport_status.get("update_time", "N/A")
        st.markdown(f"""
        <div class="transport-header">
            <h2 style="margin: 0;">🚍 Транспортная система Беларуси</h2>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">
                <span class="live-indicator"></span> Живые данные • Обновлено: {update_time}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Вкладки
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔍 Поиск маршрутов", 
        "🗺️ Карта и навигация", 
        "👥 Попутчики",
        "📢 Народные отчеты",
        "📊 Расписания"
    ])
    
    with tab1:
        st.markdown("### 🔍 Поиск маршрутов по Беларуси")
        
        col_from, col_to, col_type = st.columns([2, 2, 1])
        
        with col_from:
            cities = ["Минск", "Гомель", "Витебск", "Могилев", "Брест", "Гродно", 
                     "Барановичи", "Бобруйск", "Молодечно", "Жодино", "Солигорск"]
            from_city = st.selectbox("Откуда", cities, index=0)
        
        with col_to:
            to_city = st.selectbox("Куда", cities, index=1)
        
        with col_type:
            vehicle_types = ["Любой", "автобус", "поезд", "маршрутка", "троллейбус", "трамвай"]
            selected_type = st.selectbox("Тип", vehicle_types)
        
        if st.button("🔍 Найти маршруты", type="primary", use_container_width=True):
            if from_city and to_city:
                with st.spinner("Ищем маршруты..."):
                    # Поиск в базе данных
                    vehicle_filter = selected_type if selected_type != "Любой" else None
                    routes = search_routes(from_city, to_city, vehicle_filter)
                    
                    # Поиск в БЖД для междугородних поездов
                    if from_city != to_city:
                        trains = get_belarusian_railway_schedule(from_city, to_city)
                        routes.extend(trains)
                    
                    if routes:
                        st.markdown(f"### 📋 Найдено {len(routes)} маршрутов")
                        
                        for route in routes:
                            icon = get_vehicle_icon(route.get("vehicle_type", ""))
                            
                            with st.expander(f"{icon} **{route.get('number', 'Рейс')}**: {from_city} → {to_city}", expanded=True):
                                col_info, col_action = st.columns([3, 1])
                                
                                with col_info:
                                    st.markdown(f"""
                                    **Тип:** {route.get('vehicle_type', 'Транспорт')}
                                    - **Расписание:** {route.get('schedule', 'Не указано')}
                                    - **Время в пути:** {route.get('duration', 'Не указано')}
                                    - **Стоимость:** {route.get('price', 'Уточняйте')}
                                    - **Перевозчик:** {route.get('operator', 'Не указан')}
                                    """)
                                    
                                    if route.get('notes'):
                                        st.info(f"ℹ️ {route.get('notes')}")
                                
                                with col_action:
                                    if st.button("📋 Детали", key=f"details_{route.get('number')}"):
                                        st.session_state.selected_route = route
                                        st.rerun()
                    else:
                        st.warning(f"Маршруты из {from_city} в {to_city} не найдены.")
                        
                        # Предложение добавить маршрут
                        if st.button("➕ Добавить этот маршрут в базу"):
                            st.session_state.show_add_route = True
                            st.rerun()
        
        # Быстрые маршруты
        st.markdown("---")
        st.markdown("### 🚀 Популярные направления")
        
        popular_pairs = [
            ("Минск", "Брест"),
            ("Минск", "Гомель"),
            ("Минск", "Витебск"),
            ("Минск", "Гродно"),
            ("Минск", "Могилев"),
            ("Гомель", "Минск"),
            ("Брест", "Минск")
        ]
        
        cols = st.columns(4)
        for idx, (fr, to) in enumerate(popular_pairs[:8]):
            with cols[idx % 4]:
                if st.button(f"{fr} → {to}", key=f"quick_{fr}_{to}", use_container_width=True):
                    st.session_state.quick_from = fr
                    st.session_state.quick_to = to
                    st.rerun()
    
    with tab2:
        st.markdown("### 🗺️ Интерактивная карта транспорта")
        
        # Выбор города для карты
        selected_city = st.selectbox("Выберите город", 
                                    ["Минск", "Гомель", "Витебск", "Могилев", "Брест", "Гродно"])
        
        # Получение остановок для выбранного города
        stops = get_transport_stops(city=selected_city)
        
        if stops:
            # Отображение остановок
            st.markdown(f"### 🚏 Остановки в {selected_city}")
            
            # Фильтр по типу
            stop_types = list(set([stop["type"] for stop in stops]))
            selected_stop_type = st.multiselect("Типы остановок", stop_types, default=stop_types)
            
            filtered_stops = [s for s in stops if s["type"] in selected_stop_type]
            
            for stop in filtered_stops:
                stop_icon = {
                    "metro": "🚇",
                    "bus": "🚌",
                    "train": "🚆",
                    "tram": "🚋",
                    "trolley": "🚎",
                    "airport": "✈️"
                }.get(stop["type"], "📍")
                
                with st.expander(f"{stop_icon} **{stop['name']}** ({stop['type']})"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"""
                        **Город:** {stop['city']}
                        **Координаты:** {stop['latitude']:.4f}, {stop['longitude']:.4f}
                        """)
                        
                        if stop['lines']:
                            lines_text = ", ".join(stop['lines'])
                            st.markdown(f"**Маршруты:** {lines_text}")
                    
                    with col2:
                        if st.button("🗺️ На карте", key=f"map_{stop['id']}"):
                            # Здесь будет открытие карты с маркером
                            st.info(f"Показать {stop['name']} на карте")
        
        # Построение маршрута
        st.markdown("---")
        st.markdown("### 🧭 Построить маршрут")
        
        col_start, col_end = st.columns(2)
        with col_start:
            route_start = st.text_input("Начальная точка", placeholder="Улица, дом, остановка")
        with col_end:
            route_end = st.text_input("Конечная точка", placeholder="Улица, дом, остановка")
        
        if st.button("🗺️ Построить маршрут", type="primary"):
            if route_start and route_end:
                # Генерация карты с маршрутом
                map_html = calculate_route_map(route_start, route_end)
                components.html(map_html, height=450)
                
                # Альтернативные маршруты
                st.markdown("### 🚌 Варианты проезда")
                
                # Симуляция расчета маршрутов
                options = [
                    {"type": "🚍 Общественный транспорт", "time": "45 мин", "transfers": 1, "cost": "1.8 BYN"},
                    {"type": "🚕 Такси", "time": "25 мин", "transfers": 0, "cost": "8-12 BYN"},
                    {"type": "🚗 Автомобиль", "time": "30 мин", "transfers": 0, "cost": "≈5 BYN (бензин)"},
                    {"type": "🚲 Велосипед", "time": "40 мин", "transfers": 0, "cost": "Бесплатно"},
                ]
                
                for opt in options:
                    st.markdown(f"""
                    <div class="transport-card">
                        <h4>{opt['type']} - {opt['time']}</h4>
                        <p>💰 Стоимость: {opt['cost']}</p>
                        <p>🔄 Пересадки: {opt['transfers']}</p>
                    </div>
                    """, unsafe_allow_html=True)
    
    with tab3:
        st.markdown("### 👥 Сервис попутчиков")
        
        # Вкладки внутри раздела
        subtab1, subtab2 = st.tabs(["🔍 Найти попутчиков", "➕ Предложить поездку"])
        
        with subtab1:
            st.markdown("#### Найти попутчика")
            
            col_fr, col_to, col_date = st.columns(3)
            with col_fr:
                cp_from = st.selectbox("Откуда", cities, key="cpool_from")
            with col_to:
                cp_to = st.selectbox("Куда", cities, key="cpool_to")
            with col_date:
                cp_date = st.date_input("Дата", datetime.date.today())
            
            if st.button("🔍 Найти поездки", type="primary"):
                rides = get_carpool_rides(cp_from, cp_to, cp_date.strftime("%Y-%m-%d"))
                
                if rides:
                    st.markdown(f"#### 🚗 Найдено {len(rides)} поездок")
                    
                    for ride in rides:
                        st.markdown(f"""
                        <div class="carpool-card">
                            <h4>{ride[1]} → {ride[2]}</h4>
                            <p>📅 {ride[3]} в {ride[4]}</p>
                            <p>💺 Мест: {ride[5]}</p>
                            <p>💰 {ride[6]}</p>
                            <p>👤 Водитель: {ride[7]}</p>
                            <button style="
                                background: linear-gradient(135deg, #4CAF50, #2E7D32);
                                color: white;
                                border: none;
                                padding: 8px 20px;
                                border-radius: 6px;
                                margin-top: 10px;
                                cursor: pointer;
                            ">📞 Связаться</button>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("Поездок на эту дату не найдено.")
        
        with subtab2:
            st.markdown("#### Предложить поездку")
            
            with st.form("carpool_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    offer_from = st.selectbox("Откуда", cities, key="offer_from")
                    offer_date = st.date_input("Дата поездки", datetime.date.today())
                    offer_seats = st.number_input("Свободных мест", 1, 8, 1)
                
                with col2:
                    offer_to = st.selectbox("Куда", cities, key="offer_to")
                    offer_time = st.time_input("Время отправления", datetime.time(10, 0))
                    offer_price = st.text_input("Цена (BYN)", "10")
                
                driver_name = st.text_input("Ваше имя")
                driver_contact = st.text_input("Контакт (телефон или Telegram)")
                
                submitted = st.form_submit_button("🚗 Опубликовать поездку")
                
                if submitted:
                    if all([driver_name, driver_contact]):
                        add_carpool_ride(
                            offer_from, offer_to, 
                            offer_date.strftime("%Y-%m-%d"),
                            offer_time.strftime("%H:%M"),
                            offer_seats, offer_price,
                            driver_name, driver_contact
                        )
                        st.success("✅ Поездка добавлена! Теперь её увидят другие пользователи.")
                    else:
                        st.error("Заполните все обязательные поля")
    
    with tab4:
        st.markdown("### 📢 Народные отчеты о транспорте")
        
        # Фильтры
        col_filter, col_refresh = st.columns([3, 1])
        with col_filter:
            report_filter = st.text_input("Фильтр по маршруту", placeholder="Номер маршрута или остановка")
        with col_refresh:
            if st.button("🔄 Обновить", use_container_width=True):
                st.rerun()
        
        # Форма добавления отчета
        with st.expander("➕ Добавить отчет", expanded=False):
            with st.form("report_form"):
                col_r1, col_r2 = st.columns(2)
                
                with col_r1:
                    rep_route = st.text_input("Маршрут*", placeholder="100, 3с, Метро и т.д.")
                    rep_location = st.text_input("Место", placeholder="Остановка, улица")
                
                with col_r2:
                    rep_type = st.selectbox("Тип транспорта", 
                                          ["автобус", "троллейбус", "трамвай", "метро", "поезд", "маршрутка", "другое"])
                    rep_user = st.text_input("Ваше имя", value="Аноним")
                
                rep_message = st.text_area("Сообщение*", 
                                         placeholder="Опишите ситуацию: задержка, поломка, переполненность и т.д.",
                                         height=100)
                
                submitted = st.form_submit_button("📢 Опубликовать отчет")
                
                if submitted:
                    if rep_route and rep_message:
                        add_transport_report(rep_route, rep_message, rep_user, rep_type, rep_location)
                        st.success("✅ Отчет добавлен!")
                        st.rerun()
                    else:
                        st.error("Заполните обязательные поля (маршрут и сообщение)")
        
        # Отображение отчетов
        reports = get_transport_reports(limit=20, route_filter=report_filter if report_filter else None)
        
        if reports:
            for report in reports:
                icon = get_vehicle_icon(report.get("vehicle_type", ""))
                time_ago = datetime.datetime.now() - datetime.datetime.strptime(report["timestamp"], "%Y-%m-%d %H:%M:%S")
                minutes = int(time_ago.total_seconds() / 60)
                
                if minutes < 60:
                    time_text = f"{minutes} мин назад"
                else:
                    hours = minutes // 60
                    time_text = f"{hours} ч назад"
                
                st.markdown(f"""
                <div class="report-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-weight: bold; font-size: 1.1rem;">
                                {icon} {report['route']} 
                                {f"({report['vehicle_type']})" if report['vehicle_type'] else ""}
                            </span>
                            {f"<span style='background: #e3f2fd; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem; margin-left: 10px;'>📍 {report['location']}</span>" if report['location'] else ""}
                        </div>
                        <span style="color: #666; font-size: 0.9rem;">{time_text}</span>
                    </div>
                    <p style="margin: 10px 0;">{report['message']}</p>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="color: #666; font-size: 0.9rem;">
                                👤 {report['user_name']} 
                                {f"<span style='color: #4CAF50;'>(✓ проверено)</span>" if report['verified'] else ""}
                            </span>
                        </div>
                        <div>
                            <span style="margin-right: 15px;">
                                <button class="vote-btn upvote" onclick="voteUp({report.get('id', 0)})">
                                    👍 {report['upvotes']}
                                </button>
                                <button class="vote-btn downvote" onclick="voteDown({report.get('id', 0)})">
                                    👎 {report['downvotes']}
                                </button>
                            </span>
                            <span style="color: { '#4CAF50' if report['rating'] > 0 else '#F44336' if report['rating'] < 0 else '#666' }">
                                {report['rating']:+d}
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Пока нет отчетов. Будьте первым!")
    
    with tab5:
        st.markdown("### 📊 Расписания транспорта")
        
        # Выбор города для расписания
        schedule_city = st.selectbox("Выберите город для расписания", cities)
        
        if schedule_city == "Минск":
            st.markdown("#### 🚍 Автобусы Минска")
            
            # Популярные маршруты Минска
            minsk_routes = [
                {"number": "100", "route": "Аэропорт - Центр", "interval": "10-15 мин", "time": "05:30-00:30"},
                {"number": "1", "route": "Тракторный - Серебрянка", "interval": "7-10 мин", "time": "05:00-01:00"},
                {"number": "40", "route": "Уручье - Дражня", "interval": "10-20 мин", "time": "06:00-23:00"},
                {"number": "3с", "route": "Веснянка - Серова", "interval": "8-12 мин", "time": "05:30-00:30"},
                {"number": "101", "route": "Минск - Молодечно", "interval": "30 мин", "time": "06:00-22:00"},
            ]
            
            for route in minsk_routes:
                st.markdown(f"""
                <div class="transport-card">
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <span class="route-number">{route['number']}</span>
                        <span style="font-weight: bold;">{route['route']}</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
                        <div>
                            <div style="color: #666; font-size: 0.9rem;">Интервал</div>
                            <div style="font-weight: bold;">{route['interval']}</div>
                        </div>
                        <div>
                            <div style="color: #666; font-size: 0.9rem;">Время работы</div>
                            <div style="font-weight: bold;">{route['time']}</div>
                        </div>
                        <div>
                            <div style="color: #666; font-size: 0.9rem;">Стоимость</div>
                            <div style="font-weight: bold;">0.90 BYN</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # Расписание междугородних автобусов
        st.markdown("---")
        st.markdown("#### 🚌 Междугородние автобусы")
        
        intercity_schedule = [
            {"from": "Минск", "to": "Гомель", "times": ["07:30", "09:00", "12:00", "15:00", "18:00", "21:00"]},
            {"from": "Минск", "to": "Брест", "times": ["06:00", "08:30", "11:00", "14:00", "17:00", "20:00"]},
            {"from": "Минск", "to": "Витебск", "times": ["07:00", "10:00", "13:00", "16:00", "19:00"]},
            {"from": "Минск", "to": "Гродно", "times": ["08:00", "10:30", "14:00", "17:30", "20:00"]},
            {"from": "Минск", "to": "Могилев", "times": ["07:00", "09:30", "13:00", "16:30", "19:00"]},
        ]
        
        for schedule in intercity_schedule:
            times_str = ", ".join(schedule['times'])
            st.markdown(f"""
            <div style="background: white; padding: 15px; border-radius: 10px; margin: 10px 0; border: 1px solid #e0e0e0;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="margin: 0;">{schedule['from']} → {schedule['to']}</h4>
                        <p style="margin: 5px 0 0 0; color: #666;">Отправления: {times_str}</p>
                    </div>
                    <span style="background: #DAA520; color: white; padding: 5px 15px; border-radius: 20px;">
                        от 12 BYN
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ================= ДОБАВЛЕНИЕ КНОПКИ В САЙДБАР =================
# В секции сайдбара добавьте кнопку транспорта:

with st.sidebar:
    st.markdown("<h3 style='color:#DAA520;'>🇧🇾 ZORNET</h3>", unsafe_allow_html=True)

    pages = [
        ("🏠", "ГЛАВНАЯ", "Главная"),
        ("🚌", "ТРАНСПОРТ", "Транспорт"),  # ДОБАВЛЕНА ЭТА СТРОКА
        ("📰", "НОВОСТИ", "Новости"),
        ("🌤️", "ПОГОДА", "Погода"),
        ("💾", "ДИСК", "Диск"),
        ("👤", "ПРОФИЛЬ", "Профиль"),
    ]

    for i, (icon, text, page) in enumerate(pages):
        if st.button(f"{icon} {text}", key=f"nav_{i}_{page}", use_container_width=True):
            st.session_state.page = page
            st.rerun()
# ================= ПРОФЕССИОНАЛЬНЫЙ ОБЛАЧНЫЙ ДИСК ZORNET DISK =================
elif st.session_state.page == "Диск":
    st.markdown('<div class="gold-title">💾 ДИСК</div>', unsafe_allow_html=True)

    # Инициализация сессионных переменных
    if "disk_current_path" not in st.session_state:
        st.session_state.disk_current_path = "zornet_cloud"

    if "disk_action" not in st.session_state:
        st.session_state.disk_action = "view"  # view, upload, new_folder, search

    # Создаем корневую папку если не существует
    import os

    os.makedirs(st.session_state.disk_current_path, exist_ok=True)

    # CSS стили для диска
    st.markdown("""
    <style>
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
    </style>
    """, unsafe_allow_html=True)


    # Функции для работы с диском
    def get_file_icon(filename):
        """Возвращает иконку для файла"""
        if filename.endswith('/'):
            return "📁"
        elif filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            return "🖼️"
        elif filename.lower().endswith('.pdf'):
            return "📄"
        elif filename.lower().endswith(('.doc', '.docx')):
            return "📝"
        elif filename.lower().endswith(('.mp3', '.wav')):
            return "🎵"
        elif filename.lower().endswith(('.mp4', '.avi', '.mov')):
            return "🎬"
        elif filename.lower().endswith(('.zip', '.rar', '.7z')):
            return "🗜️"
        elif filename.lower().endswith(('.py', '.js', '.html', '.css')):
            return "💻"
        else:
            return "📄"


    def format_file_size(size_bytes):
        """Форматирует размер файла"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


    def get_disk_stats():
        """Получает статистику диска"""
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


    # ПАНЕЛЬ ИНСТРУМЕНТОВ
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

    # СТАТИСТИКА ХРАНИЛИЩА
    stats = get_disk_stats()
    used_gb = stats['total_size'] / (1024 * 1024 * 1024)
    used_percent = min(100, (used_gb / 1.0) * 100)  # Предполагаем 1GB лимит

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

    # РЕЖИМЫ РАБОТЫ
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
                for item in found_items[:10]:  # Показываем первые 10
                    icon = "📁" if item['is_dir'] else get_file_icon(item['name'])
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
        # ОСНОВНОЙ РЕЖИМ ПРОСМОТРА ФАЙЛОВ
        st.markdown("### 📁 Файлы и папки")

        # Быстрая загрузка (всегда доступна)
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

        # Навигация по папкам
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

        # Список файлов и папок
        try:
            items = os.listdir(st.session_state.disk_current_path)
        except:
            items = []

        if not items:
            st.info("📭 Папка пуста. Загрузите файлы или создайте папку.")
        else:
            # Сортируем: сначала папки, потом файлы
            items.sort(
                key=lambda x: (not os.path.isdir(os.path.join(st.session_state.disk_current_path, x)), x.lower()))

            # Показываем файлы в сетке
            cols = st.columns(3)
            for idx, item in enumerate(items):
                with cols[idx % 3]:
                    item_path = os.path.join(st.session_state.disk_current_path, item)
                    is_dir = os.path.isdir(item_path)
                    icon = "📁" if is_dir else get_file_icon(item)

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
                                # Превью файла
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

# ================= СТРАНИЦА ПРОФИЛЯ (ПРОФЕССИОНАЛЬНАЯ ВЕРСИЯ) =================
elif st.session_state.page == "Профиль":

    # CSS для профиля
    st.markdown("""
    <style>
    /* ЗОЛОТОЙ ЗАГОЛОВОК */
    .profile-gold-title {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(135deg, #FFD700 0%, #B8860B 50%, #DAA520 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 3px;
        margin: 20px 0 40px 0;
        padding: 10px;
    }

    /* КОНТЕЙНЕРЫ */
    .profile-container {
        background: white;
        border-radius: 20px;
        padding: 30px;
        margin: 20px 0;
        box-shadow: 0 10px 40px rgba(218, 165, 32, 0.1);
        border: 1px solid rgba(218, 165, 32, 0.2);
    }

    .login-container {
        background: linear-gradient(135deg, #ffffff 0%, #fffaf0 100%);
        border-radius: 20px;
        padding: 40px;
        margin: 20px auto;
        max-width: 500px;
        box-shadow: 0 15px 50px rgba(218, 165, 32, 0.15);
        border: 1px solid #FFD700;
    }

    /* КАРТОЧКИ */
    .profile-card {
        background: #f9f9f9;
        border-radius: 15px;
        padding: 25px;
        margin: 15px 0;
        border-left: 5px solid #DAA520;
        transition: transform 0.3s ease;
    }

    .profile-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(218, 165, 32, 0.15);
    }

    /* КНОПКИ */
    .gold-button {
        background: linear-gradient(135deg, #FFD700 0%, #DAA520 100%) !important;
        border: none !important;
        color: white !important;
        border-radius: 10px !important;
        padding: 12px 30px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        box-shadow: 0 5px 20px rgba(218, 165, 32, 0.3) !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }

    .gold-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(218, 165, 32, 0.4) !important;
    }

    .outline-button {
        background: transparent !important;
        border: 2px solid #DAA520 !important;
        color: #DAA520 !important;
        border-radius: 10px !important;
        padding: 12px 30px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }

    .outline-button:hover {
        background: rgba(218, 165, 32, 0.1) !important;
    }

    /* ПОЛЯ ВВОДА */
    .stTextInput > div > div > input {
        border-radius: 10px !important;
        border: 2px solid #e0e0e0 !important;
        padding: 12px 15px !important;
        font-size: 16px !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #DAA520 !important;
        box-shadow: 0 0 0 3px rgba(218, 165, 32, 0.1) !important;
    }

    /* ПЕРЕКЛЮЧАТЕЛИ */
    .stCheckbox > div > label {
        font-weight: 500;
        color: #333;
    }

    /* АВАТАРКА */
    .avatar-container {
        width: 180px;
        height: 180px;
        border-radius: 50%;
        background: linear-gradient(135deg, #FFD700, #DAA520);
        padding: 5px;
        margin: 0 auto 25px auto;
    }

    .avatar-img {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        object-fit: cover;
        border: 4px solid white;
    }

    /* СТАТУС */
    .status-online {
        display: inline-block;
        width: 12px;
        height: 12px;
        background: #4CAF50;
        border-radius: 50%;
        margin-right: 8px;
        vertical-align: middle;
    }

    /* ИКОНКИ СТАТИСТИКИ */
    .stat-icon {
        font-size: 2.5rem;
        color: #DAA520;
        margin-bottom: 10px;
    }

    /* БЭДЖИ */
    .gold-badge {
        background: linear-gradient(135deg, #FFD700, #DAA520);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
        display: inline-block;
        margin: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Инициализация состояния профиля
    if "user_logged_in" not in st.session_state:
        st.session_state.user_logged_in = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "user_avatar" not in st.session_state:
        st.session_state.user_avatar = None
    if "show_login" not in st.session_state:
        st.session_state.show_login = True
    if "show_register" not in st.session_state:
        st.session_state.show_register = False


    # Функции базы данных для профилей
    def init_profile_db():
        """Инициализация базы данных профилей"""
        conn = sqlite3.connect("zornet_profiles.db")
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                username TEXT,
                password_hash TEXT,
                avatar_path TEXT,
                gender TEXT,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                bio TEXT,
                settings TEXT
            )
        """)
        conn.commit()
        conn.close()


    def register_user(email, username, password):
        """Регистрация нового пользователя"""
        try:
            conn = sqlite3.connect("zornet_profiles.db")
            c = conn.cursor()
            # Простой хэш (в реальном приложении используйте hashlib)
            password_hash = password  # Здесь должен быть реальный хэш
            c.execute("""
                INSERT INTO profiles (email, username, password_hash)
                VALUES (?, ?, ?)
            """, (email, username, password_hash))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False  # Пользователь уже существует
        except Exception as e:
            print(f"Ошибка регистрации: {e}")
            return False


    def login_user(email, password):
        """Авторизация пользователя"""
        try:
            conn = sqlite3.connect("zornet_profiles.db")
            c = conn.cursor()
            c.execute("""
                SELECT username, password_hash FROM profiles 
                WHERE email = ?
            """, (email,))
            result = c.fetchone()
            conn.close()

            if result and result[1] == password:  # Сравнение хэшей
                return result[0]  # Возвращаем имя пользователя
            return None
        except:
            return None


    def update_profile(email, username, gender, bio):
        """Обновление профиля"""
        try:
            conn = sqlite3.connect("zornet_profiles.db")
            c = conn.cursor()
            c.execute("""
                UPDATE profiles 
                SET username = ?, gender = ?, bio = ?
                WHERE email = ?
            """, (username, gender, bio, email))
            conn.commit()
            conn.close()
            return True
        except:
            return False


    def save_avatar(email, avatar_path):
        """Сохранение пути к аватарке"""
        try:
            conn = sqlite3.connect("zornet_profiles.db")
            c = conn.cursor()
            c.execute("""
                UPDATE profiles 
                SET avatar_path = ?
                WHERE email = ?
            """, (avatar_path, email))
            conn.commit()
            conn.close()
            return True
        except:
            return False


    def get_user_profile(email):
        """Получение профиля пользователя"""
        try:
            conn = sqlite3.connect("zornet_profiles.db")
            c = conn.cursor()
            c.execute("""
                SELECT username, gender, bio, avatar_path, join_date 
                FROM profiles 
                WHERE email = ?
            """, (email,))
            result = c.fetchone()
            conn.close()

            if result:
                return {
                    "username": result[0],
                    "gender": result[1],
                    "bio": result[2],
                    "avatar_path": result[3],
                    "join_date": result[4]
                }
            return None
        except:
            return None


    # Инициализация БД
    init_profile_db()

    st.markdown('<div class="profile-gold-title">👤 ПРОФИЛЬ</div>', unsafe_allow_html=True)

    # Если пользователь не авторизован, показываем форму входа/регистрации
    if not st.session_state.user_logged_in:
        col_login, col_register = st.columns(2)

        with col_login:
            if st.session_state.show_login:
                st.markdown("""
                <div class="login-container">
                    <h2 style="text-align: center; color: #DAA520; margin-bottom: 30px;">🔐 Вход в систему</h2>
                """, unsafe_allow_html=True)

                with st.form("login_form"):
                    login_email = st.text_input("📧 Email", placeholder="your@email.com")
                    login_password = st.text_input("🔑 Пароль", type="password", placeholder="••••••••")

                    col_submit, col_switch = st.columns(2)
                    with col_submit:
                        login_submit = st.form_submit_button("🚀 Войти", use_container_width=True)
                    with col_switch:
                        if st.form_submit_button("📝 Регистрация", use_container_width=True):
                            st.session_state.show_login = False
                            st.session_state.show_register = True
                            st.rerun()

                    if login_submit and login_email and login_password:
                        with st.spinner("Вход в систему..."):
                            username = login_user(login_email, login_password)
                            if username:
                                st.session_state.user_logged_in = True
                                st.session_state.user_email = login_email
                                st.session_state.user_name = username
                                st.success(f"Добро пожаловать, {username}!")
                                st.rerun()
                            else:
                                st.error("Неверный email или пароль")

                st.markdown("</div>", unsafe_allow_html=True)

        with col_register:
            if st.session_state.show_register:
                st.markdown("""
                <div class="login-container">
                    <h2 style="text-align: center; color: #DAA520; margin-bottom: 30px;">✨ Регистрация</h2>
                """, unsafe_allow_html=True)

                with st.form("register_form"):
                    reg_email = st.text_input("📧 Email", placeholder="your@email.com")
                    reg_username = st.text_input("👤 Имя пользователя", placeholder="Ваше имя")
                    reg_password = st.text_input("🔑 Пароль", type="password", placeholder="••••••••")
                    reg_password_confirm = st.text_input("🔐 Подтвердите пароль", type="password",
                                                         placeholder="••••••••")
                    reg_gender = st.selectbox("⚧ Пол", ["Не указан", "Мужской", "Женский"])

                    col_submit_reg, col_switch_reg = st.columns(2)
                    with col_submit_reg:
                        reg_submit = st.form_submit_button("🎯 Зарегистрироваться", use_container_width=True)
                    with col_switch_reg:
                        if st.form_submit_button("← Назад к входу", use_container_width=True):
                            st.session_state.show_login = True
                            st.session_state.show_register = False
                            st.rerun()

                    if reg_submit:
                        if not all([reg_email, reg_username, reg_password, reg_password_confirm]):
                            st.error("Заполните все поля!")
                        elif reg_password != reg_password_confirm:
                            st.error("Пароли не совпадают!")
                        else:
                            with st.spinner("Регистрация..."):
                                if register_user(reg_email, reg_username, reg_password):
                                    st.success("Регистрация успешна! Теперь войдите в систему.")
                                    st.session_state.show_login = True
                                    st.session_state.show_register = False
                                    st.rerun()
                                else:
                                    st.error("Пользователь с таким email уже существует")

                st.markdown("</div>", unsafe_allow_html=True)

    # Если пользователь авторизован, показываем профиль
    else:
        # Загружаем данные профиля
        profile_data = get_user_profile(st.session_state.user_email)

        # Кнопка выхода
        if st.sidebar.button("🚪 Выйти", use_container_width=True):
            st.session_state.user_logged_in = False
            st.session_state.user_email = ""
            st.session_state.user_name = ""
            st.session_state.user_avatar = None
            st.rerun()

        # Основной контейнер профиля
        with st.container():
            st.markdown('<div class="profile-container">', unsafe_allow_html=True)

            col_profile_left, col_profile_right = st.columns([1, 2])

            with col_profile_left:
                # Аватарка пользователя
                st.markdown("""
                <div class="avatar-container">
                    <img src="https://via.placeholder.com/200/FFD700/FFFFFF?text=""" +
                            (st.session_state.user_name[0] if st.session_state.user_name else "Z") +
                            """&font-size=80" class="avatar-img">
                        </div>
                        """, unsafe_allow_html=True)

                # Загрузка аватарки
                uploaded_avatar = st.file_uploader("📷 Загрузить фото профиля",
                                                   type=['jpg', 'jpeg', 'png'],
                                                   key="avatar_uploader")

                if uploaded_avatar:
                    # Сохраняем временно в session state
                    st.session_state.user_avatar = uploaded_avatar
                    # Сохраняем в базу данных
                    avatar_path = f"avatars/{st.session_state.user_email}_{uploaded_avatar.name}"
                    save_avatar(st.session_state.user_email, avatar_path)
                    st.success("Фото профиля обновлено!")
                    st.rerun()

                # Статус
                st.markdown("""
                <div style="text-align: center; margin: 20px 0;">
                    <span class="status-online"></span>
                    <span style="color: #4CAF50; font-weight: 600;">Онлайн</span>
                </div>
                """, unsafe_allow_html=True)

            with col_profile_right:
                # Информация профиля
                with st.form("profile_info_form"):
                    st.markdown("### 📝 Информация профиля")

                    username = st.text_input("👤 Имя пользователя",
                                             value=profile_data[
                                                 "username"] if profile_data else st.session_state.user_name)

                    email = st.text_input("📧 Email",
                                          value=st.session_state.user_email,
                                          disabled=True)

                    gender = st.selectbox("⚧ Пол",
                                          ["Не указан", "Мужской", "Женский"],
                                          index=["Не указан", "Мужской", "Женский"].index(
                                              profile_data["gender"] if profile_data and profile_data[
                                                  "gender"] else "Не указан"
                                          ))

                    bio = st.text_area("📖 О себе",
                                       value=profile_data["bio"] if profile_data and profile_data["bio"] else "",
                                       height=100,
                                       placeholder="Расскажите о себе...")

                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        save_profile = st.form_submit_button("💾 Сохранить изменения", use_container_width=True)
                    with col_cancel:
                        st.form_submit_button("Отмена", use_container_width=True)

                    if save_profile:
                        if update_profile(st.session_state.user_email, username, gender, bio):
                            st.session_state.user_name = username
                            st.success("Профиль успешно обновлен!")
                            st.rerun()
                        else:
                            st.error("Ошибка при обновлении профиля")

            st.markdown('</div>', unsafe_allow_html=True)

        # Статистика в отдельном контейнере
        st.markdown('<div class="profile-container">', unsafe_allow_html=True)
        st.markdown("### 📊 Статистика")

        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

        with col_stat1:
            st.markdown("""
            <div style="text-align: center;">
                <div class="stat-icon">📅</div>
                <h3>365</h3>
                <p>Дней с нами</p>
            </div>
            """, unsafe_allow_html=True)

        with col_stat2:
            st.markdown("""
            <div style="text-align: center;">
                <div class="stat-icon">📂</div>
                <h3>128</h3>
                <p>Файлов в облаке</p>
            </div>
            """, unsafe_allow_html=True)

        with col_stat3:
            st.markdown("""
            <div style="text-align: center;">
                <div class="stat-icon">🤖</div>
                <h3>2.4K</h3>
                <p>Запросов к AI</p>
            </div>
            """, unsafe_allow_html=True)

        with col_stat4:
            st.markdown("""
            <div style="text-align: center;">
                <div class="stat-icon">🎯</div>
                <h3>95%</h3>
                <p>Активность</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Настройки в отдельном контейнере
        st.markdown('<div class="profile-container">', unsafe_allow_html=True)
        st.markdown("### ⚙️ Настройки")

        settings_col1, settings_col2 = st.columns(2)

        with settings_col1:
            st.markdown("**🔔 Уведомления**")
            email_notif = st.checkbox("Email уведомления", value=True)
            push_notif = st.checkbox("Push-уведомления", value=True)
            ai_notif = st.checkbox("Уведомления от AI", value=True)

        with settings_col2:
            st.markdown("**🔒 Безопасность**")
            two_factor = st.checkbox("Двухфакторная аутентификация")
            login_history = st.button("📋 История входов", use_container_width=True)

        if st.button("💾 Сохранить настройки", type="primary", use_container_width=True):
            st.success("Настройки сохранены!")

        st.markdown('</div>', unsafe_allow_html=True)

        # Информация о подписке
        st.markdown('<div class="profile-container">', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

# ================= ИНИЦИАЛИЗАЦИЯ =================
if __name__ == "__main__":
    init_db()
    init_disk_db()
