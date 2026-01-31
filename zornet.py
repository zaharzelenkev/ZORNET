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
import uuid
import re
import secrets
import hashlib
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

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
if "auth_step" not in st.session_state:
    st.session_state.auth_step = "login_start"
if "user_data" not in st.session_state:
    st.session_state.user_data = {}
if "user_photo" not in st.session_state:
    st.session_state.user_photo = None
if "disk_current_path" not in st.session_state:
    st.session_state.disk_current_path = "zornet_cloud"
if "disk_action" not in st.session_state:
    st.session_state.disk_action = "view"
if "auth_status" not in st.session_state:
    st.session_state.auth_status = "not_logged_in"
if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False

# ================= GOOGLE OAUTH НАСТРОЙКИ =================
GOOGLE_CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID", "ваш_клиент_ID")
GOOGLE_CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET", "ваш_клиент_секрет")
GOOGLE_REDIRECT_URI = st.secrets.get("GOOGLE_REDIRECT_URI", "http://localhost:8501")

# ================= ОБНОВЛЕННЫЕ CSS СТИЛИ (ТВОЙ ДИЗАЙН) =================
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
    
    /* Google Login Button */
    .google-login-btn {
        background: white !important;
        border: 2px solid #dee2e6 !important;
        color: #1a1a1a !important;
        padding: 15px 25px !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        width: 100% !important;
        margin: 10px 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 12px !important;
    }
    
    .google-login-btn:hover {
        border-color: #DAA520 !important;
        background: #f8f9fa !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= ФУНКЦИИ GOOGLE OAUTH =================
def verify_google_token(token):
    """Верифицирует Google ID токен"""
    try:
        # Замените YOUR_GOOGLE_CLIENT_ID на реальный ID из Google Cloud Console
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID)
        
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
        
        return idinfo
    except ValueError:
        return None

def get_google_auth_url():
    """Генерирует URL для авторизации через Google"""
    # Google OAuth 2.0 endpoint
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    
    # Параметры запроса
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
        "state": secrets.token_urlsafe(16)
    }
    
    # Собираем URL
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{auth_url}?{query_string}"

# ================= БАЗА ДАННЫХ =================
def init_db():
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    # Пользователи
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE,
            first_name TEXT,
            last_name TEXT,
            avatar TEXT,
            google_id TEXT UNIQUE,
            password_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Сообщения
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT,
            user_id INTEGER,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Комнаты
    c.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT UNIQUE,
            name TEXT,
            youtube_url TEXT,
            password_hash TEXT,
            owner_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()

def register_user(email, username, first_name, last_name, password=None, google_id=None, avatar=None):
    """Регистрация пользователя"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    try:
        password_hash = hashlib.sha256(password.encode()).hexdigest() if password else None
        
        c.execute("""
            INSERT INTO users (email, username, first_name, last_name, avatar, google_id, password_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (email, username, first_name, last_name, avatar, google_id, password_hash))
        
        conn.commit()
        return True
    except sqlite3.IntegrityError as e:
        print(f"Registration error: {e}")
        return False
    finally:
        conn.close()

def login_user(email, password):
    """Вход пользователя по email и паролю"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    c.execute("""
        SELECT id, email, username, first_name, last_name, avatar 
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
            "last_name": user[4],
            "avatar": user[5]
        }
    return None

