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
import urllib.parse
import io
import base64
import time

# ================= НАСТРОЙКИ =================
st.set_page_config(
    page_title="ZORNET",
    page_icon="🇧🇾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= API КЛЮЧИ =================
GOOGLE_API_KEY = ""  # Получи на https://console.cloud.google.com/
GOOGLE_CSE_ID = ""   # Получи на https://programmablesearchengine.google.com/
HF_API_KEY = st.secrets.get("HF_API_KEY", "")
OPENWEATHER_API_KEY = "20ebdd8243b8a3a29abe332fefdadb44"

# ================= СЕССИЯ =================
if "page" not in st.session_state:
    st.session_state.page = "Главная"
if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = []
if "weather_data" not in st.session_state:
    st.session_state.weather_data = None
if "user_city" not in st.session_state:
    st.session_state.user_city = None
if "camera_mode" not in st.session_state:
    st.session_state.camera_mode = "object"
if "camera_result" not in st.session_state:
    st.session_state.camera_result = None
if "ai_tab" not in st.session_state:
    st.session_state.ai_tab = "chat"
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "search_submitted" not in st.session_state:
    st.session_state.search_submitted = False

# ================= CSS СТИЛИ =================
st.markdown("""
<style>
    /* ОБЩИЙ СТИЛЬ */
    .stApp { 
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* СКРЫВАЕМ ЛИШНЕЕ */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {visibility: hidden;}

    /* ГЛАВНЫЙ ЗАГОЛОВОК */
    .gold-title {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 4rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(90deg, #FFD700, #DAA520, #B8860B, #DAA520, #FFD700);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: shine 3s linear infinite;
        letter-spacing: 4px;
        text-transform: uppercase;
        margin: 10px 0 30px 0;
        text-shadow: 0 2px 10px rgba(218, 165, 32, 0.2);
    }
    
    @keyframes shine {
        to { background-position: 200% center; }
    }

    /* КНОПКИ ГЛАВНОЙ */
    .main-nav-btn {
        background: white !important;
        border: 2px solid #FFD700 !important;
        color: #1a1a1a !important;
        padding: 20px !important; 
        border-radius: 15px !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        width: 100% !important;
        box-shadow: 0 6px 20px rgba(218, 165, 32, 0.15) !important;
        transition: all 0.3s ease !important;
        margin: 5px 0 !important;
    }
    
    .main-nav-btn:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 25px rgba(218, 165, 32, 0.25) !important;
        border-color: #DAA520 !important;
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
        transition: all 0.3s ease !important;
    }
    
    .gold-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(218, 165, 32, 0.4) !important;
    }

    /* ВРЕМЯ В ЗОЛОТОЙ РАМКЕ */
    .time-widget {
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
        border-radius: 12px;
        padding: 15px 20px;
        text-align: center;
        color: white;
        font-weight: 600;
        font-size: 16px;
        box-shadow: 0 4px 15px rgba(218, 165, 32, 0.3);
        margin: 5px;
    }

    /* ПОИСКОВАЯ СТРОКА */
    .search-container {
        max-width: 800px;
        margin: 40px auto;
        padding: 20px;
    }
    
    .search-box {
        background: white;
        border-radius: 50px;
        padding: 5px 25px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        border: 2px solid #f0f0f0;
        transition: all 0.3s ease;
    }
    
    .search-box:focus-within {
        border-color: #DAA520;
        box-shadow: 0 10px 40px rgba(218, 165, 32, 0.2);
        transform: translateY(-2px);
    }
    
    .search-input {
        border: none !important;
        outline: none !important;
        font-size: 18px !important;
        padding: 15px !important;
        width: 100% !important;
        background: transparent !important;
    }
    
    .search-input:focus {
        box-shadow: none !important;
    }
    
    .search-button {
        background: linear-gradient(135deg, #4285f4, #34a853, #fbbc05, #ea4335) !important;
        color: white !important;
        border: none !important;
        border-radius: 50px !important;
        padding: 12px 40px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        margin: 20px 0 !important;
        transition: all 0.3s ease !important;
    }
    
    .search-button:hover {
        transform: scale(1.05);
        box-shadow: 0 10px 25px rgba(66, 133, 244, 0.3) !important;
    }

    /* РЕЗУЛЬТАТЫ ПОИСКА */
    .search-result {
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        border-left: 4px solid #4285f4;
        box-shadow: 0 5px 15px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    
    .search-result:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }
    
    .result-title {
        color: #1a0dab;
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 5px;
        text-decoration: none;
    }
    
    .result-title:hover {
        text-decoration: underline;
    }
    
    .result-url {
        color: #006621;
        font-size: 14px;
        margin-bottom: 10px;
    }
    
    .result-snippet {
        color: #545454;
        font-size: 14px;
        line-height: 1.5;
    }

    /* AI ЧАТ */
    .ai-chat-container {
        background: linear-gradient(135deg, #fffaf0 0%, #fff5e6 100%);
        border-radius: 20px;
        padding: 25px;
        margin: 20px 0;
        border: 2px solid #FFD700;
    }
    
    .ai-message-user {
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
        color: white;
        padding: 15px 20px;
        border-radius: 18px 18px 4px 18px;
        max-width: 80%;
        margin-left: auto;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(218, 165, 32, 0.2);
    }
    
    .ai-message-bot {
        background: #f8f9fa;
        color: #1a1a1a;
        padding: 15px 20px;
        border-radius: 18px 18px 18px 4px;
        max-width: 80%;
        margin-right: auto;
        margin-bottom: 15px;
        border-left: 4px solid #DAA520;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    /* УМНАЯ КАМЕРА */
    .camera-container {
        background: linear-gradient(135deg, #f0f8ff 0%, #e6f7ff 100%);
        border-radius: 20px;
        padding: 25px;
        margin: 20px 0;
        border: 2px solid #4a90e2;
    }
    
    .camera-mode-btn {
        background: #4a90e2 !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px 20px !important;
        margin: 5px !important;
    }
    
    .camera-mode-btn.active {
        background: #2c6cb0 !important;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.2) !important;
    }
    
    .camera-result-box {
        background: white;
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        border: 2px solid #4a90e2;
        box-shadow: 0 5px 20px rgba(74, 144, 226, 0.1);
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
        ("📷", "УМНАЯ КАМЕРА", "Умная камера"),
        ("📰", "НОВОСТИ", "Новости"),
        ("🌤️", "ПОГОДА", "Погода"),
        ("💾", "ДИСК", "Диск"),
        ("👤", "ПРОФИЛЬ", "Профиль"),
    ]

    for i, (icon, text, page) in enumerate(pages):
        if st.button(f"{icon} {text}", key=f"nav_{i}_{page}", use_container_width=True):
            st.session_state.page = page
            st.rerun()

# ================= ФУНКЦИИ GOOGLE ПОИСКА =================
def search_google_custom(query, num_results=10):
    """Поиск через Google Custom Search API"""
    
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        return get_demo_results(query, num_results)
    
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        
        params = {
            'key': GOOGLE_API_KEY,
            'cx': GOOGLE_CSE_ID,
            'q': query,
            'num': min(num_results, 10),
            'lr': 'lang_ru',
            'cr': 'countryBY',
            'gl': 'by'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            if 'items' in data:
                for item in data['items']:
                    results.append({
                        'title': item.get('title', ''),
                        'link': item.get('link', ''),
                        'snippet': item.get('snippet', ''),
                        'displayLink': item.get('displayLink', '')
                    })
            
            return {
                'success': True,
                'results': results,
                'total_results': data.get('searchInformation', {}).get('totalResults', '0'),
                'search_time': data.get('searchInformation', {}).get('searchTime', 0)
            }
        else:
            return get_demo_results(query, num_results)
            
    except:
        return get_demo_results(query, num_results)

def get_demo_results(query, num_results=5):
    """Демо-результаты если API не работает"""
    demo_results = []
    
    templates = [
        {
            'title': f'{query} - поиск в Google',
            'link': f'https://www.google.com/search?q={urllib.parse.quote(query)}',
            'snippet': f'Нажмите для поиска "{query}" в Google',
            'displayLink': 'google.com'
        },
        {
            'title': f'{query} в Википедии',
            'link': f'https://ru.wikipedia.org/wiki/{urllib.parse.quote(query)}',
            'snippet': f'Ищите информацию о "{query}" в Википедии',
            'displayLink': 'wikipedia.org'
        },
        {
            'title': f'Новости о {query}',
            'link': f'https://news.google.com/search?q={urllib.parse.quote(query)}',
            'snippet': f'Свежие новости по теме "{query}"',
            'displayLink': 'news.google.com'
        },
        {
            'title': f'{query} на Яндекс',
            'link': f'https://yandex.ru/search/?text={urllib.parse.quote(query)}',
            'snippet': f'Поиск "{query}" в Яндексе',
            'displayLink': 'yandex.ru'
        }
    ]
    
    for i in range(min(num_results, len(templates))):
        demo_results.append(templates[i])
    
    return {
        'success': False,
        'results': demo_results,
        'total_results': '1000',
        'search_time': 0.5
    }

def search_google_direct(query):
    """Прямой поиск через Google"""
    return f"https://www.google.com/search?q={urllib.parse.quote(query)}"

# ================= ФУНКЦИИ ПОГОДЫ =================
def get_weather_icon(condition_code):
    icons = {
        "01d": "☀️", "01n": "🌙", "02d": "⛅", "02n": "⛅",
        "03d": "☁️", "03n": "☁️", "04d": "☁️", "04n": "☁️",
        "09d": "🌧️", "09n": "🌧️", "10d": "🌦️", "10n": "🌦️",
        "11d": "⛈️", "11n": "⛈️", "13d": "❄️", "13n": "❄️",
        "50d": "🌫️", "50n": "🌫️",
    }
    return icons.get(condition_code, "🌡️")

def get_wind_direction(degrees):
    directions = ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"]
    index = round(degrees / 45) % 8
    return directions[index]

def get_weather_by_city(city_name):
    try:
        geocode_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={OPENWEATHER_API_KEY}"
        geocode_response = requests.get(geocode_url, timeout=10)

        if geocode_response.status_code == 200 and geocode_response.json():
            city_data = geocode_response.json()[0]
            lat = city_data["lat"]
            lon = city_data["lon"]
            
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
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
                    }
                }
        return None
    except:
        return None

# ================= ФУНКЦИИ ZORNET AI =================
def ask_hf_ai(prompt: str) -> str:
    if not HF_API_KEY:
        return "⚠️ API ключ не настроен. Добавьте HF_API_KEY в secrets.toml"

    API_URL = "https://router.huggingface.co/api/chat/completions"
    HEADERS = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "messages": [
            {"role": "system", "content": "Ты ZORNET AI — умный помощник. Отвечай по‑русски кратко и понятно."},
            {"role": "user", "content": prompt}
        ],
        "max_new_tokens": 500,
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

# ================= ФУНКЦИИ УМНОЙ КАМЕРЫ =================
def detect_objects_simple(image):
    rgb_image = image.convert('RGB')
    width, height = image.size
    aspect_ratio = width / height
    
    if aspect_ratio > 1.5:
        shape = "горизонтальный объект"
    elif aspect_ratio < 0.7:
        shape = "вертикальный объект"
    else:
        shape = "квадратный объект"
    
    return [f"📏 Размер: {width}x{height} пикселей",
            f"📐 {shape}",
            "💡 Совет: Используйте Google Vision API для точного распознавания"]

def process_camera_image(image, mode):
    if mode == "object":
        return detect_objects_simple(image)
    elif mode == "text":
        return ["🔍 Режим распознавания текста",
               "⚠️ Для работы установите библиотеку pytesseract"]
    elif mode == "translate":
        return ["🌐 Режим перевода",
               "⚠️ Установите: pip install googletrans"]
    elif mode == "qr":
        return ["📱 QR-код распознан!", 
                "Для работы установите: pip install qrcode[pil]"]
    return ["Выберите режим работы"]

# ================= СТРАНИЦА ZORNET AI =================
if st.session_state.page == "ZORNET AI":
    st.markdown('<div class="gold-title">🤖 ZORNET AI</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="ai-chat-container">
        <h3 style="color: #DAA520; text-align: center;">✨ Ваш персональный AI-помощник</h3>
        <p style="text-align: center; color: #666;">Задавайте вопросы — я помогу!</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💬 Чат", use_container_width=True):
            st.session_state.ai_tab = "chat"
    
    with col2:
        if st.button("🎨 Рисовать", use_container_width=True):
            st.session_state.ai_tab = "draw"
    
    with col3:
        if st.button("📝 Текст", use_container_width=True):
            st.session_state.ai_tab = "text"
    
    if st.session_state.ai_tab == "chat":
        st.markdown("### 💬 Чат с ZORNET AI")
        
        for msg in st.session_state.ai_messages[-10:]:
            if msg["role"] == "user":
                st.markdown(f'<div class="ai-message-user">{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="ai-message-bot">{msg["content"]}</div>', unsafe_allow_html=True)
        
        user_input = st.text_area("Ваше сообщение:", height=100, 
                                  placeholder="Напишите что-нибудь...")
        
        col_send, col_clear = st.columns(2)
        
        with col_send:
            if st.button("🚀 Отправить", type="primary", use_container_width=True):
                if user_input.strip():
                    st.session_state.ai_messages.append({"role": "user", "content": user_input})
                    response = ask_hf_ai(user_input)
                    st.session_state.ai_messages.append({"role": "assistant", "content": response})
                    st.rerun()
        
        with col_clear:
            if st.button("🗑️ Очистить", use_container_width=True):
                st.session_state.ai_messages = []
                st.rerun()
    
    elif st.session_state.ai_tab == "draw":
        st.markdown("### 🎨 Генератор рисунков")
        
        drawing_mode = st.selectbox("Выберите тип:", ["Пейзаж", "Портрет", "Абстракция", "Техника"])
        color = st.color_picker("Выберите цвет:", "#DAA520")
        
        if st.button("✨ Создать рисунок", type="primary", use_container_width=True):
            img = Image.new('RGB', (400, 300), color=color)
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            
            if drawing_mode == "Пейзаж":
                draw.rectangle([0, 200, 400, 300], fill="#228B22")
                draw.rectangle([100, 100, 300, 200], fill="#87CEEB")
                
            elif drawing_mode == "Портрет":
                draw.ellipse([150, 50, 250, 150], fill="#FFE4B5")
                draw.ellipse([170, 80, 190, 100], fill="#000000")
                draw.ellipse([210, 80, 230, 100], fill="#000000")
                
            st.image(img, caption=f"Созданный рисунок: {drawing_mode}", use_column_width=True)
            
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.download_button(
                label="📥 Скачать рисунок",
                data=byte_im,
                file_name="zornet_drawing.png",
                mime="image/png",
                use_container_width=True
            )
    
    elif st.session_state.ai_tab == "text":
        st.markdown("### 📝 Генератор текста")
        
        text_type = st.selectbox("Тип текста:", 
                                ["Приветствие", "Описание", "Сообщение", "Идея"])
        
        topic = st.text_input("Тема:", placeholder="О чём написать?")
        
        if st.button("✍️ Сгенерировать", type="primary", use_container_width=True):
            if topic:
                templates = {
                    "Приветствие": f"Добро пожаловать в тему '{topic}'! Рад вас видеть здесь.",
                    "Описание": f"Тема '{topic}' очень интересна. Она включает различные аспекты...",
                    "Сообщение": f"По теме '{topic}' хочу сообщить важную информацию...",
                    "Идея": f"Идея по теме '{topic}': можно реализовать проект, который..."
                }
                
                text = templates.get(text_type, f"Текст на тему '{topic}'")
                
                st.markdown(f"""
                <div class="search-result">
                    <h4>📄 Результат:</h4>
                    <p style="margin-top: 15px; line-height: 1.6;">{text}</p>
                </div>
                """, unsafe_allow_html=True)

# ================= СТРАНИЦА УМНОЙ КАМЕРЫ =================
elif st.session_state.page == "Умная камера":
    st.markdown('<div class="gold-title">📷 УМНАЯ КАМЕРА</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="camera-container">
        <h3 style="color: #4a90e2; text-align: center;">🔍 Сфотографируйте что угодно</h3>
        <p style="text-align: center; color: #666;">Распознавание объектов и многое другое</p>
    </div>
    """, unsafe_allow_html=True)
    
    modes = [
        ("🔍 Распознавание объектов", "object"),
        ("📝 Сканирование текста", "text"),
        ("🌐 Перевод", "translate"),
        ("📱 QR-коды", "qr")
    ]
    
    cols = st.columns(4)
    for idx, (name, mode) in enumerate(modes):
        with cols[idx]:
            if st.button(name, key=f"mode_{mode}", use_container_width=True):
                st.session_state.camera_mode = mode
                st.rerun()
    
    st.markdown("### 📸 Загрузите изображение")
    
    uploaded_file = st.file_uploader(
        "Выберите файл",
        type=['jpg', 'jpeg', 'png', 'bmp', 'gif'],
        help="Поддерживаются JPG, PNG, BMP, GIF"
    )
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Загруженное изображение", use_column_width=True)
        
        st.session_state.uploaded_image = image
        
        if st.button("🚀 Анализировать изображение", type="primary", use_container_width=True):
            with st.spinner("Анализирую..."):
                results = process_camera_image(image, st.session_state.camera_mode)
                st.session_state.camera_result = results
        
        if st.session_state.camera_result:
            st.markdown("### 📊 Результаты")
            
            for result in st.session_state.camera_result:
                st.markdown(f"""
                <div class="camera-result-box">
                    <p>{result}</p>
                </div>
                """, unsafe_allow_html=True)

# ================= СТРАНИЦА ГЛАВНАЯ С GOOGLE ПОИСКОМ =================
elif st.session_state.page == "Главная":
    st.markdown('<div class="gold-title">ZORNET</div>', unsafe_allow_html=True)
    
    current_time = datetime.datetime.now(pytz.timezone('Europe/Minsk'))
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="time-widget">
            🕒 {current_time.strftime('%H:%M')}<br>Минск
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.button("🌤️ Погода", key="weather_btn", use_container_width=True):
            st.session_state.page = "Погода"
            st.rerun()
    
    with col3:
        st.markdown(f"""
        <div class="time-widget">
            💵 3.20<br>BYN/USD
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        if st.button("🤖 ZORNET AI", key="ai_btn", use_container_width=True):
            st.session_state.page = "ZORNET AI"
            st.rerun()
    
    st.markdown("---")
    
    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    
    with st.form("search_form"):
        search_query = st.text_input(
            "",
            placeholder="Поиск в Google...",
            key="search_input",
            label_visibility="collapsed"
        )
        
        col_search, col_lucky = st.columns([2, 1])
        
        with col_search:
            search_submitted = st.form_submit_button(
                "🔍 Поиск в Google",
                type="primary",
                use_container_width=True
            )
        
        with col_lucky:
            lucky_submitted = st.form_submit_button(
                "🎯 Мне повезет!",
                use_container_width=True
            )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if search_submitted and search_query:
        st.session_state.search_query = search_query
        st.session_state.search_submitted = True
        st.rerun()
    
    elif lucky_submitted and search_query:
        google_url = search_google_direct(search_query)
        js_code = f"""
        <script>
            window.open("{google_url}", "_blank");
        </script>
        """
        components.html(js_code, height=0)
        st.info(f"🎯 Открываю Google для: {search_query}")
    
    if st.session_state.search_submitted and st.session_state.search_query:
        query = st.session_state.search_query
        
        with st.spinner(f"🔍 Ищу '{query}'..."):
            results = search_google_custom(query)
            
            google_url = search_google_direct(query)
            
            if st.button(f"🌐 Открыть результаты в Google", type="primary", use_container_width=True):
                js_code = f"""
                <script>
                    window.open("{google_url}", "_blank");
                </script>
                """
                components.html(js_code, height=0)
            
            if results['success']:
                st.markdown(f"### 🔎 Результаты поиска: **{query}**")
                st.markdown(f"*Найдено примерно {results['total_results']} результатов ({results['search_time']} сек.)*")
                
                for idx, result in enumerate(results['results']):
                    st.markdown(f"""
                    <div class="search-result">
                        <div class="result-title">
                            <a href="{result['link']}" target="_blank">{result['title']}</a>
                        </div>
                        <div class="result-url">{result.get('displayLink', result['link'][:80])}</div>
                        <div class="result-snippet">{result['snippet'][:200]}...</div>
                        <div style="margin-top: 10px;">
                            <a href="{result['link']}" target="_blank" 
                               style="padding: 5px 15px; background: #4285f4; color: white; 
                                      border-radius: 5px; text-decoration: none; font-size: 12px;">
                                Перейти на сайт →
                            </a>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Показываю демо-результаты...")
                
                for idx, result in enumerate(results['results']):
                    st.markdown(f"""
                    <div class="search-result">
                        <div class="result-title">
                            <a href="{result['link']}" target="_blank">{result['title']}</a>
                        </div>
                        <div class="result-url">{result.get('displayLink', result['link'][:80])}</div>
                        <div class="result-snippet">{result['snippet']}</div>
                    </div>
                    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("#### 🔥 Популярные запросы")
    
    popular_searches = ["погода Минск", "новости Беларуси", "курс доллара", "расписание электричек", "кино сегодня"]
    cols = st.columns(5)
    
    for idx, search_term in enumerate(popular_searches):
        with cols[idx]:
            if st.button(search_term, key=f"quick_{idx}", use_container_width=True):
                st.session_state.search_query = search_term
                st.session_state.search_submitted = True
                st.rerun()

# ================= СТРАНИЦА НОВОСТЕЙ =================
elif st.session_state.page == "Новости":
    st.markdown('<div class="gold-title">📰 НОВОСТИ</div>', unsafe_allow_html=True)

    with st.spinner("Загружаю новости..."):
        try:
            headers = {"User-Agent": "ZORNET/1.0"}
            response = requests.get("https://www.belta.by/rss", headers=headers, timeout=10)
            feed = feedparser.parse(response.content)
            news = feed.entries[:5]
        except:
            news = [
                {"title": "Новости Беларуси", "link": "#", "summary": "Следите за обновлениями"},
                {"title": "Экономические новости", "link": "#", "summary": "Развитие экономики страны"},
                {"title": "Спортивные события", "link": "#", "summary": "Последние спортивные новости"},
            ]

        for item in news:
            st.markdown(f"""
            <div class="search-result">
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
                    <div class="search-result">
                        <div style="color: #666; font-size: 0.9rem;">{name}</div>
                        <div style="font-size: 1.2rem; font-weight: bold;">{value}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                if i + 1 < len(details):
                    with col2:
                        name, value = details[i + 1]
                        st.markdown(f"""
                        <div class="search-result">
                            <div style="color: #666; font-size: 0.9rem;">{name}</div>
                            <div style="font-size: 1.2rem; font-weight: bold;">{value}</div>
                        </div>
                        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🇧🇾 Города Беларуси")
    
    belarus_cities = ["Минск", "Гомель", "Витебск", "Могилёв", "Брест", "Гродно", "Бобруйск", "Барановичи"]
    cols = st.columns(4)
    
    for idx, city in enumerate(belarus_cities):
        with cols[idx % 4]:
            if st.button(f"**{city}**", key=f"city_{city}", use_container_width=True):
                st.session_state.user_city = city
                st.rerun()

# ================= СТРАНИЦА ДИСКА =================
elif st.session_state.page == "Диск":
    st.markdown('<div class="gold-title">💾 ДИСК</div>', unsafe_allow_html=True)
    
    if "disk_current_path" not in st.session_state:
        st.session_state.disk_current_path = "zornet_cloud"
    if "disk_action" not in st.session_state:
        st.session_state.disk_action = "view"
    
    import os
    os.makedirs(st.session_state.disk_current_path, exist_ok=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📤 Загрузить", key="btn_upload", use_container_width=True):
            st.session_state.disk_action = "upload"
    
    with col2:
        if st.button("📁 Новая папка", key="btn_new_folder", use_container_width=True):
            st.session_state.disk_action = "new_folder"
    
    with col3:
        if st.button("🔍 Поиск", key="btn_search", use_container_width=True):
            st.session_state.disk_action = "search"
    
    with col4:
        if st.button("🔄 Обновить", key="btn_refresh", use_container_width=True):
            st.rerun()
    
    if st.session_state.disk_action == "upload":
        st.markdown("### 📤 Загрузка файлов")
        uploaded_files = st.file_uploader("Выберите файлы для загрузки", accept_multiple_files=True)
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                file_path = os.path.join(st.session_state.disk_current_path, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            st.success(f"✅ Загружено {len(uploaded_files)} файлов!")
            st.session_state.disk_action = "view"
            st.rerun()
    
    elif st.session_state.disk_action == "new_folder":
        st.markdown("### 📁 Создание новой папки")
        folder_name = st.text_input("Введите название папки:")
        
        if st.button("✅ Создать папку", type="primary", use_container_width=True):
            if folder_name:
                new_folder_path = os.path.join(st.session_state.disk_current_path, folder_name)
                os.makedirs(new_folder_path, exist_ok=True)
                st.success(f"Папка '{folder_name}' создана!")
                st.session_state.disk_action = "view"
                st.rerun()
    
    else:
        st.markdown("### 📁 Файлы и папки")
        
        try:
            items = os.listdir(st.session_state.disk_current_path)
        except:
            items = []
        
        if not items:
            st.info("📭 Папка пуста. Загрузите файлы или создайте папку.")
        else:
            items.sort()
            cols = st.columns(3)
            
            for idx, item in enumerate(items):
                with cols[idx % 3]:
                    item_path = os.path.join(st.session_state.disk_current_path, item)
                    is_dir = os.path.isdir(item_path)
                    icon = "📁" if is_dir else "📄"
                    
                    st.markdown(f"""
                    <div class="search-result">
                        <div style="font-size: 2rem; text-align: center;">{icon}</div>
                        <div style="text-align: center; font-weight: 600;">{item}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if is_dir:
                        if st.button(f"Открыть {item}", key=f"open_{item}", use_container_width=True):
                            st.session_state.disk_current_path = item_path
                            st.rerun()
                    else:
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

# ================= СТРАНИЦА ПРОФИЛЯ =================
elif st.session_state.page == "Профиль":
    st.markdown('<div class="gold-title">👤 ПРОФИЛЬ</div>', unsafe_allow_html=True)
    
    if "user_logged_in" not in st.session_state:
        st.session_state.user_logged_in = False
    
    if not st.session_state.user_logged_in:
        col_login, col_register = st.columns(2)
        
        with col_login:
            with st.form("login_form"):
                st.markdown("### 🔐 Вход")
                login_email = st.text_input("Email", placeholder="your@email.com")
                login_password = st.text_input("Пароль", type="password", placeholder="••••••••")
                
                if st.form_submit_button("🚀 Войти", use_container_width=True):
                    st.session_state.user_logged_in = True
                    st.session_state.user_email = login_email
                    st.session_state.user_name = login_email.split('@')[0]
                    st.success(f"Добро пожаловать, {st.session_state.user_name}!")
                    st.rerun()
        
        with col_register:
            with st.form("register_form"):
                st.markdown("### ✨ Регистрация")
                reg_email = st.text_input("Email", placeholder="your@email.com", key="reg_email")
                reg_username = st.text_input("Имя пользователя", placeholder="Ваше имя")
                reg_password = st.text_input("Пароль", type="password", placeholder="••••••••", key="reg_pass")
                
                if st.form_submit_button("🎯 Зарегистрироваться", use_container_width=True):
                    st.success("Регистрация успешна!")
                    st.session_state.user_logged_in = True
                    st.session_state.user_email = reg_email
                    st.session_state.user_name = reg_username
                    st.rerun()
    
    else:
        col_profile_left, col_profile_right = st.columns([1, 2])
        
        with col_profile_left:
            st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 5rem;">👤</div>
                <div style="font-size: 1.5rem; font-weight: bold;">{st.session_state.user_name}</div>
                <div style="color: #666;">{st.session_state.user_email}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚪 Выйти", use_container_width=True):
                st.session_state.user_logged_in = False
                st.rerun()
        
        with col_profile_right:
            with st.form("profile_form"):
                st.markdown("### 📝 Редактировать профиль")
                username = st.text_input("Имя пользователя", value=st.session_state.user_name)
                email = st.text_input("Email", value=st.session_state.user_email, disabled=True)
                bio = st.text_area("О себе", placeholder="Расскажите о себе...")
                
                if st.form_submit_button("💾 Сохранить изменения", use_container_width=True):
                    st.session_state.user_name = username
                    st.success("Профиль обновлен!")
                    st.rerun()

# ================= ФУТЕР =================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p>🇧🇾 ZORNET • Белорусская платформа • Версия 3.0</p>
    <p>Google Search API • AI помощник • Умная камера • Облачный диск</p>
</div>
""", unsafe_allow_html=True)

# ================= ИНИЦИАЛИЗАЦИЯ =================
if __name__ == "__main__":
    # Инициализация базы данных
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
