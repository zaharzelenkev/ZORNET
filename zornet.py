import streamlit as st
import sqlite3
import datetime
import os
import pytz
import requests
import feedparser
from PIL import Image
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import json
from google_auth_oauthlib.flow import Flow
from pathlib import Path
import mimetypes
import time
from duckduckgo_search import DDGS
from streamlit_folium import st_folium
import folium
import random
from huggingface_hub import InferenceClient

# HF_API_KEY — добавь в Streamlit Secrets
HF_API_KEY = st.secrets["HF_API_KEY"]
client = InferenceClient(HF_API_KEY)

if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = []

def ask_hf_ai(prompt, history=[]):
    context = ""
    for msg in history[-5:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            context += f"Пользователь: {content}\n"
        else:
            context += f"Ассистент: {content}\n"
    context += f"Пользователь: {prompt}\nАссистент:"

    response = client.text_generation(
        model="mistralai/Mistral-mini-7B-v0.1",
        inputs=context,
        max_new_tokens=200,
        temperature=0.7
    )
    return response.generated_text.strip()

st.set_page_config(
    page_title="ZORNET",
    page_icon="🇧🇾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------------------
# Google OAuth Functions
# ----------------------------

def upload_to_drive(file, parent_id, creds):
    """Загружает файл в Google Drive"""
    try:
        service = build("drive", "v3", credentials=creds)

        mime_type, _ = mimetypes.guess_type(file.name)

        metadata = {
            "name": file.name,
            "parents": [parent_id]
        }

        media = MediaIoBaseUpload(
            file,
            mimetype=mime_type,
            resumable=True
        )

        service.files().create(
            body=metadata,
            media_body=media,
            fields="id"
        ).execute()
        return True
    except Exception as e:
        st.error(f"Ошибка загрузки в Drive: {e}")
        return False


def delete_drive_file(file_id, creds):
    """Удаляет файл из Google Drive"""
    try:
        service = build("drive", "v3", credentials=creds)
        service.files().delete(fileId=file_id).execute()
        return True
    except Exception as e:
        st.error(f"Ошибка удаления из Drive: {e}")
        return False


def login_with_google():
    """Создает URL для авторизации через Google"""
    try:
        flow = Flow.from_client_secrets_file(
            "client_secret.json",
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )

        # Добавляем параметр prompt="select_account"
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="select_account"
        )

        st.markdown(
            f'<a href="{auth_url}" target="_self" style="display: inline-block; padding: 12px 24px; background: #4285F4; color: white; border-radius: 8px; text-decoration: none; font-weight: 500;">🔑 Войти через Google</a>',
            unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Ошибка Google OAuth: {e}")


def get_credentials(code):
    """Получает credentials по коду авторизации"""
    try:
        flow = Flow.from_client_secrets_file(
            "client_secret.json",
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )

        flow.fetch_token(code=code)
        creds = flow.credentials

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

        return creds
    except Exception as e:
        st.error(f"Ошибка получения токена: {e}")
        return None


def load_credentials():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return Credentials.from_authorized_user_info(json.load(f), SCOPES)
    return None


def get_belta_news():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (ZORNET/1.0; +https://zornet.app)"
        }
        r = requests.get("https://www.belta.by/rss", headers=headers, timeout=30)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        return feed.entries[:10]
    except requests.exceptions.Timeout:
        st.error("Ошибка загрузки: Время ожидания истекло. Попробуйте позже.")
        return []
    except requests.exceptions.RequestException as e:
        st.error(f"Ошибка при подключении к БелТА: {e}")
        return []
    except Exception as e:
        st.error(f"Неизвестная ошибка: {e}")
        return []


# Добавь ЭТО после функции get_belta_news() (около строки 95)

# =================================================
# ТРАНСПОРТНЫЕ ФУНКЦИИ
# =================================================

def get_minsk_metro():
    """Расписание минского метро"""
    stations = [
        {"name": "Малиновка", "line": "1", "next_train": "3 мин"},
        {"name": "Петровщина", "line": "1", "next_train": "5 мин"},
        {"name": "Площадь Ленина", "line": "1", "next_train": "2 мин"},
        {"name": "Купаловская", "line": "2", "next_train": "4 мин"},
        {"name": "Немига", "line": "2", "next_train": "6 мин"},
    ]
    return stations


def get_bus_trams():
    """Расписание автобусов и трамваев Минска"""
    routes = [
        {"number": "100", "type": "автобус", "from": "Ст.м. Каменная Горка", "to": "Аэропорт", "next": "7 мин"},
        {"number": "1", "type": "трамвай", "from": "Тракторный завод", "to": "Серебрянка", "next": "5 мин"},
        {"number": "3с", "type": "троллейбус", "from": "ДС Веснянка", "to": "ДС Серова", "next": "3 мин"},
    ]
    return routes


def get_taxi_prices():
    """Сравнение цен такси"""
    services = [
        {"name": "Яндекс Такси", "price": "8-12 руб", "wait": "5-7 мин"},
        {"name": "Uber", "price": "9-13 руб", "wait": "4-6 мин"},
        {"name": "Такси Близко", "price": "7-10 руб", "wait": "8-10 мин"},
        {"name": "Такси Город", "price": "6-9 руб", "wait": "10-15 мин"},
    ]
    return services


def get_belarusian_railway():
    """Расписание Белорусской железной дороги"""
    trains = [
        {"number": "001Б", "from": "Минск", "to": "Брест", "departure": "18:00", "arrival": "21:30"},
        {"number": "735Б", "from": "Минск", "to": "Гомель", "departure": "07:30", "arrival": "11:15"},
        {"number": "603Б", "from": "Минск", "to": "Витебск", "departure": "14:20", "arrival": "18:45"},
    ]
    return trains


def get_airport_info():
    """Информация об аэропортах"""
    airports = [
        {"name": "Минск (MSQ)", "flights": "норм", "delays": "нет"},
        {"name": "Гомель (GME)", "flights": "мало", "delays": "нет"},
        {"name": "Брест (BQT)", "flights": "ограничено", "delays": "нет"},
    ]
    return airports


def get_traffic_jams():
    """Пробки в Минске и других городах"""
    cities = [
        {"city": "Минск", "level": "3/5", "description": "Умеренные пробки"},
        {"city": "Гомель", "level": "2/5", "description": "Свободно"},
        {"city": "Брест", "level": "1/5", "description": "Очень свободно"},
    ]
    return cities


# ================= ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ =================

def calculate_route(start, end, transport_type="car"):
    """Маршрутизатор - построение маршрутов"""
    routes = [
        {"type": "🚗 На машине", "time": "25 мин", "distance": "12 км", "price": "≈ 15 руб"},
        {"type": "🚌 Общ. транспорт", "time": "45 мин", "distance": "14 км", "price": "0.90 руб"},
        {"type": "🚕 Такси", "time": "22 мин", "distance": "12 км", "price": "8-12 руб"},
        {"type": "🚲 На велосипеде", "time": "55 мин", "distance": "11 км", "price": "0 руб"},
    ]
    return routes


def get_gas_prices():
    """Цены на бензин по заправкам"""
    stations = [
        {"name": "Белоруснефть", "ai92": "2.15", "ai95": "2.25", "ai98": "2.55", "diesel": "2.10"},
        {"name": "Лукойл", "ai92": "2.14", "ai95": "2.24", "ai98": "2.54", "diesel": "2.09"},
        {"name": "Газпромнефть", "ai92": "2.16", "ai95": "2.26", "ai98": "2.56", "diesel": "2.11"},
    ]
    return stations


def get_carsharing_services():
    """Сравнение каршеринга"""
    services = [
        {"name": "Anytime", "price_min": "0.35", "price_km": "0.85", "deposit": "200 руб"},
        {"name": "BelkaCar", "price_min": "0.33", "price_km": "0.80", "deposit": "150 руб"},
        {"name": "MyCar", "price_min": "0.30", "price_km": "0.75", "deposit": "100 руб"},
    ]
    return services


def get_bike_scooter_stations():
    """Велосипеды и самокаты - карта станций"""
    stations = [
        {"name": "Пл. Независимости", "bikes": "8", "scooters": "5", "status": "🟢"},
        {"name": "ТЦ Галилео", "bikes": "3", "scooters": "7", "status": "🟡"},
        {"name": "Парк Горького", "bikes": "12", "scooters": "10", "status": "🟢"},
        {"name": "Вокзал", "bikes": "0", "scooters": "4", "status": "🔴"},
    ]
    return stations


def get_parking_info():
    """Информация о парковках"""
    parkings = [
        {"name": "Центральная парковка", "price_hour": "1.50", "free_spots": "15", "max_time": "2 ч"},
        {"name": "Подземная ТЦ Галилео", "price_hour": "2.00", "free_spots": "45", "max_time": "неогр"},
        {"name": "Возле НБ РБ", "price_hour": "1.00", "free_spots": "3", "max_time": "1 ч"},
    ]
    return parkings

# ===============================
# VISION AI (SAFE FOR STREAMLIT)
# ===============================

vision_available = False
vision_processor = None
vision_model = None

if torch is not None:
    try:
        from transformers import BlipProcessor, BlipForConditionalGeneration

        @st.cache_resource
        def load_vision_model():
            processor = BlipProcessor.from_pretrained(
                "Salesforce/blip-image-captioning-base"
            )
            model = BlipForConditionalGeneration.from_pretrained(
                "Salesforce/blip-image-captioning-base",
                use_safetensors=True
            )
            model.to("cpu")
            return processor, model

        vision_processor, vision_model = load_vision_model()
        vision_available = True

    except Exception:
        vision_available = False

# --- GOOGLE OAUTH HANDLING ---
query_params = st.query_params
if "code" in query_params and "google_creds" not in st.session_state:
    try:
        # Получаем токен
        creds = get_credentials(query_params["code"])
        st.session_state.google_creds = creds

        query_params = st.query_params

        if "code" in query_params and "google_creds" not in st.session_state:
            creds = get_credentials(query_params["code"])
            if creds:
                st.session_state.google_creds = creds
                st.session_state.page = "Профиль"

                st.success("✅ Вы вошли через Google")

    except Exception as e:
        st.error(f"Ошибка авторизации Google: {e}")


def init_user_drive(creds):
    service = build("drive", "v3", credentials=creds)

    # Проверяем, есть ли папка ZORNET_DISK
    results = service.files().list(
        q="name='ZORNET_DISK' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)"
    ).execute()

    files = results.get("files", [])

    if files:
        return files[0]["id"]

    # Создаем папку
    folder_metadata = {
        "name": "ZORNET_DISK",
        "mimeType": "application/vnd.google-apps.folder"
    }

    folder = service.files().create(
        body=folder_metadata,
        fields="id"
    ).execute()

    return folder["id"]


# --- CSS СТИЛИ (Professional & Clean) ---
st.markdown("""
<style>
    /* ОБЩИЙ СТИЛЬ */
    .stApp { background-color: #ffffff; color: #1a1a1a; font-family: 'Helvetica Neue', sans-serif; }

    /* СКРЫВАЕМ ЛИШНЕЕ */
    hr, .stDivider, div[data-testid="stHorizontalRule"] { display: none !important; }
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

    /* КНОПКИ ГЛАВНОЙ - ОБЫЧНЫЕ СЕРО-БЕЛЫЕ */
    div.stButton > button {
        background: #f8f9fa !important;
        border: 1px solid #dee2e6 !important;
        color: #1a1a1a !important;
        padding: 20px !important; 
        border-radius: 12px !important;
        font-weight: bold !important;
        width: 100% !important;
        text-align: left !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
        transition: transform 0.1s !important;
        border-left: 1px solid #dee2e6 !important; /* Убираем золотую полосу */
    }
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        border-color: #ccc !important;
    }

    /* СТИЛИ ДЛЯ ПРОФИЛЯ / ВХОДА */
    .auth-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 40px;
        background: white;
        border-radius: 24px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.1);
        text-align: center;
    }

    .auth-header {
        font-size: 28px;
        font-weight: 800;
        color: #1a1a1a;
        margin-bottom: 10px;
        letter-spacing: -0.5px;
    }

    .auth-sub {
        font-size: 14px;
        color: #888;
        margin-bottom: 30px;
    }

    /* Кастомные инпуты Streamlit */
    div[data-testid="stTextInput"] input {
        background-color: #f7f7f7 !important;
        border: 1px solid #eaeaea !important;
        border-radius: 12px !important;
        padding: 15px !important;
        color: #333 !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #DAA520 !important;
        box-shadow: 0 0 0 2px rgba(218, 165, 32, 0.2) !important;
    }

    /* Кнопка входа (черная) */
    .login-btn-container button {
        background: #1a1a1a !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 15px !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        border-left: none !important;
    }
    .login-btn-container button:hover {
        background: #333 !important;
        transform: translateY(-2px);
    }

    /* Google кнопка */
    .google-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        background: white;
        border: 1px solid #ddd;
        border-radius: 12px;
        padding: 12px;
        font-weight: 500;
        color: #555;
        cursor: pointer;
        transition: all 0.2s;
        text-decoration: none;
        margin-top: 15px;
    }
    .google-btn:hover {
        background: #f8f9fa;
        border-color: #ccc;
    }

    /* Переключатель Вход/Регистрация */
    .auth-toggle {
        display: flex;
        justify-content: center;
        gap: 20px;
        margin-bottom: 30px;
        border-bottom: 1px solid #eee;
        padding-bottom: 15px;
    }
    .toggle-item {
        font-weight: 600;
        cursor: pointer;
        color: #999;
        font-size: 16px;
        transition: 0.2s;
    }
    .toggle-item.active {
        color: #DAA520;
        border-bottom: 2px solid #DAA520;
        padding-bottom: 14px;
        margin-bottom: -16px;
    }

    /* ЧАТ */
    [data-testid="stChatMessage"] {
        padding: 15px !important;
        border-radius: 15px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }

    /* СТИЛЬ ПЕРЕПИСКИ ПО ФОТО - ПРОФЕССИОНАЛЬНЫЙ СЕРЫЙ */
    .chat-message-user {
        background: linear-gradient(135deg, #f5f5f5, #e8e8e8) !important;
        border: 1px solid #d0d0d0 !important;
        color: #2c2c2c !important;
        border-radius: 18px !important;
        padding: 16px 20px !important;
        margin-bottom: 15px !important;
        max-width: 85% !important;
        margin-left: auto !important;
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif !important;
        font-size: 15px !important;
        line-height: 1.5 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    }

    .chat-message-assistant {
        background: linear-gradient(135deg, #ffffff, #f9f9f9) !important;
        border: 1px solid #e0e0e0 !important;
        color: #2c2c2c !important;
        border-radius: 18px !important;
        padding: 16px 20px !important;
        margin-bottom: 15px !important;
        max-width: 85% !important;
        margin-right: auto !important;
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif !important;
        font-size: 15px !important;
        line-height: 1.5 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
        position: relative !important;
    }

    .chat-message-assistant::before {
        content: '🤖';
        position: absolute;
        left: -45px;
        top: 10px;
        font-size: 20px;
        background: linear-gradient(135deg, #DAA520, #B8860B);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* ЗОЛОТАЯ КНОПКА ZORNET AI ТОЛЬКО НА ГЛАВНОЙ */
    .gold-button-main-only {
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%) !important;
        border: none !important;
        color: white !important;
        border-radius: 12px !important;
        padding: 14px 28px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        letter-spacing: 0.5px !important;
        transition: all 0.3s !important;
        box-shadow: 0 4px 15px rgba(218, 165, 32, 0.3) !important;
    }

    .gold-button-main-only:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(218, 165, 32, 0.4) !important;
        background: linear-gradient(135deg, #B8860B 0%, #DAA520 100%) !important;
    }

    /* ОБЫЧНЫЕ ВИДЖЕТЫ (время, погода, курс) */
    .simple-widget {
        background: #f8f9fa !important;
        border: 1px solid #dee2e6 !important;
        border-radius: 10px !important;
        padding: 10px !important;
        text-align: center !important;
        font-weight: 500 !important;
        color: #495057 !important;
    }
</style>
""", unsafe_allow_html=True)


# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("zornet_pro.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, nick TEXT, gender TEXT, avatar_path TEXT)")
    c.execute("SELECT COUNT(*) FROM users WHERE id = 1")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (id, nick, gender) VALUES (1, 'Гость', 'Не указан')")
    conn.commit()
    conn.close()


# --- ФУНКЦИЯ ПОИСКА (ZORNET SEARCH) ---
def search_zornet(query, num_results=10):
    """Реальный поиск в интернете через DuckDuckGo"""
    results = []
    try:
        with DDGS() as ddgs:
            # Поиск сайтов
            search_gen = ddgs.text(query, max_results=num_results)
            for r in search_gen:
                results.append(r)
    except Exception as e:
        st.error(f"Ошибка поиска: {e}")
    return results


def get_user_data():
    conn = sqlite3.connect("zornet_pro.db")
    c = conn.cursor()
    c.execute("SELECT nick, gender, avatar_path FROM users WHERE id = 1")
    data = c.fetchone()
    conn.close()
    return data


init_db()
user_data = get_user_data()

# --- НАСТРОЙКИ СТРАНИЦЫ ---
if "page" not in st.session_state:
    st.session_state.page = "Главная"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_ai" not in st.session_state:
    st.session_state.pending_ai = False
if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = [
        {"role": "assistant", "content": "Привет! Я ZORNET AI. Чем могу помочь?"}
    ]


# =================================================
# ФУНКЦИИ ДЛЯ ДИСКА
# =================================================

def init_disk_db():
    """Инициализация базы данных для диска"""
    conn = sqlite3.connect("zornet_disk.db")
    c = conn.cursor()

    # Таблица файлов
    c.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            size INTEGER,
            file_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_folder BOOLEAN DEFAULT 0,
            parent_id INTEGER DEFAULT 0,
            user_id INTEGER DEFAULT 1,
            FOREIGN KEY (parent_id) REFERENCES files (id)
        )
    ''')

    # Таблица пользователей диска
    c.execute('''
        CREATE TABLE IF NOT EXISTS disk_users (
            user_id INTEGER PRIMARY KEY,
            used_space INTEGER DEFAULT 0,
            max_space INTEGER DEFAULT 5368709120,
            last_sync TIMESTAMP
        )
    ''')

    # Создаем корневую папку если нет
    c.execute("SELECT id FROM files WHERE name = 'root' AND is_folder = 1")
    if not c.fetchone():
        c.execute(
            "INSERT INTO files (name, path, is_folder, parent_id) VALUES (?, ?, ?, ?)",
            ("root", "/root", 1, 0)
        )

    # Инициализируем пользователя
    c.execute("SELECT user_id FROM disk_users WHERE user_id = 1")
    if not c.fetchone():
        c.execute(
            "INSERT INTO disk_users (user_id, used_space, max_space) VALUES (?, ?, ?)",
            (1, 0, 5368709120)
        )

    conn.commit()
    conn.close()

    # Создаем директории для хранения
    Path("storage/users/1").mkdir(parents=True, exist_ok=True)


def get_file_icon(file_type, is_folder=False):
    """Возвращает иконку для типа файла"""
    if is_folder:
        return "📁"

    icon_map = {
        'pdf': '📄',
        'doc': '📝', 'docx': '📝',
        'xls': '📊', 'xlsx': '📊',
        'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️',
        'mp3': '🎵', 'wav': '🎵',
        'mp4': '🎬', 'avi': '🎬', 'mov': '🎬',
        'zip': '📦', 'rar': '📦',
        'py': '🐍', 'js': '📜', 'html': '🌐', 'css': '🎨'
    }

    ext = file_type.lower() if file_type else ''
    return icon_map.get(ext, '📄')


def human_readable_size(size_bytes):
    """Конвертирует размер в читаемый формат"""
    if not size_bytes:
        return "0 Б"

    for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} ПБ"


def save_uploaded_file(uploaded_file, parent_id=0):
    """Сохраняет загруженный файл"""
    user_id = 1
    storage_path = f"storage/users/{user_id}"

    # Генерируем уникальное имя
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = uploaded_file.name.replace(" ", "_")
    unique_name = f"{timestamp}_{safe_name}"
    file_path = os.path.join(storage_path, unique_name)

    # Сохраняем файл
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Определяем тип файла
    file_type = uploaded_file.name.split('.')[-1] if '.' in uploaded_file.name else ''

    # Сохраняем в БД
    conn = sqlite3.connect("zornet_disk.db")
    c = conn.cursor()

    c.execute('''
        INSERT INTO files (name, path, size, file_type, is_folder, parent_id, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        uploaded_file.name,
        file_path,
        uploaded_file.size,
        file_type,
        0,
        parent_id,
        user_id
    ))

    # Обновляем использованное пространство
    c.execute(
        "UPDATE disk_users SET used_space = used_space + ? WHERE user_id = ?",
        (uploaded_file.size, user_id)
    )

    conn.commit()
    conn.close()

    return True


