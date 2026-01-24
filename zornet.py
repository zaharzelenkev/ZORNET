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
            placeholder="Поиск в интернете... Нажмите Enter для поиска в Google",
            key="main_search",
            label_visibility="collapsed"
        )
        submitted = st.form_submit_button("🔍 Искать в ZORNET", use_container_width=True)

    # Если форма отправлена (Enter или кнопка)
    if submitted and search_query:
        # Кодируем запрос для URL
        encoded_query = requests.utils.quote(search_query)
        google_url = f"https://www.google.com/search?q={encoded_query}"
        
        # Перенаправляем в Google в той же вкладке
        js_code = f"""
        <script>
            window.location.href = "{google_url}";
        </script>
        """
        components.html(js_code, height=0, width=0)
        
        # Показываем сообщение о перенаправлении
        st.info("Перенаправление в Google... Если не сработало, нажмите кнопку ниже:")
        st.markdown(f'<a href="{google_url}" target="_self"><button style="padding:10px 20px;background:#4285F4;color:white;border:none;border-radius:5px;cursor:pointer;">🔍 Открыть Google</button></a>', unsafe_allow_html=True)
        
        # Останавливаем дальнейшее выполнение
        st.stop()
