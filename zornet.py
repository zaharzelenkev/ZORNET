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
    initial_sidebar_state="collapsed"  # Изменили на collapsed, чтобы сайдбар был скрыт по умолчанию
)

# ================= СЕССИЯ =================
if "page" not in st.session_state:
    st.session_state.page = "Главная"
if "sidebar_visible" not in st.session_state:
    st.session_state.sidebar_visible = False  # Добавили состояние видимости сайдбара
if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = []
if "weather_data" not in st.session_state:
    st.session_state.weather_data = None
if "user_city" not in st.session_state:
    st.session_state.user_city = None
if "city_query" in st.query_params:
    st.session_state.user_city = st.query_params["city_query"]
    st.session_state.page = "Погода"

# ================= CSS СТИЛИ =================
st.markdown("""
<style>
    /* ОБЩИЙ СТИЛЬ */
    .stApp { background-color: #ffffff; }

    /* СКРЫВАЕМ ЛИШНЕЕ */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* КНОПКА МЕНЮ (три полоски справа сверху) */
    .menu-button-container {
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 1000000;
    }
    
    .menu-button {
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
        color: white;
        border: none;
        border-radius: 8px;
        width: 50px;
        height: 50px;
        font-size: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(218, 165, 32, 0.4);
        transition: all 0.3s ease;
    }
    
    .menu-button:hover {
        transform: scale(1.05);
        box-shadow: 0 6px 16px rgba(218, 165, 32, 0.6);
    }
    
    /* Стиль для трех полосок */
    .hamburger-icon {
        display: flex;
        flex-direction: column;
        gap: 4px;
        width: 24px;
    }
    
    .hamburger-icon span {
        display: block;
        height: 3px;
        background: white;
        border-radius: 2px;
        transition: all 0.3s ease;
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

# ================= КНОПКА МЕНЮ (три полоски) =================
# Создаем кнопку меню через JavaScript, чтобы она была всегда видна
components.html("""
<script>
// Функция для создания кнопки меню
function createMenuButton() {
    // Создаем контейнер для кнопки
    const menuContainer = document.createElement('div');
    menuContainer.className = 'menu-button-container';
    menuContainer.innerHTML = `
        <button class="menu-button" id="menuToggleBtn">
            <div class="hamburger-icon">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </button>
    `;
    
    // Добавляем контейнер в тело документа
    document.body.appendChild(menuContainer);
    
    // Получаем кнопку сайдбара Streamlit
    const sidebarToggleBtn = document.querySelector('[data-testid="stSidebarCollapseButton"] button');
    
    // Назначаем обработчик клика на нашу кнопку
    document.getElementById('menuToggleBtn').addEventListener('click', function() {
        if (sidebarToggleBtn) {
            sidebarToggleBtn.click();
            
            // Анимация для кнопки меню
            this.classList.toggle('active');
            const spans = this.querySelectorAll('.hamburger-icon span');
            if (this.classList.contains('active')) {
                spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
                spans[1].style.opacity = '0';
                spans[2].style.transform = 'rotate(-45deg) translate(7px, -6px)';
            } else {
                spans[0].style.transform = 'none';
                spans[1].style.opacity = '1';
                spans[2].style.transform = 'none';
            }
        }
    });
    
    // Делаем стандартную кнопку Streamlit невидимой
    if (sidebarToggleBtn) {
        sidebarToggleBtn.parentElement.style.display = 'none';
    }
}

// Создаем кнопку при загрузке страницы
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createMenuButton);
} else {
    createMenuButton();
}
</script>
""", height=0)

# ================= САЙДБАР =================
# Управляем видимостью сайдбара через session state
if st.session_state.sidebar_visible:
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
                st.session_state.sidebar_visible = False
                st.rerun()
        
        # Кнопка закрытия меню
        st.markdown("---")
        if st.button("✕ Закрыть меню", use_container_width=True):
            st.session_state.sidebar_visible = False
            st.rerun()

# ================= ФУНКЦИИ ПОГОДЫ =================
def get_weather_icon(condition_code):
    icons = {"01d": "☀️", "01n": "🌙", "02d": "⛅", "02n": "⛅", "03d": "☁️", "03n": "☁️", "04d": "☁️", "04n": "☁️", "09d": "🌧️", "09n": "🌧️", "10d": "🌦️", "10n": "🌦️", "11d": "⛈️", "11n": "⛈️", "13d": "❄️", "13n": "❄️", "50d": "🌫️", "50n": "🌫️"}
    return icons.get(condition_code, "🌡️")

def get_weather_by_city(city_name):
    API_KEY = "20ebdd8243b8a3a29abe332fefdadb44"
    try:
        
        # Геокодинг
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={API_KEY}"
        geo_res = requests.get(geo_url, timeout=10).json()
        if not geo_res: return None
        
        lat, lon = geo_res[0]["lat"], geo_res[0]["lon"]
        
        # Текущая погода
        curr_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=ru"
        curr_data = requests.get(curr_url, timeout=10).json()
        
        # Прогноз
        fore_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=ru"
        fore_data = requests.get(fore_url, timeout=10).json()
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={API_KEY}&units=metric&lang=ru"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {
                "current": {
                    "temp": round(data["main"]["temp"]),
                    "description": data["weather"][0]["description"].capitalize(),
                    "icon": data["weather"][0]["icon"],
                    "city": data["name"],
                    "country": data["sys"]["country"],
                    "humidity": data["main"]["humidity"],
                    "wind_speed": data["wind"]["speed"]
                }
            }
        return None
    except: return None

# ================= КОМПОНЕНТ ПОИСКА (ЗОЛОТОЙ) =================
def golden_search_bar(placeholder="Поиск...", target_param="q", is_google=True):
    # Если это для погоды, форма будет отправлять параметр в URL самого приложения
    action_url = "https://www.google.com/search" if is_google else ""
    target_attr = 'target="_top"' if is_google else ""
    
    components.html(f"""
    <style>
        .search-container {{ text-align: center; font-family: sans-serif; }}
        input[type="text"] {{
            width: 100%; max-width: 600px; padding: 15px 25px;
            font-size: 18px; border: 2px solid #e0e0e0; border-radius: 30px;
            outline: none; box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        }}
        input[type="text"]:focus {{ border-color: #DAA520; }}
        button {{
            margin-top: 15px; background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
            color: white; border: none; padding: 12px 40px; border-radius: 25px;
            font-weight: bold; cursor: pointer; box-shadow: 0 4px 15px rgba(218, 165, 32, 0.4);
        }}
    </style>
    <div class="search-container">
        <form action="{action_url}" method="get" {target_attr}>
            <input type="text" name="{target_param}" placeholder="{placeholder}" required autocomplete="off">
            <br>
            <button type="submit">Найти</button>
        </form>
    </div>
    """, height=150)

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
        if st.button("📰 Новости", use_container_width=True):
            st.session_state.page = "Новости"
            st.rerun()
    with col4:
        if st.button("🤖 ZORNET AI", use_container_width=True):
            st.session_state.page = "ZORNET AI"
            st.rerun()

    st.markdown("---")

    # --- ИНТЕГРАЦИЯ GOOGLE ПОИСКА (ЧЕРЕЗ IFRAME) ---
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
        
        /* Контейнер формы */
        .search-container {
            width: 100%;
            max-width: 600px;
            padding: 10px;
            box-sizing: border-box;
            text-align: center;
        }

        /* Поле ввода */
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

        /* Кнопка */
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
                <input type="text" name="q" placeholder="🔍 Введите запрос" required autocomplete="off">
                <br>
                <button type="submit">Поиск</button>
            </form>
        </div>

    </body>
    </html>
    """, height=220)

    # ДОПОЛНИТЕЛЬНЫЕ КНОПКИ ПОД ПОИСКОМ
    st.markdown("---")
    
    # Панель "Найдется всё" с курсами валют
    col_currency1, col_currency2, col_currency3 = st.columns(3)
    with col_currency1:
        st.markdown("""
        <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; text-align: center;">
            <div style="color: #666; font-size: 14px;">USD</div>
            <div style="color: #DAA520; font-size: 24px; font-weight: bold;">2.84</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_currency2:
        st.markdown("""
        <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; text-align: center;">
            <div style="color: #666; font-size: 14px;">EUR</div>
            <div style="color: #DAA520; font-size: 24px; font-weight: bold;">3.34</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_currency3:
        st.markdown("""
        <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; text-align: center;">
            <div style="color: #666; font-size: 14px;">RUB</div>
            <div style="color: #DAA520; font-size: 24px; font-weight: bold;">3.21</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<h3 style='text-align: center; color: #DAA520; margin: 30px 0 20px 0;'>НАЙДЁТСЯ ВСЁ</h3>", unsafe_allow_html=True)
    
    # Промокод
    st.markdown("""
    <div style="background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%); 
                border-radius: 10px; padding: 15px; text-align: center; color: white; margin: 20px 0;">
        <div style="font-size: 16px; font-weight: bold;">🎁 Промокод 300 рублей на первую рекламу в Яндекс Директе</div>
        <div style="font-size: 20px; font-weight: 800; margin-top: 5px;">zornet.by</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Сервисы (сетка 4x4)
    st.markdown("<h3 style='margin: 30px 0 20px 0;'>Найти сервис</h3>", unsafe_allow_html=True)
    
    # Первый ряд
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🎮\nИгры", use_container_width=True):
            st.info("Игры скоро будут доступны!")
    with col2:
        if st.button("🗺️\nКарты", use_container_width=True):
            st.info("Карты скоро будут доступны!")
    with col3:
        if st.button("🎬\nКинопоиск", use_container_width=True):
            st.info("Кинопоиск скоро будет доступен!")
    with col4:
        if st.button("🌐\nПереводчик", use_container_width=True):
            st.info("Переводчик скоро будет доступен!")
    
    # Второй ряд
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        if st.button("✍️\nАвтору", use_container_width=True):
            st.info("Сервис 'Автору' скоро будет доступен!")
    with col6:
        if st.button("✈️\nПутешествия", use_container_width=True):
            st.info("Путешествия скоро будут доступны!")
    with col7:
        if st.button("🎥\nВидео", use_container_width=True):
            st.info("Видео скоро будет доступно!")
    with col8:
        if st.button("🖼️\nКартинки", use_container_width=True):
            st.info("Картинки скоро будут доступны!")
    
    # Третий ряд
    col9, col10, col11, col12 = st.columns(4)
    with col9:
        if st.button("🎵\nМузыка", use_container_width=True):
            st.info("Музыка скоро будет доступна!")
    with col10:
        if st.button("📺\nТелепрограмма", use_container_width=True):
            st.info("Телепрограмма скоро будет доступна!")
    with col11:
        if st.button("🏠\nНедвижимость", use_container_width=True):
            st.info("Недвижимость скоро будет доступна!")
    with col12:
        if st.button("🎪\nZORNET Афиша", use_container_width=True):
            st.info("ZORNET Афиша скоро будет доступна!")
    
    # Четвертый ряд
    col13, col14, col15, col16 = st.columns(4)
    with col13:
        if st.button("💻\nПрактикум", use_container_width=True):
            st.info("Практикум скоро будет доступен!")
    with col14:
        if st.button("🔋\nБери заряд", use_container_width=True):
            st.info("Сервис 'Бери заряд' скоро будет доступен!")
    with col15:
        if st.button("📢\nДирект", use_container_width=True):
            st.info("Директ скоро будет доступен!")
    with col16:
        if st.button("💾\nДиск", use_container_width=True):
            st.session_state.page = "Диск"
            st.rerun()
    
    # Кнопка "Показать все"
    if st.button("📋 Показать все сервисы", use_container_width=True):
        st.info("Все сервисы будут показаны в расширенном меню")
    
    st.markdown("---")
    
    # Приложения
    st.markdown("<h3 style='margin: 20px 0 15px 0;'>Приложения</h3>", unsafe_allow_html=True)
    
    app_col1, app_col2, app_col3, app_col4 = st.columns(4)
    with app_col1:
        st.markdown("""
        <div style="text-align: center; padding: 15px;">
            <div style="font-size: 32px; margin-bottom: 10px;">📱</div>
            <div style="font-weight: 500;">ZORNET Браузер</div>
        </div>
        """, unsafe_allow_html=True)
    
    with app_col2:
        st.markdown("""
        <div style="text-align: center; padding: 15px;">
            <div style="font-size: 32px; margin-bottom: 10px;">📧</div>
            <div style="font-weight: 500;">ZORNET Почта</div>
        </div>
        """, unsafe_allow_html=True)
    
    with app_col3:
        st.markdown("""
        <div style="text-align: center; padding: 15px;">
            <div style="font-size: 32px; margin-bottom: 10px;">🗺️</div>
            <div style="font-weight: 500;">ZORNET Карты</div>
        </div>
        """, unsafe_allow_html=True)
    
    with app_col4:
        st.markdown("""
        <div style="text-align: center; padding: 15px;">
            <div style="font-size: 32px; margin-bottom: 10px;">🎵</div>
            <div style="font-weight: 500;">ZORNET Музыка</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Кнопка "Все сервисы"
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        if st.button("🌐 Все сервисы", type="primary", use_container_width=True):
            st.info("Все сервисы ZORNET будут доступны в полном меню")

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

# ================= ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ (чтобы не было NameError) =================
def get_wind_direction(degrees):
    try:
        directions = ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"]
        index = round(float(degrees) / 45) % 8
        return directions[index]
    except:
        return "Н/Д"

# ================= СТРАНИЦА ПОГОДЫ =================
if st.session_state.page == "Погода":
    st.markdown('<div class="gold-title">🌤️ ПОГОДА</div>', unsafe_allow_html=True)

    # --- ЗОЛОТОЙ ПОИСК (ДИЗАЙН КАК НА ГЛАВНОЙ) ---
    components.html("""
    <div style="text-align: center; font-family: 'Helvetica Neue', sans-serif;">
        <form action="/" method="get" target="_top">
            <input type="text" name="city_query" placeholder="🔍 Введите город (напр. Гродно, Москва)" 
                style="width: 100%; max-width: 600px; padding: 18px 25px; font-size: 18px; 
                border: 2px solid #e0e0e0; border-radius: 30px; outline: none; 
                box-shadow: 0 4px 10px rgba(0,0,0,0.05); -webkit-appearance: none;" required>
            <br>
            <button type="submit" style="margin-top: 20px; background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
                color: white; border: none; padding: 14px 40px; border-radius: 25px; font-size: 16px; 
                font-weight: 700; cursor: pointer; box-shadow: 0 4px 15px rgba(218, 165, 32, 0.4);
                text-transform: uppercase; letter-spacing: 1px; width: 100%; max-width: 250px;">
                Найти
            </button>
        </form>
    </div>
    """, height=180)

    # Определяем город для показа
    city_to_show = st.session_state.get('user_city', 'Минск')

    with st.spinner(f"Получение данных для {city_to_show}..."):
        weather_data = get_weather_by_city(city_to_show)

        if weather_data:
            current = weather_data["current"]
            
            # Используем .get() для защиты от KeyError
            temp = current.get('temp', '--')
            feels = current.get('feels_like', '--')
            desc = current.get('description', 'Данные отсутствуют')
            hum = current.get('humidity', '--')
            wind = current.get('wind_speed', '--')
            press = current.get('pressure', '--')
            vis = current.get('visibility', '--')

            st.markdown(f"### 🌤️ Погода в {current.get('city', city_to_show)}, {current.get('country', '')}")

            # Главный блок
            col_t, col_i = st.columns([2, 1])
            with col_t:
                st.markdown(f"""
                <div style="background: white; padding: 25px; border-radius: 20px; border-left: 8px solid #DAA520; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                    <div style="font-size: 4.5rem; font-weight: 800; color: #1a1a1a;">{temp}°C</div>
                    <div style="font-size: 1.5rem; color: #666; margin-top: 5px;">
                        {get_weather_icon(current.get('icon', ''))} {desc}
                    </div>
                    <div style="font-size: 1rem; color: #999; margin-top: 10px;">
                        💁 Ощущается как <b>{feels}°C</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_i:
                st.markdown(f"""
                <div style="text-align: center; font-size: 6rem;">
                    {get_weather_icon(current.get('icon', ''))}
                </div>
                """, unsafe_allow_html=True)

            st.markdown("#### 📊 Детали")
            
            # Сетка деталей
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("💧 Влажность", f"{hum}%")
            d2.metric("💨 Ветер", f"{wind} м/с")
            d3.metric("🧭 Направление", get_wind_direction(current.get('wind_deg', 0)))
            d4.metric("👁️ Видимость", f"{vis} км")

            # Прогноз (если есть в API)
            if weather_data.get("forecast"):
                st.markdown("#### 📅 Прогноз")
                forecast_list = weather_data["forecast"]["list"]
                # Показываем 5 следующих отметок времени (или дней)
                cols = st.columns(5)
                for idx, item in enumerate(forecast_list[:5]):
                    with cols[idx]:
                        time_label = item['dt_txt'].split(' ')[1][:5]
                        st.markdown(f"""
                        <div style="background: #f0f2f6; padding: 10px; border-radius: 10px; text-align: center;">
                            <div style="font-weight: bold;">{time_label}</div>
                            <div style="font-size: 1.5rem;">{get_weather_icon(item['weather'][0]['icon'])}</div>
                            <div>{round(item['main']['temp'])}°C</div>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.error(f"Не удалось найти город '{city_to_show}'. Проверьте правильность написания.")

    # Кнопки быстрых городов
    st.markdown("---")
    st.markdown("### 🇧🇾 Быстрый выбор")
    bc1, bc2, bc3, bc4 = st.columns(4)
    if bc1.button("Минск", use_container_width=True): st.session_state.user_city = "Минск"; st.rerun()
    if bc2.button("Гродно", use_container_width=True): st.session_state.user_city = "Гродно"; st.rerun()
    if bc3.button("Брест", use_container_width=True): st.session_state.user_city = "Брест"; st.rerun()
    if bc4.button("Гомель", use_container_width=True): st.session_state.user_city = "Гомель"; st.rerun()

# ================= СТРАНИЦА ПОГОДЫ =================
elif st.session_state.page == "Погода":
    st.markdown('<div class="gold-title">🌤️ ПОГОДА</div>', unsafe_allow_html=True)

    # Поиск внутри погоды
    with st.container():
        col_s1, col_s2 = st.columns([4, 1])
        with col_s1:
            city_in = st.text_input("Город", value=st.session_state.user_city, label_visibility="collapsed", placeholder="Введите город...")
        with col_s2:
            if st.button("Поиск", type="primary", use_container_width=True):
                st.session_state.user_city = city_in
                st.rerun()

    data = get_weather_by_city(st.session_state.user_city)
    
    if data:
        curr = data["current"]
        st.markdown(f"### 📍 {curr['city']}, {curr['country']}")
        
        # Основной блок
        m1, m2 = st.columns([2, 1])
        with m1:
            st.markdown(f"""
            <div class="weather-card">
                <div style="font-size: 4.5rem; font-weight: 800; color: #1a1a1a;">{curr['temp']}°C</div>
                <div style="font-size: 1.6rem; color: #DAA520; font-weight: 600;">{get_weather_icon(curr['icon'])} {curr['description']}</div>
                <div style="color: #666; margin-top: 10px;">Ощущается как <b>{curr['feels_like']}°C</b></div>
            </div>
            """, unsafe_allow_html=True)
        
        with m2:
            st.markdown(f"""
            <div style="background: #f8f9fa; padding: 20px; border-radius: 20px; height: 100%;">
                <p>💧 Влажность: <b>{curr['humidity']}%</b></p>
                <p>💨 Ветер: <b>{curr['wind_speed']} м/с</b></p>
                <p>🧭 Направление: <b>{get_wind_direction(curr['wind_deg'])}</b></p>
                <p>👁️ Видимость: <b>{curr['visibility']} км</b></p>
            </div>
            """, unsafe_allow_html=True)

        # Прогноз на 5 дней (Восстановлено!)
        if data.get("forecast"):
            st.markdown("#### 📅 Прогноз на ближайшие дни")
            f_cols = st.columns(5)
            # Фильтруем прогноз, чтобы брать данные на 12:00 каждого дня
            forecast_items = [item for item in data["forecast"]["list"] if "12:00:00" in item["dt_txt"]][:5]
            
            for idx, item in enumerate(forecast_items):
                with f_cols[idx]:
                    day_name = datetime.datetime.strptime(item["dt_txt"], "%Y-%m-%d %H:%M:%S").strftime("%a")
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%); 
                        padding: 15px; border-radius: 15px; text-align: center; color: white;">
                        <div style="font-weight: bold;">{day_name}</div>
                        <div style="font-size: 2rem;">{get_weather_icon(item['weather'][0]['icon'])}</div>
                        <div style="font-size: 1.2rem; font-weight: bold;">{round(item['main']['temp'])}°C</div>
                    </div>
                    """, unsafe_allow_html=True)

        # Города Беларуси (Восстановлено!)
        st.markdown("---")
        st.markdown("### 🇧🇾 Быстрый выбор")
        bel_cities = ["Минск", "Гродно", "Брест", "Гомель", "Витебск", "Могилев", "Солигорск", "Лида"]
        b_cols = st.columns(4)
        for i, city in enumerate(bel_cities):
            if b_cols[i % 4].button(city, use_container_width=True):
                st.session_state.user_city = city
                st.rerun()
    else:
        st.error("Город не найден. Попробуйте еще раз.")

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