def create_folder(folder_name, parent_id=0):
    """Создает новую папку"""
    conn = sqlite3.connect("zornet_disk.db")
    c = conn.cursor()

    # Проверяем, нет ли уже папки с таким именем
    c.execute(
        "SELECT id FROM files WHERE name = ? AND is_folder = 1 AND parent_id = ?",
        (folder_name, parent_id)
    )

    if not c.fetchone():
        c.execute('''
            INSERT INTO files (name, path, is_folder, parent_id, user_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (folder_name, f"/{folder_name}", 1, parent_id, 1))
        conn.commit()

    conn.close()


def get_files_in_folder(parent_id=0):
    """Возвращает файлы в указанной папке"""
    conn = sqlite3.connect("zornet_disk.db")
    c = conn.cursor()

    c.execute('''
        SELECT id, name, path, size, file_type, created_at, is_folder
        FROM files 
        WHERE parent_id = ? AND user_id = 1
        ORDER BY is_folder DESC, name ASC
    ''', (parent_id,))

    files = c.fetchall()
    conn.close()
    return files


def delete_file(file_id):
    """Удаляет файл или папку"""
    conn = sqlite3.connect("zornet_disk.db")
    c = conn.cursor()

    # Получаем информацию о файле
    c.execute("SELECT path, size, is_folder FROM files WHERE id = ?", (file_id,))
    file_info = c.fetchone()

    if file_info:
        path, size, is_folder = file_info

        # Удаляем физический файл (если не папка)
        if not is_folder and os.path.exists(path):
            os.remove(path)
            # Обновляем использованное пространство
            c.execute(
                "UPDATE disk_users SET used_space = used_space - ? WHERE user_id = ?",
                (size or 0, 1)
            )

        # Удаляем запись из БД
        c.execute("DELETE FROM files WHERE id = ?", (file_id,))

        # Если это папка, удаляем все файлы внутри
        if is_folder:
            c.execute("SELECT id FROM files WHERE parent_id = ?", (file_id,))
            child_files = c.fetchall()
            for child_id in child_files:
                delete_file(child_id[0])

    conn.commit()
    conn.close()


def get_disk_usage():
    """Возвращает статистику использования диска"""
    conn = sqlite3.connect("zornet_disk.db")
    c = conn.cursor()

    c.execute("SELECT used_space, max_space FROM disk_users WHERE user_id = 1")
    usage = c.fetchone()
    conn.close()

    if usage:
        used, total = usage
        percent = (used / total * 100) if total > 0 else 0
        return used, total, percent
    return 0, 5368709120, 0


# =================================================
# САЙДБАР (ОБЩИЙ ДЛЯ ВСЕХ СТРАНИЦ)
# =================================================
with st.sidebar:
    st.markdown("<h3 style='color:#DAA520;'>🇧🇾 ZORNET</h3>", unsafe_allow_html=True)

    nav_items = [
        ("🏠", "ГЛАВНАЯ", "Главная"),
        ("🤖", "ZORNET AI", "ZORNET AI"),
        ("📰", "НОВОСТИ", "Новости"),
        ("💾", "ДИСК", "Диск"),
        ("🚌", "ТРАНСПОРТ", "Транспорт"),
        ("👤", "ПРОФИЛЬ", "Профиль"),
        ("📷", "КАМЕРА", "Камера"),
    ]

    for icon, text, page in nav_items:
        if st.button(f"{icon} {text}", key=f"nav_{page}", use_container_width=True):
            st.session_state.page = page
            if page != "Главная":
                st.session_state.messages = []
            st.rerun()


# =================================================
# ФУНКЦИИ ПОИСКА
# =================================================

def search_zornet(query, num_results=10, region="by-ru", safesearch="moderate"):
    """Реальный поиск в интернете через DuckDuckGo"""
    results = []
    try:
        with DDGS() as ddgs:
            # Поиск сайтов с указанием региона и настроек безопасности
            search_gen = ddgs.text(
                query,
                max_results=num_results,
                region=region,
                safesearch=safesearch
            )

            for r in search_gen:
                # Форматируем результат
                result = {
                    "title": r.get("title", "Без названия"),
                    "url": r.get("href", "#"),
                    "snippet": r.get("body", "Описание отсутствует"),
                    "source": r.get("href", "").split("/")[2] if "/" in r.get("href", "") else ""
                }
                results.append(result)

    except Exception as e:
        st.error(f"Ошибка поиска: {e}")
        # Запасные результаты на случай ошибки
        results = get_fallback_results(query)

    return results


def get_fallback_results(query):
    """Запасные результаты на случай если поиск не работает"""
    fallbacks = [
        {
            "title": f"Результаты по запросу: {query}",
            "url": "https://www.google.com/search",
            "snippet": "Поиск в интернете временно недоступен. Попробуйте позже.",
            "source": "Zornet Search"
        },
        {
            "title": "Белорусские новости онлайн",
            "url": "https://www.belta.by",
            "snippet": "Последние новости Беларуси и мира на официальном сайте БелТА.",
            "source": "belta.by"
        },
        {
            "title": "Карты и навигация",
            "url": "https://maps.google.com",
            "snippet": "Построение маршрутов, карты городов Беларуси.",
            "source": "google.com"
        }
    ]
    return fallbacks


def get_search_suggestions(query):
    """Получает подсказки для поиска"""
    suggestions = []
    try:
        with DDGS() as ddgs:
            suggestions_gen = ddgs.suggestions(query)
            suggestions = [s for s in suggestions_gen]
    except:
        suggestions = [f"{query} в Беларуси", f"{query} 2024", f"{query} минск"]

    return suggestions[:5]


def get_popular_searches():
    """Популярные поисковые запросы"""
    return [
        "Новости Беларуси сегодня",
        "Курс доллара в Беларуси",
        "Погода в Минске",
        "Расписание электричек",
        "Карта метро Минска",
        "Такси Минск цены",
        "Обмен валюты",
        "Гостиницы в Минске",
        "Афиша мероприятий",
        "Работа в Минске"
    ]


# =================================================
# ГЛАВНАЯ СТРАНИЦА (ИСПРАВЛЕННАЯ - ВЕРНУЛ КАК БЫЛО)
# =================================================
if st.session_state.page == "Главная":
    # ВЕРХНЯЯ ПАНЕЛЬ С ПОИСКОМ И КНОПКОЙ ZORNET AI
    col1, col2, col3 = st.columns([1, 3, 1])

    with col1:
        # ЗОЛОТАЯ КНОПКА ZORNET AI
        st.markdown("""
        <style>
        div[data-testid="stButton"] > button[kind="secondary"] {
            background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%) !important;
            border: none !important;
            color: white !important;
            border-radius: 12px !important;
            padding: 14px 28px !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            letter-spacing: 0.5px !important;
            transition: all 0.3s !important;
            box-shadow: 0 4px 15px rgba(218, 165, 32, 0.3) !important;
        }

        div[data-testid="stButton"] > button[kind="secondary"]:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(218, 165, 32, 0.4) !important;
            background: linear-gradient(135deg, #B8860B 0%, #DAA520 100%) !important;
        }
        </style>
        """, unsafe_allow_html=True)

        if st.button("🤖 **ZORNET AI**", key="zornet_ai_btn", type="secondary", use_container_width=True,
                     help="Открыть ZORNET AI чат"):
            st.session_state.page = "ZORNET AI"
            st.rerun()

    with col2:
        # ПОИСКОВАЯ СТРОКА
        search_query = st.text_input(
            "",
            placeholder="🔍 Поиск в интернете...",
            key="main_search",
            label_visibility="collapsed"
        )

    with col3:
        # ВРЕМЯ И ДАТА - обычный виджет
        current_time = datetime.datetime.now(pytz.timezone('Europe/Minsk'))
        st.markdown(f"""
        <div class="simple-widget">
            <div style="font-weight: 600; color: #1a1a1a;">{current_time.strftime('%H:%M')}</div>
            <div style="font-size: 12px; color: #666;">{current_time.strftime('%d.%m.%Y')}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="gold-title">ZORNET</div>', unsafe_allow_html=True)

    # Виджеты - обычные серо-белые
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        # ВРЕМЯ
        current_time = datetime.datetime.now(pytz.timezone('Europe/Minsk'))
        if st.button(f"🕒 {current_time.strftime('%H:%M')}\nМинск", use_container_width=True):
            pass  # Ничего не делаем, просто виджет

    with c2:
        # ПОГОДА - обычная кнопка
        if st.button("⛅ -5°C\nМинск", use_container_width=True):
            pass  # Ничего не делаем, просто виджет

    with c3:
        # КУРС ДОЛЛАРА - обычная кнопка
        if st.button("💵 3.20\nBYN/USD", use_container_width=True):
            pass  # Ничего не делаем, просто виджет

    with c4:
        # ТРАНСПОРТ - обычная кнопка
        if st.button("🚌 ТРАНСПОРТ\n", use_container_width=True):
            st.session_state.page = "Транспорт"
            st.rerun()

    st.markdown("---")

    # ПОИСКОВЫЕ РЕЗУЛЬТАТЫ (если есть запрос)
    if search_query:
        st.markdown(f"### 🔍 Результаты поиска: **{search_query}**")

        with st.spinner("Ищу информацию..."):
            results = search_zornet(search_query, num_results=8)

            if results:
                # Подсказки для поиска
                suggestions = get_search_suggestions(search_query)
                if suggestions:
                    st.markdown("**✨ Похожие запросы:**")
                    cols = st.columns(len(suggestions))
                    for idx, suggestion in enumerate(suggestions):
                        with cols[idx]:
                            if st.button(suggestion, key=f"sugg_{idx}", use_container_width=True):
                                st.session_state.search_query = suggestion
                                st.rerun()

                # Результаты поиска
                for idx, result in enumerate(results):
                    with st.container():
                        st.markdown(f"""
                        <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #DAA520;">
                            <div style="font-weight: 600; color: #1a1a1a; margin-bottom: 5px; font-size: 16px;">
                                {idx + 1}. {result['title']}
                            </div>
                            <div style="color: #1a73e8; font-size: 13px; margin-bottom: 8px;">{result['url'][:80]}...</div>
                            <div style="color: #555; font-size: 14px;">{result['snippet'][:200]}...</div>
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
                st.markdown("""
                <div style="text-align: center; padding: 60px 20px; color: #666;">
                    <div style="font-size: 48px; margin-bottom: 20px; opacity: 0.3;">🔍</div>
                    <h3>Ничего не найдено</h3>
                    <p>Попробуйте изменить запрос или проверьте соединение с интернетом</p>
                </div>
                """, unsafe_allow_html=True)

elif st.session_state.page == "ZORNET AI":
    st.markdown('<div class="gold-title">🤖 ZORNET AI</div>', unsafe_allow_html=True)

    # Инициализация сообщений чата
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = [
            {"role": "assistant", "content": "Привет! Я ZORNET AI. Чем могу помочь?"}
        ]

    # Отображение истории сообщений с профессиональным стилем
    for message in st.session_state.ai_messages:
        if message["role"] == "user":
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; margin-bottom: 15px;">
                <div class="chat-message-user">
                    {message["content"]}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="display: flex; align-items: flex-start; margin-bottom: 15px;">
                <div class="chat-message-assistant">
                    {message["content"]}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Поле ввода
    if prompt := st.chat_input("Спросите ZORNET AI...", key="ai_chat_input"):
        # Добавляем сообщение пользователя с профессиональным стилем
        st.markdown(f"""
        <div style="display: flex; justify-content: flex-end; margin-bottom: 15px;">
            <div class="chat-message-user">
                {prompt}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.session_state.ai_messages.append({"role": "user", "content": prompt})
        
        # Получаем ответ от HF AI
        with st.spinner("ZORNET думает..."):
            response = ask_hf_ai(prompt, st.session_state.ai_messages[-10:])  # Берём последние 10 сообщений
            st.session_state.ai_messages.append({"role": "assistant", "content": response})
        
        st.rerun()

    # Боковая панель с примерами вопросов
    with st.sidebar:
        st.markdown("### 💡 Примеры вопросов")

        example_questions = [
            "Напиши план развития для стартапа в IT",
            "Объясни квантовую физику простыми словами",
            "Помоги написать письмо отказ от сотрудничества",
            "Какие новейшие технологии в AI сейчас самые перспективные?",
            "Напиши код для простого веб-сайта на HTML/CSS",
            "Объясни разницу между Python и JavaScript",
            "Помоги составить резюме для разработчика",
            "Какие книги по саморазвитию ты можешь порекомендовать?"
        ]

        for question in example_questions:
            if st.button(question, key=f"ex_{question[:10]}", use_container_width=True):
                st.session_state.ai_messages.append({"role": "user", "content": question})
                st.rerun()

        st.markdown("---")

        # Очистка истории
        if st.button("🧹 Очистить историю", use_container_width=True):
            st.session_state.ai_messages = [
                {"role": "assistant", "content": "Привет! Я ZORNET AI. Чем могу помочь?"}
            ]
            st.rerun()
    
# =================================================
# СТРАНИЦА НОВОСТЕЙ
elif st.session_state.page == "Новости":
    st.markdown('<h1 style="color:#DAA520;">📰 Новости БелТА</h1>', unsafe_allow_html=True)
    
    # ВРЕМЕННО: заглушка для функции get_belta_news
    def get_belta_news():
        return [
            type('News', (), {'title': 'Тестовая новость 1', 'link': '#', 'published': '2024-01-01', 'summary': 'Тестовое описание'})()
        ]
    
    news = get_belta_news()
    if not news:
        st.info("Новости временно недоступны.")
    else:
        for entry in news:
            st.markdown(f"""
            <div style="
                background: #f8f9fa;
                border-left: 4px solid #DAA520;
                padding: 15px;
                margin-bottom: 15px;
                border-radius: 8px;
            ">
                <a href="{entry.link}" target="_blank" style="color:#DAA520; font-size:1.2rem; font-weight:bold; text-decoration:none;">{entry.title}</a><br>
                <small style="color:#666;">{getattr(entry, 'published', '')[:16]}</small>
                <p style="color:#1a1a1a; margin-top:10px;">{getattr(entry, 'summary', '')[:300]}...</p>
            </div>
            """, unsafe_allow_html=True)

# =================================================
# СТРАНИЦА ТРАНСПОРТА
elif st.session_state.page == "Транспорт":
    st.markdown('<div class="gold-title">🚌 ТРАНСПОРТ</div>', unsafe_allow_html=True)

    # Транспортные табы
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🚇 Метро", "🚌 Автобусы/Трамваи", "🚕 Такси",
        "🚂 Железная дорога", "✈️ Аэропорты", "🚗 Пробки", "🛣️ Маршруты"
    ])

    with tab1:
        st.subheader("Минское метро")
        stations = get_minsk_metro()
        for station in stations:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{station['name']}**")
            with col2:
                st.write(f"Линия {station['line']}")
            with col3:
                st.success(f"🚇 {station['next_train']}")

    with tab2:
        st.subheader("Автобусы и трамваи")
        routes = get_bus_trams()
        for route in routes:
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
        services = get_taxi_prices()
        for service in services:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{service['name']}**")
            with col2:
                st.write(f"💵 {service['price']}")
            with col3:
                st.write(f"🕒 {service['wait']}")

    with tab4:
        st.subheader("Белорусская железная дорога")
        trains = get_belarusian_railway()
        for train in trains:
            col1, col2, col3, col4 = st.columns([1, 2, 2, 2])
            with col1:
                st.write(f"**{train['number']}**")
            with col2:
                st.write(f"📍 {train['from']}")
            with col3:
                st.write(f"➡️ {train['to']}")
            with col4:
                st.write(f"🕒 {train['departure']} - {train['arrival']}")

    with tab5:
        st.subheader("Аэропорты Беларуси")
        airports = get_airport_info()
        for airport in airports:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{airport['name']}**")
            with col2:
                st.write(f"✈️ {airport['flights']}")
            with col3:
                st.success(f"✅ {airport['delays']}")

    with tab6:
        st.subheader("Пробки в городах")
        cities = get_traffic_jams()
        for city in cities:
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                st.write(f"**{city['city']}**")
            with col2:
                # Цветной индикатор пробок
                level = int(city['level'][0])
                if level <= 2:
                    color = "🟢"
                elif level <= 4:
                    color = "🟡"
                else:
                    color = "🔴"
                st.write(f"{color} {city['level']}")
            with col3:
                st.write(city['description'])

    with tab7:
        st.subheader("Построение маршрутов")
        col1, col2 = st.columns(2)
        with col1:
            start = st.text_input("Откуда", "Площадь Независимости")
        with col2:
            end = st.text_input("Куда", "Национальный аэропорт")

        if st.button("Построить маршрут"):
            routes = calculate_route(start, end)
            for route in routes:
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1:
                    st.write(f"**{route['type']}**")
                with col2:
                    st.write(f"🕒 {route['time']}")
                with col3:
                    st.write(f"📏 {route['distance']}")
                with col4:
                    st.write(f"💵 {route['price']}")

# =================================================
# СТРАНИЦА ДИСКА
# =================================================
elif st.session_state.page == "Диск":
    # Инициализация диска
    if 'disk_initialized' not in st.session_state:
        st.session_state.disk_initialized = True
        st.session_state.current_folder = 0
        st.session_state.folder_stack = [("Корневая папка", 0)]
        st.session_state.selected_items = set()
        st.session_state.view_mode = 'grid'
        init_disk_db()

    st.markdown('<div class="gold-title">💾 ZORNET DISK</div>', unsafe_allow_html=True)

    # Навигация по папкам
    if len(st.session_state.folder_stack) > 1:
        nav_items = st.session_state.folder_stack
        nav_html = '<div style="margin-bottom: 20px;">'
        for i, (name, folder_id) in enumerate(nav_items):
            nav_html += f'<span style="color: #666; font-size: 14px;">📁 {name}</span>'
            if i < len(nav_items) - 1:
                nav_html += '<span style="color: #ccc; font-size: 12px; margin: 0 5px;">›</span>'
        nav_html += '</div>'
        st.markdown(nav_html, unsafe_allow_html=True)

    # Панель действий
    cols = st.columns([1, 1, 1, 2, 1])

    with cols[0]:
        if st.button("📁 New Folder", key="new_folder_btn", use_container_width=True):
            with st.popover("Create New Folder", use_container_width=True):
                folder_name = st.text_input("Folder name:", "New Folder", key="folder_input")
                if st.button("Create", key="create_folder"):
                    if folder_name:
                        create_folder(folder_name, st.session_state.current_folder)
                        st.rerun()

    with cols[1]:
        uploaded_files = st.file_uploader(
            "Upload files",
            accept_multiple_files=True,
            key="main_uploader",
            label_visibility="collapsed"
        )
        if uploaded_files:
            progress_bar = st.progress(0)
            for i, uploaded_file in enumerate(uploaded_files):
                save_uploaded_file(uploaded_file, st.session_state.current_folder)
                progress_bar.progress((i + 1) / len(uploaded_files))
            st.rerun()

    with cols[2]:
        view_mode = st.selectbox(
            "View:",
            ["Grid View", "List View"],
            index=0 if st.session_state.view_mode == 'grid' else 1,
            label_visibility="collapsed"
        )
        st.session_state.view_mode = 'grid' if view_mode == "Grid View" else 'list'

    with cols[3]:
        search_query = st.text_input(
            "",
            placeholder="Search files and folders...",
            label_visibility="collapsed"
        )

    with cols[4]:
        if st.session_state.selected_items:
            if st.button(f"🗑️ Delete ({len(st.session_state.selected_items)})",
                         use_container_width=True, type="secondary"):
                for item_id in list(st.session_state.selected_items):
                    delete_file(item_id)
                st.session_state.selected_items = set()
                st.rerun()

    # Статистика использования диска
    used_space, total_space, usage_percent = get_disk_usage()

    st.markdown(f"""
    <div style="background: #f8f9fa; border-radius: 10px; padding: 20px; margin: 20px 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
            <div>
                <div style="font-weight: 600; color: #1a1a1a;">Storage Overview</div>
                <div style="font-size: 14px; color: #666;">{human_readable_size(used_space)} of {human_readable_size(total_space)} used</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 24px; font-weight: 700; color: #DAA520;">{usage_percent:.0f}%</div>
            </div>
        </div>
        <div style="background: rgba(212, 175, 55, 0.1); height: 6px; border-radius: 3px; overflow: hidden; margin: 10px 0;">
            <div style="background: linear-gradient(90deg, #DAA520, #F4D03F); height: 100%; width: {usage_percent}%; border-radius: 3px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Файлы и папки
    files = get_files_in_folder(st.session_state.current_folder)

    # Фильтрация по поиску
    if search_query:
        files = [f for f in files if search_query.lower() in f[1].lower()]

    if not files:
        st.markdown("""
        <div style="text-align: center; padding: 60px 20px; color: #666;">
            <div style="font-size: 48px; margin-bottom: 20px; opacity: 0.3;">📁</div>
            <h3>No files found</h3>
            <p>""" + (
            "Try a different search term" if search_query else "Upload files or create a new folder to get started") + """</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        if st.session_state.view_mode == 'grid':
            # Сетка
            cols = st.columns(4)
            for idx, file in enumerate(files):
                file_id, name, path, size, file_type, created_at, is_folder = file
                col_idx = idx % 4

                with cols[col_idx]:
                    # Определяем иконку
                    if is_folder:
                        icon = "📁"
                        bg_color = "rgba(212, 175, 55, 0.1)"
                    else:
                        icon_map = {
                            'pdf': '📄', 'doc': '📝', 'docx': '📝',
                            'xls': '📊', 'xlsx': '📊',
                            'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️',
                            'mp3': '🎵', 'wav': '🎵',
                            'mp4': '🎬', 'avi': '🎬', 'mov': '🎬',
                            'zip': '📦', 'rar': '📦',
                            'txt': '📃', 'py': '🐍'
                        }
                        icon = icon_map.get(file_type.lower() if file_type else '', '📄')
                        bg_color = "rgba(212, 175, 55, 0.08)"

                    # Форматирование
                    created_str = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%b %d")
                    size_str = human_readable_size(size) if size else ""

                    # Карточка
                    st.markdown(f"""
                    <div style="background: white; border: 1px solid rgba(0,0,0,0.08); border-radius: 12px; 
                                padding: 20px; text-align: center; margin-bottom: 15px; cursor: pointer;
                                transition: all 0.2s;"
                         onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.1)';"
                         onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='none';">
                        <div style="width: 50px; height: 50px; border-radius: 10px; background: {bg_color}; 
                                    display: flex; align-items: center; justify-content: center; margin: 0 auto 15px;
                                    color: #DAA520; font-size: 24px;">
                            {icon}
                        </div>
                        <div style="font-weight: 500; color: #1a1a1a; font-size: 14px; margin-bottom: 5px; 
                                    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{name}">
                            {name}
                        </div>
                        <div style="font-size: 12px; color: #888;">
                            {size_str} • {created_str}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Кнопки действий
                    if is_folder:
                        if st.button("📂 Open", key=f"open_{file_id}", use_container_width=True):
                            st.session_state.folder_stack.append((name, file_id))
                            st.session_state.current_folder = file_id
                            st.rerun()
                    else:
                        if os.path.exists(path):
                            with open(path, "rb") as f:
                                st.download_button(
                                    "📥 Download",
                                    data=f.read(),
                                    file_name=name,
                                    key=f"dl_{file_id}",
                                    use_container_width=True
                                )
        else:
            # Таблица
            st.markdown("""
            <style>
            .file-table {
                width: 100%;
                border-collapse: collapse;
            }
            .file-table th {
                background: rgba(212, 175, 55, 0.05);
                padding: 12px;
                text-align: left;
                font-weight: 600;
                color: #666;
                border-bottom: 1px solid rgba(0,0,0,0.1);
            }
            .file-table td {
                padding: 12px;
                border-bottom: 1px solid rgba(0,0,0,0.05);
            }
            .file-table tr:hover {
                background: rgba(212, 175, 55, 0.02);
            }
            </style>
            """, unsafe_allow_html=True)

            st.markdown("""
            <table class="file-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Size</th>
                        <th>Modified</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
            """, unsafe_allow_html=True)

            for file in files:
                file_id, name, path, size, file_type, created_at, is_folder = file

                # Иконка и тип
                icon = "📁" if is_folder else "📄"
                type_text = "Folder" if is_folder else (file_type.upper() if file_type else "File")

                # Форматирование
                size_str = human_readable_size(size) if size else "—"
                modified_str = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y")

                # Строка таблицы
                st.markdown(f"""
                <tr>
                    <td style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 18px;">{icon}</span>
                        <span style="font-weight: 500;">{name}</span>
                    </td>
                    <td>{type_text}</td>
                    <td>{size_str}</td>
                    <td>{modified_str}</td>
                    <td>
                """, unsafe_allow_html=True)

                # Кнопки действий
                col1, col2 = st.columns(2)
                with col1:
                    if is_folder:
                        if st.button("Open", key=f"t_open_{file_id}"):
                            st.session_state.folder_stack.append((name, file_id))
                            st.session_state.current_folder = file_id
                            st.rerun()
                    else:
                        if os.path.exists(path):
                            with open(path, "rb") as f:
                                st.download_button("Download", data=f.read(), file_name=name, key=f"t_dl_{file_id}")
                with col2:
                    if st.button("Delete", key=f"t_del_{file_id}", type="secondary"):
                        delete_file(file_id)
                        st.rerun()

                st.markdown('</td></tr>', unsafe_allow_html=True)

            st.markdown('</tbody></table>', unsafe_allow_html=True)

# =================================================
# СТРАНИЦА ПРОФИЛЯ
# =================================================
elif st.session_state.page == "Профиль":
    col_l, col_c, col_r = st.columns([1, 4, 1])

    with col_c:
        # Проверяем авторизацию
        if "google_creds" not in st.session_state:
            # ЭКРАН ВХОДА
            st.markdown('<div style="text-align: center; margin-bottom: 30px;">', unsafe_allow_html=True)
            st.markdown(
                '<div style="font-size: 36px; font-weight: 800; background: linear-gradient(to bottom, #DAA520, #B8860B); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 2px;">ZORNET</div>',
                unsafe_allow_html=True)
            st.markdown('<div style="color: #666; font-size: 16px; margin-top: 5px;">Зорнет ИИ</div>',
                        unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Карточка
            st.markdown(
                '<div style="background: white; border-radius: 20px; padding: 40px; box-shadow: 0 10px 40px rgba(0,0,0,0.1);">',
                unsafe_allow_html=True)

            # Переключатель
            if "auth_mode" not in st.session_state:
                st.session_state.auth_mode = "login"

            toggle_cols = st.columns(2)

            # Кнопка Вход
            if toggle_cols[0].button("Войти", key="tab_login", use_container_width=True,
                                     type="primary" if st.session_state.auth_mode == "login" else "secondary"):
                st.session_state.auth_mode = "login"
                st.rerun()

            # Кнопка Регистрация
            if toggle_cols[1].button("Регистрация", key="tab_reg", use_container_width=True,
                                     type="primary" if st.session_state.auth_mode == "register" else "secondary"):
                st.session_state.auth_mode = "register"
                st.rerun()

            # Поля ввода
            email = st.text_input("Email", key="auth_email")
            password = st.text_input("Пароль", type="password", key="auth_pass")

            if st.session_state.auth_mode == "register":
                confirm = st.text_input("Повторите пароль", type="password")

            st.write("")

            # ЗОЛОТАЯ КНОПКА
            btn_label = "Войти" if st.session_state.auth_mode == "login" else "Зарегистрироваться"
            if st.button(btn_label, use_container_width=True, type="primary"):
                st.success("Успешный вход!" if st.session_state.auth_mode == "login" else "Регистрация успешна!")

            # GOOGLE AUTH
            try:
                flow = Flow.from_client_secrets_file(
                    "client_secret.json",
                    scopes=SCOPES,
                    redirect_uri=REDIRECT_URI
                )
                auth_url, _ = flow.authorization_url(
                    access_type="offline",
                    include_granted_scopes="true",
                    prompt="select_account"
                )
                st.markdown(f"""
                <div style="text-align: center; margin-top: 20px;">
                    <a href="{auth_url}" target="_self" style="display: inline-flex; align-items: center; justify-content: center; 
                           width: 100%; padding: 12px; background: white; border: 1px solid #ddd; border-radius: 10px; 
                           text-decoration: none; color: #555; font-weight: 500; transition: all 0.2s;">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg" 
                             width="16" style="margin-right: 8px;">
                        Войти через Google
                    </a>
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.error("Ошибка конфигурации Google.")

            st.markdown('</div>', unsafe_allow_html=True)

        else:
            # АВТОРИЗОВАННЫЙ ПРОФИЛЬ
            # Данные пользователя
            user_info = {
                "name": "Пользователь",
                "email": "user@example.com",
                "date": datetime.datetime.now().strftime("%d/%m/%Y"),
                "letter": "U"
            }

            try:
                creds = st.session_state.google_creds
                if hasattr(creds, 'id_token') and creds.id_token:
                    import jwt

                    decoded = jwt.decode(creds.id_token, options={"verify_signature": False})
                    user_info["email"] = decoded.get('email', user_info["email"])
                    user_info["name"] = decoded.get('name', user_info["name"])
                    user_info["letter"] = user_info["name"][0].upper()
            except:
                pass

            st.markdown('<div style="text-align: center; margin-bottom: 30px;">', unsafe_allow_html=True)
            st.markdown(
                '<div style="font-size: 36px; font-weight: 800; background: linear-gradient(to bottom, #DAA520, #B8860B); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 2px;">ZORNET</div>',
                unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Карточка профиля
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #DAA520, #B8860B); border-radius: 16px; 
                        padding: 30px; max-width: 350px; margin: 0 auto; text-align: center; 
                        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);">
                <div style="width: 90px; height: 90px; border-radius: 50%; background-color: white; 
                            color: #B8860B; font-size: 40px; font-weight: bold; display: flex; 
                            justify-content: center; align-items: center; margin: 0 auto 20px;">
                    {user_info['letter']}
                </div>
                <div style="color: white; margin-bottom: 20px;">
                    <h2 style="color: white; margin-bottom: 10px;">{user_info['name']}</h2>
                    <a href="mailto:{user_info['email']}" style="color: white; text-decoration: none; 
                       font-size: 14px;">{user_info['email']}</a>
                    <p style="margin-top: 10px;">{user_info['date']}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.write("")

            col1, col2, col3 = st.columns([1, 4, 1])
            with col2:
                if st.button("Редактировать профиль", use_container_width=True, type="primary"):
                    st.info("В разработке")

                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

                if st.button("Выйти", type="secondary", use_container_width=True):
                    del st.session_state.google_creds
                    st.rerun()

# =================================================
# СТРАНИЦА КАМЕРЫ
# =================================================
elif st.session_state.page == "Камера":
    st.title("📷 Камера")

    # Кнопка для загрузки изображения
    uploaded_image = st.file_uploader("Выберите изображение", type=['jpg', 'jpeg', 'png'])

    # Или использовать камеру
    camera_image = st.camera_input("Снять фото")

    img_to_process = uploaded_image or camera_image

    if not vision_available:
        st.warning("📷 Камера временно недоступна на сервере")
        
        # Обработка изображения с помощью BLIP
        with st.spinner("Анализирую изображение..."):
            inputs = vision_processor(image, return_tensors="pt")
            out = vision_model.generate(**inputs, max_length=50)
            description = vision_processor.decode(out[0], skip_special_tokens=True)

        st.subheader("📝 Описание изображения:")
        st.write(description)

        # Сохранение изображения
        if st.button("💾 Сохранить в Диск"):
            # Сохраняем временно
            temp_path = "temp_image.jpg"
            image.save(temp_path)

            # Создаем файловый объект
            from io import BytesIO

            img_byte_arr = BytesIO()
            image.save(img_byte_arr, format='JPEG')
            img_byte_arr.seek(0)


            # Сохраняем в диск
            class UploadedFile:
                def __init__(self, name, data):
                    self.name = name
                    self.data = data

                def getbuffer(self):
                    return self.data.getvalue()

                @property
                def size(self):
                    return len(self.data.getvalue())


            uploaded_file = UploadedFile(
                name=f"photo_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
                data=img_byte_arr
            )

            if save_uploaded_file(uploaded_file):
                st.success("Изображение сохранено в Диск!")
                st.session_state.page = "Диск"
                st.rerun
