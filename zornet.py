import streamlit as st
import sqlite3
import datetime
import os
import pytz
import requests
import feedparser
from PIL import Image
from pathlib import Path
import mimetypes
from duckduckgo_search import DDGS
from huggingface_hub import InferenceClient

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
        ("🤖", "ZORNET AI", "ZORNET AI"),
        ("📰", "НОВОСТИ", "Новости"),
        ("🌤️", "ПОГОДА", "Погода"),
        ("💾", "ДИСК", "Диск"),
        ("🚌", "ТРАНСПОРТ", "Транспорт"),
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

    search_query = st.text_input(
        "",
        placeholder="Поиск в интернете...",
        key="main_search",
        label_visibility="collapsed"
    )

    if search_query:
        st.markdown(f"### 🔍 Результаты поиска: **{search_query}**")
        with st.spinner("Ищу информацию..."):
            results = search_zornet(search_query, num_results=5)
            if results:
                for idx, result in enumerate(results):
                    st.markdown(f"""
                    <div class="search-result">
                        <div style="font-weight: 600; color: #1a1a1a; font-size: 16px;">
                            {idx + 1}. {result['title']}
                        </div>
                        <div style="color: #1a73e8; font-size: 13px; margin: 5px 0;">
                            {result['url'][:60]}...
                        </div>
                        <div style="color: #555; font-size: 14px;">
                            {result['snippet']}
                        </div>
                        <div style="margin-top: 10px;">
                            <a href="{result['url']}" target="_blank" 
                               style="padding: 6px 12px; background: #DAA520; color: white; 
                                      border-radius: 6px; text-decoration: none; font-size: 12px;">
                                Перейти на сайт
                            </a>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("По вашему запросу ничего не найдено.")

# ================= СТРАНИЦА AI =================
elif st.session_state.page == "ZORNET AI":
    st.markdown('<div class="gold-title">🤖 ZORNET AI</div>', unsafe_allow_html=True)
    
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = [
            {"role": "assistant", "content": "Привет! Я ZORNET AI. Чем могу помочь?"}
        ]
    
    for message in st.session_state.ai_messages:
        if message["role"] == "user":
            st.markdown(f'<div class="user-message">{message["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="ai-message">{message["content"]}</div>', unsafe_allow_html=True)
    
    if prompt := st.chat_input("Спросите ZORNET AI..."):
        st.session_state.ai_messages.append({"role": "user", "content": prompt})
        
        with st.spinner("ZORNET думает..."):
            response = ask_hf_ai(prompt)
            st.session_state.ai_messages.append({"role": "assistant", "content": response})
        
        st.rerun()

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
    
    # Вкладки
    tab1, tab2 = st.tabs(["📍 По местоположению", "🏙️ По городу"])
    
    with tab1:
        st.subheader("Погода по вашему местоположению")
        
        # Способ 1: Запрос геолокации
        st.markdown("### Способ 1: Запрос точного местоположения")
        
        try:
            # Пытаемся импортировать библиотеку
            import streamlit_geolocation
            
            if st.button("📍 Запросить доступ к моему местоположению", type="primary", key="geo_request"):
                with st.spinner("Запрашиваю разрешение у браузера..."):
                    location = streamlit_geolocation.get_location()
                    
                    if location and location.get("latitude"):
                        lat = location["latitude"]
                        lon = location["longitude"]
                        
                        st.success(f"✅ Разрешение получено! Координаты: {lat:.4f}, {lon:.4f}")
                        
                        # Получаем погоду
                        with st.spinner("Получаю актуальную погоду..."):
                            weather_data = get_weather_by_coords(lat, lon)
                            
                            if weather_data:
                                st.session_state.weather_data = weather_data
                                st.session_state.user_city = weather_data["current"]["city"]
                                st.rerun()
                            else:
                                st.error("⚠️ Не удалось получить данные о погоде")
                    else:
                        st.error("❌ Не удалось получить местоположение. Проверьте разрешения браузера.")
                        
        except ImportError:
            st.error("❌ Библиотека streamlit-geolocation не установлена!")
            st.info("Добавьте 'streamlit-geolocation' в файл requirements.txt")
        
        # Способ 2: Автоматическое определение
        st.markdown("### Способ 2: Автоматическое определение")
        
        if st.button("🌍 Определить мой город автоматически", key="auto_city"):
            with st.spinner("Определяю ваш город..."):
                try:
                    # Получаем город по IP
                    response = requests.get('https://ipapi.co/json/', timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        city = data.get("city", "Минск")
                        country = data.get("country_name", "Беларусь")
                        lat = data.get("latitude", 53.9)
                        lon = data.get("longitude", 27.5667)
                        
                        st.success(f"📍 Определено: {city}, {country}")
                        
                        # Получаем погоду
                        weather_data = get_weather_by_coords(lat, lon)
                        
                        if weather_data:
                            st.session_state.weather_data = weather_data
                            st.session_state.user_city = city
                            st.rerun()
                        else:
                            st.error("Не удалось получить погоду")
                    else:
                        st.error("Не удалось определить местоположение")
                except:
                    st.error("Ошибка подключения")
        
        # Способ 3: Ручной ввод
        with st.expander("🔧 Ввести координаты вручную"):
            col1, col2 = st.columns(2)
            with col1:
                manual_lat = st.number_input("Широта", value=53.9, format="%.4f", key="man_lat")
            with col2:
                manual_lon = st.number_input("Долгота", value=27.5667, format="%.4f", key="man_lon")
            
            if st.button("Получить погоду по координатам", key="manual_coords"):
                with st.spinner("Получаю погоду..."):
                    weather_data = get_weather_by_coords(manual_lat, manual_lon)
                    
                    if weather_data:
                        st.session_state.weather_data = weather_data
                        st.session_state.user_city = weather_data["current"]["city"]
                        st.rerun()
                    else:
                        st.error("Не удалось получить погоду")
    
    with tab2:
        st.subheader("Поиск погоды по городу")
        
        city_input = st.text_input(
            "Введите название города",
            placeholder="Например: Минск, Москва, Лондон...",
            key="city_input"
        )
        
        if st.button("🔍 Найти погоду", type="primary", key="search_city"):
            if city_input:
                with st.spinner(f"Ищу погоду для {city_input}..."):
                    weather_data = get_weather_by_city(city_input)
                    
                    if weather_data:
                        st.session_state.weather_data = weather_data
                        st.session_state.user_city = city_input
                        st.rerun()
                    else:
                        st.error(f"Город '{city_input}' не найден")
            else:
                st.warning("Введите название города")
        
        # Быстрые города
        st.markdown("### 🏙️ Быстрый выбор")
        quick_cities = ["Минск", "Гомель", "Витебск", "Могилёв", "Брест", "Гродно"]
        cols = st.columns(3)
        
        for idx, city in enumerate(quick_cities):
            with cols[idx % 3]:
                if st.button(city, key=f"quick_{city}", use_container_width=True):
                    with st.spinner(f"Загружаю {city}..."):
                        weather_data = get_weather_by_city(city)
                        
                        if weather_data:
                            st.session_state.weather_data = weather_data
                            st.session_state.user_city = city
                            st.rerun()
    
    # ===== ОТОБРАЖЕНИЕ ПОГОДЫ (если есть данные) =====
    if st.session_state.weather_data:
        current = st.session_state.weather_data["current"]
        
        st.markdown("---")
        st.markdown(f"## 🌤️ Погода в {current['city']}, {current['country']}")
        
        # Основная информация
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"""
            <div style="font-size: 4.5rem; font-weight: 800; color: #1a1a1a; line-height: 1;">
                {current['temp']}°C
            </div>
            <div style="font-size: 1.8rem; color: #666; margin-top: 10px;">
                {get_weather_icon(current['icon'])} {current['description']}
            </div>
            <div style="font-size: 1.2rem; color: #888; margin-top: 5px;">
                💁 Ощущается как {current['feels_like']}°C
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 6rem;">
                    {get_weather_icon(current['icon'])}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Детали
        st.markdown("### 📊 Детали")
        detail_cols = st.columns(4)
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
        
        for i in range(0, 8, 2):
            col1, col2 = st.columns(2)
            with col1:
                name, value = details[i]
                st.markdown(f"""
                <div style="
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 12px;
                    margin-bottom: 10px;
                    border-left: 4px solid #DAA520;
                ">
                    <div style="font-size: 0.9rem; color: #666;">{name}</div>
                    <div style="font-size: 1.3rem; font-weight: bold; color: #1a1a1a;">{value}</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                if i + 1 < len(details):
                    name, value = details[i + 1]
                    st.markdown(f"""
                    <div style="
                        background: #f8f9fa;
                        padding: 15px;
                        border-radius: 12px;
                        margin-bottom: 10px;
                        border-left: 4px solid #DAA520;
                    ">
                        <div style="font-size: 0.9rem; color: #666;">{name}</div>
                        <div style="font-size: 1.3rem; font-weight: bold; color: #1a1a1a;">{value}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Прогноз
        if st.session_state.weather_data.get("forecast"):
            st.markdown("### 📅 Прогноз на 5 дней")
            
            forecast = st.session_state.weather_data["forecast"]["list"]
            days = {}
            
            for item in forecast:
                date = item["dt_txt"].split(" ")[0]
                if date not in days:
                    days[date] = item
            
            forecast_dates = list(days.keys())[:5]
            forecast_cols = st.columns(5)
            
            for idx, date in enumerate(forecast_dates):
                with forecast_cols[idx]:
                    day = days[date]
                    day_name = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%a")
                    
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, #6ecbf5 0%, #059be5 100%);
                        border-radius: 12px;
                        padding: 15px;
                        text-align: center;
                        color: white;
                        box-shadow: 0 4px 15px rgba(6, 147, 227, 0.3);
                    ">
                        <div style="font-weight: bold; font-size: 1.1rem; margin-bottom: 10px;">
                            {day_name}
                        </div>
                        <div style="font-size: 2.5rem; margin: 10px 0;">
                            {get_weather_icon(day['weather'][0]['icon'])}
                        </div>
                        <div style="font-size: 1.5rem; font-weight: bold;">
                            {round(day['main']['temp'])}°C
                        </div>
                        <div style="font-size: 0.8rem; margin-top: 8px; opacity: 0.9;">
                            {day['weather'][0]['description']}
                        </div>
                        <div style="font-size: 0.7rem; margin-top: 5px; opacity: 0.8;">
                            💧 {day['main']['humidity']}% | 💨 {day['wind']['speed']} м/с
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

# ================= СТРАНИЦА ТРАНСПОРТА =================
elif st.session_state.page == "Транспорт":
    st.markdown('<div class="gold-title">🚌 ТРАНСПОРТ</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["🚇 Метро", "🚌 Автобусы/Трамваи", "🚕 Такси", "🚂 Железная дорога"])
    
    with tab1:
        st.subheader("Минское метро")
        for station in get_minsk_metro():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{station['name']}**")
            with col2:
                st.write(f"Линия {station['line']}")
            with col3:
                st.success(f"🚇 {station['next']}")
    
    with tab2:
        st.subheader("Автобусы и трамваи")
        for route in get_bus_trams():
            col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
            with col1:
                st.write(f"**{route['number']}**")
            with col2:
                st.write(f"{route['type']}")
            with col3:
                st.write(f"{route['from']} → {route['to']}")
            with col4:
                st.info(f"⏱️ {route['next']}")
    
    with tab3:
        st.subheader("Сравнение цен такси")
        for service in get_taxi_prices():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{service['name']}**")
            with col2:
                st.write(f"💵 {service['price']}")
            with col3:
                st.write(f"🕒 {service['wait']}")
    
    with tab4:
        st.subheader("Белорусская железная дорога")
        for train in get_belarusian_railway():
            col1, col2, col3, col4 = st.columns([1, 2, 2, 2])
            with col1:
                st.write(f"**{train['number']}**")
            with col2:
                st.write(f"📍 {train['from']}")
            with col3:
                st.write(f"➡️ {train['to']}")
            with col4:
                st.write(f"🕒 {train['time']}")
# ... (весь предыдущий код до страницы Диска остается без изменений) ...

# ================= СТРАНИЦА ТРАНСПОРТА =================
elif st.session_state.page == "Транспорт":
    st.markdown('<div class="gold-title">🚌 ТРАНСПОРТ</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["🚇 Метро", "🚌 Автобусы/Трамваи", "🚕 Такси", "🚂 Железная дорога"])
    
    with tab1:
        st.subheader("Минское метро")
        for station in get_minsk_metro():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{station['name']}**")
            with col2:
                st.write(f"Линия {station['line']}")
            with col3:
                st.success(f"🚇 {station['next']}")
    
    with tab2:
        st.subheader("Автобусы и трамваи")
        for route in get_bus_trams():
            col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
            with col1:
                st.write(f"**{route['number']}**")
            with col2:
                st.write(f"{route['type']}")
            with col3:
                st.write(f"{route['from']} → {route['to']}")
            with col4:
                st.info(f"⏱️ {route['next']}")
    
    with tab3:
        st.subheader("Сравнение цен такси")
        for service in get_taxi_prices():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{service['name']}**")
            with col2:
                st.write(f"💵 {service['price']}")
            with col3:
                st.write(f"🕒 {service['wait']}")
    
    with tab4:
        st.subheader("Белорусская железная дорога")
        for train in get_belarusian_railway():
            col1, col2, col3, col4 = st.columns([1, 2, 2, 2])
            with col1:
                st.write(f"**{train['number']}**")
            with col2:
                st.write(f"📍 {train['from']}")
            with col3:
                st.write(f"➡️ {train['to']}")
            with col4:
                st.write(f"🕒 {train['time']}")

# ================= СТРАНИЦА ДИСКА =================
elif st.session_state.page == "Диск":
    st.markdown('<div class="gold-title">💾 ZORNET DISK</div>', unsafe_allow_html=True)
    
    ROOT_DIR = Path("zornet_files")
    ROOT_DIR.mkdir(exist_ok=True)
    
    if "current_dir" not in st.session_state:
        st.session_state.current_dir = ROOT_DIR
    
    current_dir = st.session_state.current_dir
    
    # Загрузка файлов
    st.subheader("Загрузить файлы")
    uploaded_files = st.file_uploader("Выберите файлы", type=None, accept_multiple_files=True)
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_path = current_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            save_file_to_db(uploaded_file.name, uploaded_file.size)
        st.success(f"✅ Загружено {len(uploaded_files)} файлов")
        st.rerun()
    
    # Список файлов
    st.subheader(f"Содержимое папки")
    items = list(current_dir.iterdir())
    if items:
        for item in sorted(items, key=lambda x: (x.is_file(), x.name.lower())):
            col1, col2, col3 = st.columns([4, 2, 1])
            with col1:
                icon = get_icon(item)  # Используем функцию из начала файла
                st.write(f"{icon} {item.name}")
            with col2:
                st.write(f"Размер: {item.stat().st_size / 1024:.2f} KB")
            with col3:
                st.download_button("Скачать", data=open(item, "rb").read(), file_name=item.name)
    else:
        st.info("Папка пуста.")

# ================= СТРАНИЦА ПРОФИЛЯ =================
elif st.session_state.page == "Профиль":
    st.markdown('<div class="gold-title">👤 ПРОФИЛЬ</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.image("https://via.placeholder.com/150", width=150)
        st.markdown("### Пользователь ZORNET")
    
    with col2:
        st.markdown("### 📊 Статистика")
        st.metric("Всего пользователей", get_user_count())
        st.metric("Активных сессий", "1")
        st.metric("Использовано памяти", "2.5 GB")
        
        st.markdown("### ⚙️ Настройки")
        st.checkbox("Уведомления", value=True)
        st.checkbox("Темная тема", value=False)
        st.checkbox("Авто-обновление", value=True)

# ================= ИНИЦИАЛИЗАЦИЯ =================
if __name__ == "__main__":
    init_db()
    init_disk_db()
