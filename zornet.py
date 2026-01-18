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
if "location_permission" not in st.session_state:
    st.session_state.location_permission = False

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
        ("🌤️", "ПОГОДА", "Погода"),  # Добавлена вкладка погоды
        ("💾", "ДИСК", "Диск"),
        ("🚌", "ТРАНСПОРТ", "Транспорт"),
        ("👤", "ПРОФИЛЬ", "Профиль"),
    ]
    
    # Используем уникальные ключи с индексом
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
    API_KEY = "20ebdd8243b8a3a29abe332fefdadb44"  # Демо-ключ, замени на свой!
    
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
            st.error(f"API ошибка: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Ошибка получения погоды: {e}")
        return None

def get_weather_by_city(city_name):
    """Получает погоду по названию города"""
    API_KEY = "f2b2b0b5b5b5b5b5b5b5b5b5b5b5b5b5"
    
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

# HTML/JS для запроса геолокации
geolocation_html = """
<script>
function getLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            // Успех
            function(position) {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                // Отправляем координаты в Streamlit
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: lat + ',' + lon
                }, '*');
                
                document.getElementById('location-status').innerHTML = 
                    '<span style="color: green;">✓ Местоположение получено!</span>';
            },
            // Ошибка
            function(error) {
                let errorMessage = "❌ Ошибка получения местоположения: ";
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        errorMessage += "Пользователь отказал в доступе";
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMessage += "Информация о местоположении недоступна";
                        break;
                    case error.TIMEOUT:
                        errorMessage += "Время запроса истекло";
                        break;
                    default:
                        errorMessage += "Неизвестная ошибка";
                        break;
                }
                document.getElementById('location-status').innerHTML = 
                    '<span style="color: red;">' + errorMessage + '</span>';
            },
            // Опции
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }
        );
    } else {
        document.getElementById('location-status').innerHTML = 
            '<span style="color: red;">❌ Ваш браузер не поддерживает геолокацию</span>';
    }
}

// Запускаем при загрузке если пользователь уже дал разрешение
window.onload = function() {
    if (localStorage.getItem('location-permission') === 'granted') {
        getLocation();
    }
};
</script>

<div style="text-align: center; padding: 20px;">
    <button onclick="getLocation()" style="
        padding: 12px 24px;
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 16px;
        font-weight: bold;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(218, 165, 32, 0.3);
    ">
        📍 Получить мое местоположение
    </button>
    
    <div id="location-status" style="margin-top: 15px; font-size: 14px;">
        Нажмите кнопку выше для получения местоположения
    </div>
    
    <div style="margin-top: 20px; font-size: 12px; color: #666;">
        Мы используем ваш IP и данные браузера для определения приблизительного местоположения
    </div>
</div>
"""

# Альтернатива: получение приблизительного местоположения по IP
def get_location_by_ip():
    """Получает приблизительное местоположение по IP адресу"""
    try:
        response = requests.get('https://ipapi.co/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "lat": data.get("latitude"),
                "lon": data.get("longitude"),
                "city": data.get("city"),
                "country": data.get("country_name"),
                "ip": data.get("ip")
            }
    except:
        pass
    
    # Fallback на публичные геолокационные сервисы
    try:
        response = requests.get('http://ip-api.com/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return {
                    "lat": data.get("lat"),
                    "lon": data.get("lon"),
                    "city": data.get("city"),
                    "country": data.get("country"),
                    "ip": data.get("query")
                }
    except:
        pass
    
    return None