def get_user_by_google_id(google_id):
    """Поиск пользователя по Google ID"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    c.execute("""
        SELECT id, email, username, first_name, last_name, avatar 
        FROM users 
        WHERE google_id = ?
    """, (google_id,))
    
    user = c.fetchone()
    conn.close()
    
    if user:
        return {
            "id": user[0],
            "email": user[1],
            "username": user[2],
            "first_name": user[3],
            "last_name": user[4],
            "avatar": user[5]
        }
    return None

def get_user_by_email(email):
    """Поиск пользователя по email"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    c.execute("""
        SELECT id, email, username, first_name, last_name, avatar 
        FROM users 
        WHERE email = ?
    """, (email,))
    
    user = c.fetchone()
    conn.close()
    
    if user:
        return {
            "id": user[0],
            "email": user[1],
            "username": user[2],
            "first_name": user[3],
            "last_name": user[4],
            "avatar": user[5]
        }
    return None

# ================= САЙДБАР =================
with st.sidebar:
    st.markdown("<h3 style='color:#DAA520;'>🇧🇾 ZORNET</h3>", unsafe_allow_html=True)
    
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
        if st.button(f"{icon} {text}", key=f"nav_{i}_{page}", use_container_width=True):
            st.session_state.page = page
            st.rerun()

# ================= ПРОВЕРКА АВТОРИЗАЦИИ =================
def check_auth():
    """Проверяет авторизацию пользователя"""
    if not st.session_state.is_logged_in:
        # Если не авторизован и не на странице входа
        if st.session_state.page not in ["Профиль", "Вход"]:
            st.session_state.page = "Профиль"
            st.rerun()
        return False
    return True

# ================= СТРАНИЦА ВХОДА/РЕГИСТРАЦИИ =================
if st.session_state.page == "Профиль" and not st.session_state.is_logged_in:
    st.markdown("""
    <style>
        .login-page {
            max-width: 500px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        
        .login-card {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            border: 1px solid #e0e0e0;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="gold-title">ZORNET ID</div>', unsafe_allow_html=True)
    
    # Получаем query параметры (для Google OAuth callback)
    query_params = st.experimental_get_query_params()
    
    # Если пришел код от Google
    if "code" in query_params:
        code = query_params["code"][0]
        
        # Здесь должен быть обмен кода на токен
        # Для демо просто создаем пользователя
        st.session_state.user_data = {
            "email": "zahar.zelenkevv@gmail.com",
            "first_name": "Захар",
            "last_name": "Зеленкевич",
            "username": "zahar_zornet"
        }
        st.session_state.is_logged_in = True
        st.session_state.auth_status = "logged_in"
        st.success("✅ Успешный вход через Google!")
        st.session_state.page = "Главная"
        st.rerun()
    
    # Если пользователь еще не выбрал метод входа
    if st.session_state.auth_step == "login_start":
        st.markdown('<div class="login-page">', unsafe_allow_html=True)
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style="text-align: center; margin-bottom: 30px;">
                <img src="https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_92x30dp.png" 
                     width="92" height="30" style="margin-bottom: 20px;">
                <h3 style="font-weight: 400; color: #202124;">Вход в ZORNET</h3>
                <p style="color: #5f6368;">Для доступа ко всем функциям</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Google OAuth button
            google_auth_url = get_google_auth_url()
            st.markdown(f"""
            <a href="{google_auth_url}" target="_self" style="text-decoration: none;">
                <div class="google-login-btn">
                    <svg width="20" height="20" viewBox="0 0 24 24">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                    </svg>
                    Войти через Google
                </div>
            </a>
            """, unsafe_allow_html=True)
            
            st.markdown('<div style="text-align: center; margin: 20px 0; color: #999;">или</div>', unsafe_allow_html=True)
            
            # Обычная форма входа
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="email@example.com")
                password = st.text_input("Пароль", type="password", placeholder="********")
                
                col_login, col_register = st.columns(2)
                with col_login:
                    login_submitted = st.form_submit_button("Войти", type="primary", use_container_width=True)
                with col_register:
                    register_clicked = st.form_submit_button("Регистрация", use_container_width=True)
                
                if login_submitted:
                    if email and password:
                        user = login_user(email, password)
                        if user:
                            st.session_state.user_data = user
                            st.session_state.is_logged_in = True
                            st.session_state.auth_status = "logged_in"
                            st.session_state.page = "Главная"
                            st.success("✅ Вход выполнен!")
                            st.rerun()
                        else:
                            st.error("Неверный email или пароль")
                    else:
                        st.error("Заполните все поля")
                
                if register_clicked:
                    st.session_state.auth_step = "register"
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Страница регистрации
    elif st.session_state.auth_step == "register":
        st.markdown('<div class="login-page">', unsafe_allow_html=True)
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        
        st.markdown("### Регистрация")
        
        with st.form("register_form"):
            col_name1, col_name2 = st.columns(2)
            with col_name1:
                first_name = st.text_input("Имя", placeholder="Иван")
            with col_name2:
                last_name = st.text_input("Фамилия", placeholder="Иванов")
            
            email = st.text_input("Email", placeholder="email@example.com")
            username = st.text_input("Никнейм (английскими буквами)", placeholder="ivan_zornet")
            
            avatar = st.file_uploader("Аватарка (необязательно)", type=['jpg', 'png', 'jpeg'])
            
            col_pass1, col_pass2 = st.columns(2)
            with col_pass1:
                password = st.text_input("Пароль", type="password", placeholder="********")
            with col_pass2:
                password_confirm = st.text_input("Повторите пароль", type="password", placeholder="********")
            
            col_submit, col_back = st.columns(2)
            with col_submit:
                register_submitted = st.form_submit_button("Создать аккаунт", type="primary", use_container_width=True)
            with col_back:
                back_clicked = st.form_submit_button("← Назад", use_container_width=True)
            
            if register_submitted:
                if not all([first_name, email, username, password, password_confirm]):
                    st.error("Заполните все обязательные поля")
                elif password != password_confirm:
                    st.error("Пароли не совпадают")
                elif len(password) < 6:
                    st.error("Пароль должен быть не менее 6 символов")
                else:
                    # Сохраняем аватар если есть
                    avatar_path = None
                    if avatar:
                        os.makedirs("avatars", exist_ok=True)
                        avatar_path = f"avatars/{username}_{int(datetime.datetime.now().timestamp())}.jpg"
                        with open(avatar_path, "wb") as f:
                            f.write(avatar.getbuffer())
                    
                    if register_user(email, username, first_name, last_name, password, None, avatar_path):
                        # Автоматически входим после регистрации
                        user = login_user(email, password)
                        if user:
                            st.session_state.user_data = user
                            st.session_state.is_logged_in = True
                            st.session_state.auth_status = "logged_in"
                            st.success("✅ Аккаунт успешно создан!")
                            st.session_state.page = "Главная"
                            st.rerun()
                    else:
                        st.error("Пользователь с таким email или никнеймом уже существует")
            
            if back_clicked:
                st.session_state.auth_step = "login_start"
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.stop()

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
    # Проверяем авторизацию
    if not check_auth():
        st.stop()
    
    st.markdown('<div class="gold-title">ZORNET</div>', unsafe_allow_html=True)
    
    current_time = datetime.datetime.now(pytz.timezone('Europe/Minsk')).strftime('%H:%M')
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.button(f"🕒 {current_time}\nМинск", use_container_width=True)
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
    
    st.markdown("---")
    
    # Информация о пользователе
    user = st.session_state.user_data
    st.info(f"👤 **{user.get('first_name', 'Пользователь')} {user.get('last_name', '')}** | ✉️ {user.get('email', '')} | 🆔 @{user.get('username', 'user')}")
    
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

# ================= МЕССЕНДЖЕР (Telegram стиль) =================
elif st.session_state.page == "Мессенджер":
    if not check_auth():
        st.stop()
    
    st.markdown('<div class="gold-title">💬 МЕССЕНДЖЕР</div>', unsafe_allow_html=True)
    
    # Telegram-like стили
    st.markdown("""
    <style>
        .messenger-container {
            display: flex;
            height: 700px;
            background: white;
            border-radius: 16px;
            border: 1px solid #e0e0e0;
            overflow: hidden;
        }
        
        .contacts-sidebar {
            width: 350px;
            border-right: 1px solid #e0e0e0;
            background: #f8f9fa;
            overflow-y: auto;
        }
        
        .chat-area {
            flex: 1;
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
            transition: background 0.2s;
        }
        
        .contact-item:hover {
            background: #e9ecef;
        }
        
        .contact-item.active {
            background: #e3f2fd;
        }
        
        .message-bubble {
            max-width: 70%;
            padding: 10px 14px;
            border-radius: 18px;
            margin-bottom: 8px;
            word-wrap: break-word;
        }
        
        .message-bubble.you {
            background: #DCF8C6;
            margin-left: auto;
            border-bottom-right-radius: 4px;
        }
        
        .message-bubble.other {
            background: white;
            margin-right: auto;
            border-bottom-left-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Контакты (в реальном приложении из БД)
    contacts = [
        {"id": 1, "name": "Марина", "last_msg": "Жду руководства", "time": "16:01", "unread": 2, "online": True},
        {"id": 2, "name": "Алексей", "last_msg": "Линукс слишком жесткий", "time": "16:01", "unread": 0, "online": True},
        {"id": 3, "name": "Ирина", "last_msg": "С октября где-то он", "time": "16:24", "unread": 0, "online": False},
        {"id": 4, "name": "Дмитрий", "last_msg": "Я еще ставлю его", "time": "16:06", "unread": 1, "online": True},
    ]
    
    # Две колонки: контакты и чат
    col_contacts, col_chat = st.columns([1, 2])
    
    with col_contacts:
        st.markdown("### Контакты")
        
        # Поиск контактов
        search_query = st.text_input("🔍 Поиск...", placeholder="Имя или сообщение")
        
        # Список контактов
        for contact in contacts:
            if search_query and search_query.lower() not in contact["name"].lower() and search_query.lower() not in contact["last_msg"].lower():
                continue
            
            is_active = st.session_state.get("current_chat_id") == contact["id"]
            
            st.markdown(f"""
            <div class="contact-item {'active' if is_active else ''}" 
                 onclick="window.location='?page=Мессенджер&chat={contact['id']}'">
                <div style="display: flex; justify-content: space-between;">
                    <div style="font-weight: 600; color: #333;">{contact['name']}</div>
                    <div style="font-size: 12px; color: #666;">{contact['time']}</div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                    <div style="font-size: 14px; color: #666; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        {contact['last_msg']}
                    </div>
                    {contact['unread'] > 0 and f'<div style="background: #DAA520; color: white; border-radius: 50%; width: 20px; height: 20px; text-align: center; line-height: 20px; font-size: 12px;">{contact["unread"]}</div>' or ''}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col_chat:
        if st.session_state.get("current_chat_id"):
            current_contact = next((c for c in contacts if c["id"] == st.session_state.current_chat_id), None)
            
            if current_contact:
                # Заголовок чата
                st.markdown(f"""
                <div class="chat-header">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="
                            width: 40px;
                            height: 40px;
                            border-radius: 50%;
                            background: linear-gradient(135deg, #DAA520, #B8860B);
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            color: white;
                            font-weight: bold;
                        ">
                            {current_contact['name'][0]}
                        </div>
                        <div>
                            <div style="font-weight: 600; font-size: 18px;">{current_contact['name']}</div>
                            <div style="font-size: 14px; color: #666;">
                                {current_contact['online'] and '🟢 онлайн' or '⚫ был(а) недавно'}
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Сообщения
                messages = [
                    {"sender": "other", "text": "Привет! Как дела?", "time": "16:01"},
                    {"sender": "you", "text": "Привет! Все отлично, работаю над ZORNET", "time": "16:02"},
                    {"sender": "other", "text": "Круто! Когда покажешь?", "time": "16:03"},
                    {"sender": "you", "text": "Скоро, сейчас финальные правки", "time": "16:04"},
                ]
                
                st.markdown('<div class="messages-container">', unsafe_allow_html=True)
                for msg in messages:
                    st.markdown(f"""
                    <div class="message-bubble {msg['sender']}">
                        <div>{msg['text']}</div>
                        <div style="font-size: 11px; color: #666; text-align: right; margin-top: 4px;">{msg['time']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Поле ввода
                new_message = st.text_input("💬 Введите сообщение...", key="chat_input", label_visibility="collapsed")
                
                col_send, col_attach, col_voice = st.columns([6, 1, 1])
                with col_send:
                    if st.button("Отправить", type="primary", use_container_width=True):
                        if new_message:
                            st.success("Сообщение отправлено!")
                            st.rerun()
                with col_attach:
                    st.button("📎", help="Прикрепить файл", use_container_width=True)
                with col_voice:
                    st.button("🎤", help="Голосовое сообщение", use_container_width=True)
        else:
            st.info("👈 Выберите чат из списка слева")

# ================= СОВМЕСТНЫЙ ПРОСМОТР =================
elif st.session_state.page == "Совместный просмотр":
    if not check_auth():
        st.stop()
    
    st.markdown('<div class="gold-title">🎬 СОВМЕСТНЫЙ ПРОСМОТР</div>', unsafe_allow_html=True)
    
    # Две колонки: создание комнаты и список комнат
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Создать комнату для просмотра")
        
        # URL видео
        video_url = st.text_input(
            "Ссылка на YouTube видео:",
            placeholder="https://www.youtube.com/watch?v=...",
            help="Вставьте ссылку на YouTube видео"
        )
        
        # Название комнаты
        room_name = st.text_input(
            "Название комнаты:",
            placeholder="Например: Фильм с друзьями",
            value="Моя комната"
        )
        
        # Пароль (обязательно)
        col_pass1, col_pass2 = st.columns(2)
        with col_pass1:
            room_password = st.text_input(
                "Пароль для комнаты:",
                type="password",
                placeholder="Обязательно",
                help="Без пароля комната не будет создана"
            )
        with col_pass2:
            confirm_password = st.text_input(
                "Подтвердите пароль:",
                type="password",
                placeholder="Повторите пароль"
            )
        
        # Кнопка создания
        if st.button("🎥 Создать комнату", type="primary", use_container_width=True):
            if video_url and room_name and room_password:
                if room_password != confirm_password:
                    st.error("Пароли не совпадают!")
                else:
                    # Генерируем ID комнаты
                    room_id = str(uuid.uuid4())[:8]
                    
                    # Извлекаем ID видео
                    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', video_url)
                    
                    if video_id_match:
                        video_id = video_id_match.group(1)
                        
                        # Сохраняем в сессии
                        st.session_state.rooms.append({
                            "id": room_id,
                            "name": room_name,
                            "video_id": video_id,
                            "password": room_password,
                            "owner": st.session_state.user_data.get("username", "Гость"),
                            "created": datetime.datetime.now().strftime("%H:%M"),
                            "users": [st.session_state.user_data.get("username", "Гость")]
                        })
                        
                        st.success(f"Комната '{room_name}' создана!")
                        
                        # Показываем ссылку
                        st.markdown(f"**ID комнаты:** `{room_id}`")
                        st.markdown(f"**Пароль:** `{room_password}`")
                        
                        # Кнопка для перехода в комнату
                        if st.button("▶️ Перейти в комнату"):
                            st.session_state.watch_room = room_id
                            st.rerun()
                    else:
                        st.error("Неверная ссылка на YouTube видео")
            else:
                st.error("Заполните все поля, включая пароль!")
    
    with col2:
        st.markdown("### Присоединиться к комнате")
        
        join_room_id = st.text_input("ID комнаты:", placeholder="Введите ID комнаты")
        join_password = st.text_input("Пароль:", type="password", placeholder="Введите пароль")
        
        if st.button("🔗 Присоединиться", use_container_width=True):
            if join_room_id and join_password:
                # Ищем комнату
                room_found = False
                for room in st.session_state.rooms:
                    if room["id"] == join_room_id:
                        if room.get("password") == join_password:
                            # Добавляем пользователя в комнату
                            if st.session_state.user_data.get("username") not in room["users"]:
                                room["users"].append(st.session_state.user_data.get("username", "Гость"))
                            
                            st.session_state.watch_room = room["id"]
                            st.success("Вы присоединились к комнате!")
                            st.rerun()
                        else:
                            st.error("Неверный пароль")
                        room_found = True
                        break
                
                if not room_found:
                    st.error("Комната не найдена")
            else:
                st.error("Введите ID комнаты и пароль")
        
        st.markdown("---")
        st.markdown("#### Активные комнаты")
        
        if st.session_state.rooms:
            for room in st.session_state.rooms[-3:]:  # Последние 3 комнаты
                st.markdown(f"""
                <div style="background: #f8f9fa; padding: 10px; border-radius: 8px; margin: 5px 0; border-left: 3px solid #DAA520;">
                    <b>{room['name']}</b><br>
                    <small>Создал: {room['owner']}</small><br>
                    <small>👥 {len(room['users'])} участников</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("🎬 Пока нет активных комнат")
    
    # Если выбрана комната, показываем плеер
    if st.session_state.get("watch_room"):
        st.markdown("---")
        st.markdown("### 🎥 Комната для совместного просмотра")
        
        # Получаем данные комнаты
        current_room = None
        for room in st.session_state.rooms:
            if room["id"] == st.session_state.watch_room:
                current_room = room
                break
        
        if current_room:
            st.markdown(f"**Комната:** {current_room['name']}")
            st.markdown(f"**Владелец:** {current_room['owner']}")
            st.markdown(f"**Участники:** {', '.join(current_room['users'])}")
            
            # YouTube плеер с синхронизацией
            components.html(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ 
                        margin: 0; 
                        padding: 20px; 
                        background: white;
                        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                    }}
                    .watch-container {{
                        max-width: 1000px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 16px;
                        overflow: hidden;
                        border: 1px solid #e0e0e0;
                    }}
                    .chat-messages {{
                        height: 300px;
                        overflow-y: auto;
                        padding: 20px;
                        background: #f8f9fa;
                        border-top: 1px solid #e0e0e0;
                    }}
                    .message {{
                        margin-bottom: 12px;
                        padding: 10px 14px;
                        border-radius: 18px;
                        max-width: 80%;
                        word-wrap: break-word;
                    }}
                    .message-you {{
                        background: #DCF8C6;
                        margin-left: auto;
                        border-bottom-right-radius: 4px;
                    }}
                    .message-other {{
                        background: white;
                        margin-right: auto;
                        border-bottom-left-radius: 4px;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    }}
                </style>
            </head>
            <body>
                <div class="watch-container">
                    <!-- YouTube плеер -->
                    <iframe 
                        width="100%" 
                        height="500" 
                        src="https://www.youtube.com/embed/{current_room['video_id']}?autoplay=1&controls=1&modestbranding=1"
                        frameborder="0" 
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                        allowfullscreen
                        style="border-bottom: 1px solid #e0e0e0;">
                    </iframe>
                    
                    <!-- Чат комнаты -->
                    <div style="padding: 20px; background: white;">
                        <h3 style="margin: 0 0 15px 0; color: #333;">💬 Чат комнаты</h3>
                        
                        <div class="chat-messages" id="chatMessages">
                            <div class="message message-other">
                                <div style="font-weight: 600; color: #DAA520;">{current_room['owner']}</div>
                                <div>Добро пожаловать в комнату!</div>
                                <div style="font-size: 12px; color: #666; text-align: right;">{current_room['created']}</div>
                            </div>
                        </div>
                        
                        <div style="display: flex; gap: 10px; margin-top: 15px;">
                            <input type="text" id="chatInput" 
                                   placeholder="Напишите сообщение..." 
                                   style="
                                        flex: 1;
                                        padding: 12px 16px;
                                        border: 2px solid #e0e0e0;
                                        border-radius: 25px;
                                        outline: none;
                                        font-size: 14px;
                                   ">
                            <button onclick="sendMessage()" style="
                                background: #DAA520;
                                color: white;
                                border: none;
                                border-radius: 25px;
                                padding: 0 24px;
                                font-weight: 600;
                                cursor: pointer;
                                transition: background 0.2s;
                            ">
                                Отправить
                            </button>
                        </div>
                    </div>
                </div>
                
                <script>
                    function sendMessage() {{
                        var input = document.getElementById('chatInput');
                        var message = input.value.trim();
                        
                        if (message) {{
                            var chat = document.getElementById('chatMessages');
                            var newMsg = document.createElement('div');
                            newMsg.className = 'message message-you';
                            newMsg.innerHTML = `
                                <div style="font-weight: 600; color: #333;">Вы</div>
                                <div>${{message}}</div>
                                <div style="font-size: 12px; color: #666; text-align: right;">${{new Date().toLocaleTimeString([], {{hour: '2-digit', minute:'2-digit'}})}}</div>
                            `;
                            chat.appendChild(newMsg);
                            input.value = '';
                            chat.scrollTop = chat.scrollHeight;
                        }}
                    }}
                    
                    // Автофокус на поле ввода
                    document.getElementById('chatInput').focus();
                    
                    // Отправка по Enter
                    document.getElementById('chatInput').addEventListener('keypress', function(e) {{
                        if (e.key === 'Enter') {{
                            sendMessage();
                        }}
                    }});
                </script>
            </body>
            </html>
            """, height=900)
        
        # Кнопка выхода из комнаты
        if st.button("← Выйти из комнаты", use_container_width=True):
            st.session_state.watch_room = None
            st.rerun()

# ================= СТРАНИЦА ДИСКА =================
elif st.session_state.page == "Диск":
    if not check_auth():
        st.stop()
    
    st.markdown('<div class="gold-title">💾 ДИСК</div>', unsafe_allow_html=True)
    
    # Проверка авторизации для диска
    if st.session_state.auth_status != "logged_in":
        st.warning("⚠️ Чтобы пользоваться диском войдите в ZORNET ID")
        if st.button("Перейти в профиль для входа"):
            st.session_state.page = "Профиль"
            st.rerun()
        st.stop()
    
    # Создаем уникальный путь для текущего пользователя
    user_email = st.session_state.user_data.get('email', 'anonymous')
    user_folder_name = "".join(filter(str.isalnum, user_email))
    user_base_path = os.path.join("zornet_storage", user_folder_name)
    
    # Если путь еще не задан — обновляем
    if not st.session_state.disk_current_path.startswith(user_base_path):
        st.session_state.disk_current_path = user_base_path
    
    # Физически создаем папку пользователя на сервере
    os.makedirs(st.session_state.disk_current_path, exist_ok=True)
    
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
    
    # Функции для работы с диском
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
    
    # СТАТИСТИКА ХРАНИЛИЩА
    stats = get_disk_stats()
    used_gb = stats['total_size'] / (1024 * 1024 * 1024)
    used_percent = min(100, (used_gb / 1.0) * 100)  # 1GB лимит
    
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
        # ОСНОВНОЙ РЕЖИМ ПРОСМОТРА ФАЙЛОВ
        st.markdown("### 📁 Файлы и папки")
        
        # Быстрая загрузка
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
        if st.session_state.disk_current_path != user_base_path:
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

# ================= СТРАНИЦА НОВОСТЕЙ =================
elif st.session_state.page == "Новости":
    if not check_auth():
        st.stop()
    
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
    if not check_auth():
        st.stop()
    
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

# ================= ИНИЦИАЛИЗАЦИЯ =================
if __name__ == "__main__":
    init_db()
    init_disk_db()