# ================= НАСТРОЙКИ =================
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
    """Поиск в интернете - с запасными результатами"""
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
        st.error(f"Ошибка DuckDuckGo: {e}")
    
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
    
    relevant_results = []
    for res in fallback_results:
        if query.lower() in res["title"].lower() or query.lower() in res["snippet"].lower():
            relevant_results.append(res)
    
    if not relevant_results:
        relevant_results = fallback_results[:3]
    
    return relevant_results

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
        if st.button("⛅ -5°C\nМинск", use_container_width=True):
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
        key=f"main_search_{st.session_state.page}",
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
    
    with st.sidebar:
        st.markdown("### 💡 Примеры вопросов")
        
        examples = [
            "Напиши план развития для IT-стартапа",
            "Объясни квантовую физику просто",
            "Помоги написать деловое письмо",
            "Какие технологии AI самые перспективные?",
        ]
        
        for example in examples:
            if st.button(example, key=f"ex_{example[:10]}", use_container_width=True):
                st.session_state.ai_messages.append({"role": "user", "content": example})
                st.rerun()
        
        if st.button("🧹 Очистить историю", use_container_width=True):
            st.session_state.ai_messages = [
                {"role": "assistant", "content": "Привет! Я ZORNET AI. Чем могу помочь?"}
            ]
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
    
    # Инициализация сессионных переменных
    if "location_coords" not in st.session_state:
        st.session_state.location_coords = None
    if "location_city" not in st.session_state:
        st.session_state.location_city = None
    
    # Вкладки
    tab1, tab2 = st.tabs(["📍 По местоположению", "🏙️ По городу"])
    
    with tab1:
        st.subheader("Погода по вашему местоположению")
        
        # Кнопка для системного запроса геолокации
        st.markdown("""
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h4 style="color: #1a1a1a; margin-bottom: 15px;">📍 Системный запрос местоположения</h4>
            <p style="color: #666; margin-bottom: 15px;">
                Нажмите кнопку ниже, чтобы ваш браузер запросил разрешение на доступ к вашему точному местоположению.
                Это самый точный способ определить ваше местоположение.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Отображаем HTML/JS виджет
        st.components.v1.html(geolocation_html, height=200)
        
        # Кнопка для получения местоположения по IP (менее точное, но не требует разрешения)
        st.markdown("---")
        st.markdown("### 🌐 Альтернативный способ")
        st.markdown("""
        <div style="background: #f0f7ff; padding: 15px; border-radius: 10px; margin-bottom: 15px;">
            <p style="color: #1a73e8; margin: 0;">
                Если вы не хотите делиться точным местоположением, мы можем определить ваш город по IP адресу.
                Этот метод менее точен, но не требует разрешений.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🌐 Определить по IP", key="ip_location"):
                with st.spinner("Определяю местоположение по IP..."):
                    location_data = get_location_by_ip()
                    
                    if location_data and location_data["lat"] and location_data["lon"]:
                        st.session_state.location_coords = (location_data["lat"], location_data["lon"])
                        st.session_state.location_city = location_data["city"]
                        
                        st.success(f"📍 Определено: {location_data['city']}, {location_data['country']}")
                        
                        # Автоматически получаем погоду
                        weather_data = get_weather_by_coords(
                            location_data["lat"], 
                            location_data["lon"]
                        )
                        st.session_state.weather_data = weather_data
                    else:
                        st.error("Не удалось определить местоположение по IP")
        
        with col2:
            if st.session_state.location_city:
                st.info(f"Текущее местоположение: **{st.session_state.location_city}**")
        
        # Поле для ручного ввода координат (для разработчиков)
        with st.expander("🔧 Для разработчиков: ввести координаты вручную"):
            col_lat, col_lon = st.columns(2)
            with col_lat:
                manual_lat = st.number_input("Широта", value=53.9, format="%.4f")
            with col_lon:
                manual_lon = st.number_input("Долгота", value=27.5667, format="%.4f")
            
            if st.button("Получить погоду по координатам", key="manual_coords"):
                st.session_state.location_coords = (manual_lat, manual_lon)
                st.session_state.location_city = "Ручные координаты"
        
        # Получаем и отображаем погоду если есть координаты
        if st.session_state.location_coords:
            lat, lon = st.session_state.location_coords
            
            with st.spinner(f"Получаю погоду для {st.session_state.location_city or 'вашего местоположения'}..."):
                weather_data = get_weather_by_coords(lat, lon)
                
                if weather_data:
                    current = weather_data["current"]
                    
                    # Отображение погоды в красивом виджете
                    st.markdown(f"""
                    <div class="weather-widget">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-size: 0.9rem; color: rgba(255,255,255,0.8); margin-bottom: 5px;">
                                    📍 {current['city']}, {current['country']}
                                </div>
                                <div class="weather-temp">{current['temp']}°C</div>
                                <div class="weather-description">
                                    {get_weather_icon(current['icon'])} {current['description']}
                                </div>
                                <div style="font-size: 1rem; opacity: 0.9; margin-top: 5px;">
                                    Ощущается как {current['feels_like']}°C
                                </div>
                            </div>
                            <div style="font-size: 5rem; margin-right: 20px;">
                                {get_weather_icon(current['icon'])}
                            </div>
                        </div>
                        
                        <div class="weather-details">
                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                                <div>
                                    <div style="display: flex; align-items: center; gap: 10px;">
                                        <span style="font-size: 1.5rem;">💧</span>
                                        <div>
                                            <div style="font-size: 0.9rem; opacity: 0.8;">Влажность</div>
                                            <div style="font-size: 1.3rem; font-weight: bold;">{current['humidity']}%</div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div>
                                    <div style="display: flex; align-items: center; gap: 10px;">
                                        <span style="font-size: 1.5rem;">💨</span>
                                        <div>
                                            <div style="font-size: 0.9rem; opacity: 0.8;">Ветер</div>
                                            <div style="font-size: 1.3rem; font-weight: bold;">
                                                {current['wind_speed']} м/с
                                            </div>
                                            <div style="font-size: 0.9rem;">
                                                {get_wind_direction(current['wind_deg'])}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div>
                                    <div style="display: flex; align-items: center; gap: 10px;">
                                        <span style="font-size: 1.5rem;">📊</span>
                                        <div>
                                            <div style="font-size: 0.9rem; opacity: 0.8;">Давление</div>
                                            <div style="font-size: 1.3rem; font-weight: bold;">{current['pressure']} гПа</div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div>
                                    <div style="display: flex; align-items: center; gap: 10px;">
                                        <span style="font-size: 1.5rem;">👁️</span>
                                        <div>
                                            <div style="font-size: 0.9rem; opacity: 0.8;">Видимость</div>
                                            <div style="font-size: 1.3rem; font-weight: bold;">{current['visibility']} км</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div style="margin-top: 20px; display: flex; justify-content: space-around; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 10px;">
                            <div style="text-align: center;">
                                <div style="font-size: 1.2rem;">🌅</div>
                                <div style="font-size: 0.9rem; opacity: 0.8;">Восход</div>
                                <div style="font-size: 1.2rem; font-weight: bold;">{current['sunrise']}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 1.2rem;">🌇</div>
                                <div style="font-size: 0.9rem; opacity: 0.8;">Закат</div>
                                <div style="font-size: 1.2rem; font-weight: bold;">{current['sunset']}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 1.2rem;">☁️</div>
                                <div style="font-size: 0.9rem; opacity: 0.8;">Облачность</div>
                                <div style="font-size: 1.2rem; font-weight: bold;">{current['clouds']}%</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Прогноз на 5 дней
                    if weather_data.get("forecast"):
                        st.subheader("📅 Прогноз на 5 дней")
                        
                        forecast_items = weather_data["forecast"]["list"]
                        daily_forecast = {}
                        
                        for item in forecast_items:
                            date = item["dt_txt"].split(" ")[0]
                            if date not in daily_forecast:
                                daily_forecast[date] = item
                        
                        cols = st.columns(5)
                        dates = list(daily_forecast.keys())[:5]
                        
                        for idx, date in enumerate(dates):
                            with cols[idx]:
                                day_data = daily_forecast[date]
                                day_name = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%a")
                                
                                st.markdown(f"""
                                <div class="forecast-day">
                                    <div style="font-weight: bold; margin-bottom: 10px; color: #1a1a1a;">{day_name}</div>
                                    <div style="font-size: 2.5rem; margin: 10px 0; text-align: center;">
                                        {get_weather_icon(day_data['weather'][0]['icon'])}
                                    </div>
                                    <div style="font-size: 1.5rem; font-weight: bold; text-align: center; color: #1a1a1a;">
                                        {round(day_data['main']['temp'])}°C
                                    </div>
                                    <div style="font-size: 0.9rem; margin-top: 5px; text-align: center; color: #666;">
                                        {day_data['weather'][0]['description'].capitalize()}
                                    </div>
                                    <div style="font-size: 0.8rem; margin-top: 5px; text-align: center; color: #888;">
                                        💧 {day_data['main']['humidity']}% | 💨 {day_data['wind']['speed']} м/с
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                else:
                    st.error("Не удалось получить данные о погоде. Попробуйте позже или используйте поиск по городу.")
    
    with tab2:
        st.subheader("Поиск погоды по городу")
        
        col_search, col_btn = st.columns([3, 1])
        with col_search:
            city_input = st.text_input("Введите название города", 
                                     placeholder="Например: Минск, Москва, Лондон...",
                                     key="city_search")
        
        with col_btn:
            search_clicked = st.button("🔍 Найти", type="primary", use_container_width=True)
        
        if search_clicked and city_input:
            with st.spinner(f"Ищу погоду для {city_input}..."):
                weather_data = get_weather_by_city(city_input)
                
                if weather_data:
                    current = weather_data["current"]
                    
                    st.markdown(f"""
                    <div class="weather-widget">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-size: 0.9rem; color: rgba(255,255,255,0.8); margin-bottom: 5px;">
                                    📍 {current['city']}, {current['country']}
                                </div>
                                <div class="weather-temp">{current['temp']}°C</div>
                                <div class="weather-description">
                                    {get_weather_icon(current['icon'])} {current['description']}
                                </div>
                            </div>
                            <div style="font-size: 5rem; margin-right: 20px;">
                                {get_weather_icon(current['icon'])}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Сохраняем для быстрого доступа
                    st.session_state.weather_data = weather_data
                    
                    # Кнопка сохранить этот город
                    if st.button("⭐ Сохранить этот город"):
                        if "saved_cities" not in st.session_state:
                            st.session_state.saved_cities = []
                        if current['city'] not in st.session_state.saved_cities:
                            st.session_state.saved_cities.append(current['city'])
                            st.success(f"Город {current['city']} сохранен!")
        
        # Сохраненные города
        if "saved_cities" in st.session_state and st.session_state.saved_cities:
            st.subheader("⭐ Сохраненные города")
            cols = st.columns(len(st.session_state.saved_cities))
            for idx, city in enumerate(st.session_state.saved_cities[:5]):
                with cols[idx]:
                    if st.button(city, key=f"saved_{city}"):
                        weather_data = get_weather_by_city(city)
                        if weather_data:
                            st.session_state.weather_data = weather_data
                            st.rerun()

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
def get_icon(file_path):
    ext = file_path.suffix.lower()
    if file_path.is_dir(): return "📁"
    if ext in [".jpg", ".jpeg", ".png", ".gif"]: return "🖼️"
    if ext == ".pdf": return "📄"
    if ext in [".doc", ".docx"]: return "📝"
    if ext in [".mp3", ".wav"]: return "🎵"
    if ext in [".mp4", ".avi"]: return "🎬"
    return "📦"

def render_breadcrumb(path):
    parts = list(path.relative_to(ROOT_DIR).parts)
    breadcrumb_html = ["<a href='#' onclick='window.location.reload()'>Главная</a>"]
    p = ROOT_DIR
    for part in parts:
        p = p / part
        breadcrumb_html.append(f"<a href='#' onclick='window.location.reload()'>{part}</a>")
    st.markdown(" / ".join(breadcrumb_html), unsafe_allow_html=True)

if st.session_state.page == "Диск":
    st.markdown('<div class="gold-title">💾 ZORNET DISK</div>', unsafe_allow_html=True)
    
    ROOT_DIR = Path("zornet_files")
    ROOT_DIR.mkdir(exist_ok=True)
    
    if "current_dir" not in st.session_state:
        st.session_state.current_dir = ROOT_DIR
    
    current_dir = st.session_state.current_dir
    render_breadcrumb(current_dir)

    st.subheader("Загрузить файлы (Drag & Drop поддерживается)")
    uploaded_files = st.file_uploader("Выберите файлы", type=None, accept_multiple_files=True)
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_path = current_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            save_file_to_db(uploaded_file.name, uploaded_file.size)
        st.success(f"✅ Загружено {len(uploaded_files)} файлов")
        st.rerun()

    st.subheader(f"Содержимое папки: {current_dir.name}")
    items = list(current_dir.iterdir())
    if items:
        for item in sorted(items, key=lambda x: (x.is_file(), x.name.lower())):
            col1, col2, col3 = st.columns([4, 2, 1])
            with col1:
                icon = get_icon(item)
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
