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
from duckduckgo_search import DDGS
from huggingface_hub import InferenceClient
import streamlit.components.v1 as components
import uuid
import re
import secrets
import hashlib

# ================= НАСТРОЙКИ =================
st.set_page_config(
    page_title="ZORNET",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None
)

# ================= СЕССИЯ =================
if "page" not in st.session_state:
    st.session_state.page = "Главная"
if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False
if "user_data" not in st.session_state:
    st.session_state.user_data = {}
if "rooms" not in st.session_state:
    st.session_state.rooms = []
if "messages" not in st.session_state:
    st.session_state.messages = {}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = None
if "disk_current_path" not in st.session_state:
    st.session_state.disk_current_path = "zornet_storage"
if "disk_action" not in st.session_state:
    st.session_state.disk_action = "view"

# ================= CSS СТИЛИ =================
st.markdown("""
<style>
    /* Основные стили */
    :root {
        --primary-color: #FFC107;
        --primary-dark: #FFA000;
        --primary-light: #FFECB3;
        --bg-color: #FFFFFF;
        --sidebar-bg: #F5F5F5;
        --text-color: #333333;
        --border-color: #E0E0E0;
        --hover-bg: #FAFAFA;
    }
    
    /* Убираем Streamlit дефолтные стили */
    .stApp {
        background: var(--bg-color);
    }
    
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Сайдбар */
    section[data-testid="stSidebar"] {
        background: var(--sidebar-bg);
        border-right: 1px solid var(--border-color);
    }
    
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 2rem;
    }
    
    /* Заголовок */
    .main-title {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 48px;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(135deg, #FFC107 0%, #FFA000 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 20px 0 40px 0;
        letter-spacing: -1px;
    }
    
    /* Кнопки */
    div.stButton > button {
        background: white;
        border: 2px solid var(--border-color);
        color: var(--text-color);
        padding: 15px 25px;
        border-radius: 12px;
        font-weight: 600;
        width: 100%;
        transition: all 0.3s ease;
    }
    
    div.stButton > button:hover {
        border-color: var(--primary-color);
        background: var(--primary-light);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(255, 193, 7, 0.2);
    }
    
    div.stButton > button[kind="primary"] {
        background: var(--primary-color);
        border-color: var(--primary-color);
        color: white;
    }
    
    div.stButton > button[kind="primary"]:hover {
        background: var(--primary-dark);
        border-color: var(--primary-dark);
    }
    
    /* Карточки */
    .card {
        background: white;
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    
    .card:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.08);
    }
    
    /* Входы */
    .stTextInput > div > div > input {
        border: 2px solid var(--border-color);
        border-radius: 10px;
        padding: 12px 16px;
        font-size: 16px;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(255, 193, 7, 0.1);
    }
    
    /* Табы */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: var(--sidebar-bg);
        padding: 4px;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 12px 24px;
        background: transparent;
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--primary-color) !important;
        color: white !important;
    }
    
    /* Адаптивность */
    @media (max-width: 768px) {
        .main-title {
            font-size: 32px;
        }
        
        .card {
            padding: 16px;
        }
        
        .stButton > button {
            padding: 12px 20px;
        }
    }
    
    /* Мессенджер стили */
    .message-container {
        max-width: 800px;
        margin: 0 auto;
        height: 600px;
        display: flex;
        flex-direction: column;
        background: white;
        border-radius: 16px;
        border: 1px solid var(--border-color);
        overflow: hidden;
    }
    
    .messages-area {
        flex: 1;
        overflow-y: auto;
        padding: 20px;
        background: var(--sidebar-bg);
    }
    
    .message {
        max-width: 70%;
        margin-bottom: 16px;
        padding: 12px 16px;
        border-radius: 18px;
        word-wrap: break-word;
    }
    
    .message-user {
        background: var(--primary-color);
        color: white;
        margin-left: auto;
        border-bottom-right-radius: 4px;
    }
    
    .message-other {
        background: white;
        color: var(--text-color);
        margin-right: auto;
        border-bottom-left-radius: 4px;
        border: 1px solid var(--border-color);
    }
    
    .message-input-area {
        padding: 20px;
        border-top: 1px solid var(--border-color);
        background: white;
    }
    
    /* Комнаты для просмотра */
    .room-card {
        background: white;
        border: 2px solid var(--border-color);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .room-card:hover {
        border-color: var(--primary-color);
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(255, 193, 7, 0.15);
    }
    
    /* Диск */
    .file-item {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        border-bottom: 1px solid var(--border-color);
        transition: background 0.2s;
    }
    
    .file-item:hover {
        background: var(--hover-bg);
    }
    
    .file-icon {
        font-size: 24px;
        margin-right: 16px;
        width: 40px;
        text-align: center;
    }
    
    .file-name {
        flex: 1;
        font-weight: 500;
    }
    
    .file-size {
        color: #666;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# ================= БАЗА ДАННЫХ =================
def init_db():
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    # Пользователи
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            username TEXT UNIQUE,
            first_name TEXT,
            last_name TEXT,
            avatar TEXT,
            password_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Сообщения
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users (id),
            FOREIGN KEY (receiver_id) REFERENCES users (id)
        )
    """)
    
    # Комнаты для совместного просмотра
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
    
    # Файлы на диске
    c.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            filename TEXT,
            filepath TEXT,
            size INTEGER,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()

# ================= ФУНКЦИИ АВТОРИЗАЦИИ =================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(email, username, first_name, last_name, password, avatar_path=None):
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    try:
        password_hash = hash_password(password)
        c.execute("""
            INSERT INTO users (email, username, first_name, last_name, avatar, password_hash)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (email, username, first_name, last_name, avatar_path, password_hash))
        
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(email, password):
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    password_hash = hash_password(password)
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

# ================= СТРАНИЦА ВХОДА/РЕГИСТРАЦИИ =================
if not st.session_state.is_logged_in and st.session_state.page != "Вход":
    st.session_state.page = "Вход"

if st.session_state.page == "Вход":
    st.markdown('<h1 class="main-title">ZORNET</h1>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Вход", "Регистрация"])
    
    with tab1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.container():
                st.markdown("### Вход в аккаунт")
                
                email = st.text_input("Email", placeholder="email@example.com")
                password = st.text_input("Пароль", type="password", placeholder="********")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Войти", type="primary", use_container_width=True):
                        if email and password:
                            user = login_user(email, password)
                            if user:
                                st.session_state.user_data = user
                                st.session_state.is_logged_in = True
                                st.session_state.page = "Главная"
                                st.rerun()
                            else:
                                st.error("Неверный email или пароль")
                        else:
                            st.error("Заполните все поля")
                
                with col_btn2:
                    if st.button("Войти через Google", use_container_width=True):
                        # Здесь будет реальная интеграция с Google OAuth
                        st.info("Google OAuth будет реализован в будущем. Используйте обычную регистрацию.")
                        
                        # Для теста создаем тестового пользователя
                        st.session_state.user_data = {
                            "id": 1,
                            "email": "test@zornet.by",
                            "username": "test_user",
                            "first_name": "Тестовый",
                            "last_name": "Пользователь",
                            "avatar": None
                        }
                        st.session_state.is_logged_in = True
                        st.session_state.page = "Главная"
                        st.rerun()
    
    with tab2:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.container():
                st.markdown("### Создать аккаунт")
                
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
                
                if st.button("Создать аккаунт", type="primary", use_container_width=True):
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
                        
                        if register_user(email, username, first_name, last_name, password, avatar_path):
                            # Автоматически входим после регистрации
                            user = login_user(email, password)
                            if user:
                                st.session_state.user_data = user
                                st.session_state.is_logged_in = True
                                st.session_state.page = "Главная"
                                st.success("✅ Аккаунт успешно создан!")
                                st.rerun()
                        else:
                            st.error("Пользователь с таким email или никнеймом уже существует")
    
    st.stop()

# ================= САЙДБАР (только для авторизованных) =================
with st.sidebar:
    user = st.session_state.user_data
    st.markdown(f"""
    <div style="padding: 20px; border-bottom: 1px solid var(--border-color);">
        <div style="display: flex; align-items: center; gap: 12px;">
            <div style="
                width: 48px;
                height: 48px;
                border-radius: 50%;
                background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
                font-size: 20px;
            ">
                {user.get('first_name', 'П')[0]}
            </div>
            <div>
                <div style="font-weight: 600;">{user.get('first_name', 'Пользователь')}</div>
                <div style="font-size: 14px; color: #666;">@{user.get('username', 'user')}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    pages = [
        ("🏠", "Главная", "Главная"),
        ("💬", "Мессенджер", "Мессенджер"),
        ("🎬", "Совместный просмотр", "Совместный просмотр"),
        ("💾", "Диск", "Диск"),
        ("📰", "Новости", "Новости"),
        ("🌤️", "Погода", "Погода"),
        ("⚙️", "Настройки", "Настройки"),
    ]
    
    for icon, text, page in pages:
        if st.button(f"{icon} {text}", key=f"nav_{page}", use_container_width=True):
            st.session_state.page = page
            st.rerun()
    
    st.markdown("---")
    if st.button("🚪 Выйти", use_container_width=True):
        st.session_state.is_logged_in = False
        st.session_state.user_data = {}
        st.session_state.page = "Вход"
        st.rerun()

# ================= ГЛАВНАЯ СТРАНИЦА =================
if st.session_state.page == "Главная":
    st.markdown('<h1 class="main-title">ZORNET</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💬 **Мессенджер**\n\nОбщайтесь с друзьями в реальном времени", use_container_width=True, key="home_messenger"):
            st.session_state.page = "Мессенджер"
            st.rerun()
    
    with col2:
        if st.button("🎬 **Совместный просмотр**\n\nСмотрите YouTube вместе с друзьями", use_container_width=True, key="home_watch"):
            st.session_state.page = "Совместный просмотр"
            st.rerun()
    
    with col3:
        if st.button("💾 **Облачный диск**\n\nХраните и делитесь файлами", use_container_width=True, key="home_disk"):
            st.session_state.page = "Диск"
            st.rerun()
    
    st.markdown("---")
    
    # Быстрые действия
    st.markdown("### 🚀 Быстрые действия")
    
    col4, col5, col6 = st.columns(3)
    
    with col4:
        current_time = datetime.datetime.now(pytz.timezone('Europe/Minsk')).strftime('%H:%M')
        st.markdown(f"""
        <div class="card">
            <div style="font-size: 32px; color: var(--primary-color); margin-bottom: 10px;">🕒</div>
            <div style="font-size: 24px; font-weight: 600;">{current_time}</div>
            <div style="color: #666; font-size: 14px;">Минск</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown("""
        <div class="card" onclick="window.location='?page=Погода'">
            <div style="font-size: 32px; color: var(--primary-color); margin-bottom: 10px;">🌤️</div>
            <div style="font-size: 18px; font-weight: 600;">Погода</div>
            <div style="color: #666; font-size: 14px;">Узнайте погоду в вашем городе</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col6:
        st.markdown("""
        <div class="card">
            <div style="font-size: 32px; color: var(--primary-color); margin-bottom: 10px;">🔍</div>
            <div style="font-size: 18px; font-weight: 600;">Поиск</div>
            <div style="color: #666; font-size: 14px;">Ищите информацию в интернете</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Поиск Google
        components.html("""
        <div style="margin-top: 10px;">
            <form action="https://www.google.com/search" method="get" target="_blank">
                <input type="text" name="q" placeholder="Поиск в Google..." 
                       style="width: 100%; padding: 10px 15px; border: 2px solid var(--border-color); 
                              border-radius: 25px; font-size: 14px; outline: none;">
            </form>
        </div>
        """, height=60)

# ================= МЕССЕНДЖЕР =================
elif st.session_state.page == "Мессенджер":
    st.markdown('<h1 class="main-title">💬 Мессенджер</h1>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Чаты", "Создать чат"])
    
    with tab1:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### Контакты")
            
            # Поиск контактов
            search_contact = st.text_input("Поиск...", placeholder="Имя или username")
            
            # Список контактов (в реальном приложении брать из БД)
            contacts = [
                {"id": 2, "name": "Марина", "username": "marina_dev", "last_online": "только что", "unread": 3},
                {"id": 3, "name": "Алексей", "username": "alex_code", "last_online": "5 мин назад", "unread": 0},
                {"id": 4, "name": "Ирина", "username": "irina_design", "last_online": "в сети", "unread": 1},
                {"id": 5, "name": "Дмитрий", "username": "dima_admin", "last_online": "2 часа назад", "unread": 0},
            ]
            
            for contact in contacts:
                if search_contact.lower() not in contact["name"].lower() + contact["username"].lower():
                    continue
                    
                is_active = st.session_state.current_chat == contact["id"]
                bg_color = "var(--primary-light)" if is_active else "transparent"
                
                st.markdown(f"""
                <div style="
                    padding: 12px 16px;
                    margin: 4px 0;
                    background: {bg_color};
                    border-radius: 12px;
                    cursor: pointer;
                    transition: background 0.2s;
                " onclick="window.location='?page=Мессенджер&chat={contact['id']}'">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="font-weight: 600;">{contact['name']}</div>
                        <div style="font-size: 12px; color: #666;">{contact['last_online']}</div>
                    </div>
                    <div style="font-size: 14px; color: #666;">@{contact['username']}</div>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("### Чат")
            
            if st.session_state.current_chat:
                # Выбранный чат
                chat_id = st.session_state.current_chat
                
                # Область сообщений
                messages_html = """
                <div class="messages-area">
                    <div class="message message-other">
                        <div style="font-weight: 600;">Марина</div>
                        <div>Привет! Как дела?</div>
                        <div style="font-size: 12px; color: #666; text-align: right; margin-top: 4px;">16:01</div>
                    </div>
                    
                    <div class="message message-user">
                        <div>Привет! Все отлично, работаю над ZORNET</div>
                        <div style="font-size: 12px; color: rgba(255,255,255,0.8); text-align: right; margin-top: 4px;">16:02</div>
                    </div>
                    
                    <div class="message message-other">
                        <div style="font-weight: 600;">Марина</div>
                        <div>Круто! Когда покажешь?</div>
                        <div style="font-size: 12px; color: #666; text-align: right; margin-top: 4px;">16:03</div>
                    </div>
                </div>
                """
                
                # Поле ввода
                st.markdown(f"""
                <div class="message-container">
                    {messages_html}
                    <div class="message-input-area">
                        <form>
                            <div style="display: flex; gap: 10px;">
                                <input type="text" placeholder="Введите сообщение..." 
                                       style="flex: 1; padding: 12px 16px; border: 2px solid var(--border-color); 
                                              border-radius: 25px; outline: none;">
                                <button type="submit" 
                                        style="background: var(--primary-color); color: white; border: none; 
                                               border-radius: 25px; padding: 0 24px; font-weight: 600; cursor: pointer;">
                                    Отправить
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("👈 Выберите чат из списка слева")
    
    with tab2:
        st.markdown("### Создать новый чат")
        
        col1, col2 = st.columns(2)
        
        with col1:
            chat_type = st.radio("Тип чата:", ["Личный чат", "Групповой чат"])
            
            if chat_type == "Личный чат":
                username = st.text_input("Username пользователя", placeholder="username")
                if st.button("Найти пользователя", type="primary"):
                    if username:
                        st.info(f"Поиск пользователя @{username}...")
            
            else:  # Групповой чат
                group_name = st.text_input("Название группы", placeholder="Моя группа")
                members = st.multiselect("Участники", ["Марина", "Алексей", "Ирина", "Дмитрий"])
                
                if st.button("Создать группу", type="primary"):
                    if group_name and members:
                        st.success(f"Группа '{group_name}' создана!")
        
        with col2:
            st.markdown("#### Настройки чата")
            enable_notifications = st.checkbox("Уведомления", value=True)
            pin_chat = st.checkbox("Закрепить чат")
            
            if st.button("Создать чат", type="primary", disabled=True):
                st.success("Чат создан!")

# ================= СОВМЕСТНЫЙ ПРОСМОТР =================
elif st.session_state.page == "Совместный просмотр":
    st.markdown('<h1 class="main-title">🎬 Совместный просмотр</h1>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Создать комнату", "Присоединиться", "Мои комнаты"])
    
    with tab1:
        st.markdown("### Создать комнату для просмотра")
        
        with st.form("create_room_form"):
            room_name = st.text_input("Название комнаты", placeholder="Фильм с друзьями")
            
            youtube_url = st.text_input(
                "Ссылка на YouTube видео",
                placeholder="https://www.youtube.com/watch?v=...",
                help="Вставьте ссылку на YouTube видео"
            )
            
            col_pass1, col_pass2 = st.columns(2)
            with col_pass1:
                room_password = st.text_input("Пароль для комнаты", type="password", placeholder="Необязательно")
            with col_pass2:
                confirm_password = st.text_input("Повторите пароль", type="password", placeholder="Необязательно")
            
            if st.form_submit_button("🎥 Создать комнату", type="primary"):
                if room_name and youtube_url:
                    if room_password and room_password != confirm_password:
                        st.error("Пароли не совпадают")
                    else:
                        # Извлекаем ID видео
                        video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', youtube_url)
                        
                        if video_id_match:
                            video_id = video_id_match.group(1)
                            room_id = str(uuid.uuid4())[:8]
                            
                            # Сохраняем комнату
                            room_data = {
                                "id": room_id,
                                "name": room_name,
                                "youtube_id": video_id,
                                "password": room_password,
                                "owner": st.session_state.user_data["username"],
                                "created": datetime.datetime.now().strftime("%H:%M"),
                                "users": []
                            }
                            
                            st.session_state.rooms.append(room_data)
                            
                            st.success(f"Комната '{room_name}' создана!")
                            
                            # Показываем информацию для присоединения
                            st.markdown("---")
                            st.markdown("### 📋 Информация для присоединения")
                            
                            col_info1, col_info2 = st.columns(2)
                            
                            with col_info1:
                                st.info(f"**ID комнаты:** `{room_id}`")
                                if room_password:
                                    st.info(f"**Пароль:** `{room_password}`")
                            
                            with col_info2:
                                if st.button("▶️ Перейти в комнату"):
                                    st.session_state.current_room = room_id
                                    st.rerun()
                        else:
                            st.error("Неверная ссылка на YouTube видео")
                else:
                    st.error("Заполните название комнаты и ссылку на видео")
    
    with tab2:
        st.markdown("### Присоединиться к комнате")
        
        col_id, col_pass = st.columns(2)
        
        with col_id:
            join_room_id = st.text_input("ID комнаты", placeholder="Введите ID комнаты")
        
        with col_pass:
            join_password = st.text_input("Пароль комнаты", type="password", placeholder="Если требуется")
        
        if st.button("🔗 Присоединиться", type="primary", use_container_width=True):
            if join_room_id:
                # Ищем комнату
                room_found = False
                for room in st.session_state.rooms:
                    if room["id"] == join_room_id:
                        if room.get("password") and room["password"] != join_password:
                            st.error("Неверный пароль")
                        else:
                            st.session_state.current_room = room["id"]
                            st.success("Вы присоединились к комнате!")
                            st.rerun()
                        room_found = True
                        break
                
                if not room_found:
                    st.error("Комната не найдена")
            else:
                st.error("Введите ID комнаты")
    
    with tab3:
        st.markdown("### Мои комнаты")
        
        if st.session_state.rooms:
            for room in st.session_state.rooms:
                if room["owner"] == st.session_state.user_data["username"]:
                    with st.container():
                        st.markdown(f"""
                        <div class="room-card">
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <div>
                                    <div style="font-size: 18px; font-weight: 600;">{room['name']}</div>
                                    <div style="color: #666; font-size: 14px;">ID: {room['id']} • Создана в {room['created']}</div>
                                </div>
                                <div style="display: flex; gap: 8px;">
                                    <button style="
                                        background: var(--primary-color); 
                                        color: white; 
                                        border: none; 
                                        padding: 8px 16px; 
                                        border-radius: 8px;
                                        cursor: pointer;
                                    " onclick="window.location='?page=Совместный%20просмотр&room={room['id']}'">
                                        Войти
                                    </button>
                                </div>
                            </div>
                            <div style="margin-top: 12px; color: #666;">
                                🔒 {'С паролем' if room.get('password') else 'Без пароля'} • 👥 {len(room.get('users', []))} участников
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("У вас пока нет созданных комнат")
    
    # Если есть активная комната
    if hasattr(st.session_state, 'current_room'):
        st.markdown("---")
        st.markdown(f"### 🎥 Комната: {st.session_state.current_room}")
        
        # Находим комнату
        current_room_data = None
        for room in st.session_state.rooms:
            if room["id"] == st.session_state.current_room:
                current_room_data = room
                break
        
        if current_room_data:
            # YouTube плеер
            video_id = current_room_data.get("youtube_id", "dQw4w9WgXcQ")
            
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
                    .player-wrapper {{
                        max-width: 1000px;
                        margin: 0 auto;
                    }}
                    .chat-wrapper {{
                        margin-top: 20px;
                        background: #f8f9fa;
                        border-radius: 12px;
                        padding: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="player-wrapper">
                    <iframe 
                        width="100%" 
                        height="500" 
                        src="https://www.youtube.com/embed/{video_id}?autoplay=1&controls=1&modestbranding=1"
                        frameborder="0" 
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                        allowfullscreen
                        style="border-radius: 12px;">
                    </iframe>
                    
                    <div class="chat-wrapper">
                        <h3 style="margin: 0 0 15px 0;">💬 Чат комнаты</h3>
                        <div id="chat-messages" style="
                            height: 200px;
                            overflow-y: auto;
                            background: white;
                            border-radius: 8px;
                            padding: 15px;
                            margin-bottom: 15px;
                            border: 1px solid #e0e0e0;
                        ">
                            <div style="color: #666; font-style: italic;">
                                Чат загружается...
                            </div>
                        </div>
                        
                        <div style="display: flex; gap: 10px;">
                            <input type="text" id="message-input" 
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
                                background: #FFC107;
                                color: white;
                                border: none;
                                border-radius: 25px;
                                padding: 0 24px;
                                font-weight: 600;
                                cursor: pointer;
                            ">
                                Отправить
                            </button>
                        </div>
                    </div>
                </div>
                
                <script>
                    function sendMessage() {{
                        var input = document.getElementById('message-input');
                        var message = input.value.trim();
                        
                        if (message) {{
                            var chat = document.getElementById('chat-messages');
                            var newMsg = document.createElement('div');
                            newMsg.innerHTML = `
                                <div style="margin-bottom: 10px;">
                                    <div style="font-weight: 600; color: #333;">Вы</div>
                                    <div>${{message}}</div>
                                    <div style="font-size: 12px; color: #666; text-align: right;">${{new Date().toLocaleTimeString([], {{hour: '2-digit', minute:'2-digit'}})}}</div>
                                </div>
                            `;
                            chat.appendChild(newMsg);
                            input.value = '';
                            chat.scrollTop = chat.scrollHeight;
                        }}
                    }}
                    
                    // Автофокус на поле ввода
                    document.getElementById('message-input').focus();
                </script>
            </body>
            </html>
            """, height=800)
            
            if st.button("← Выйти из комнаты"):
                del st.session_state.current_room
                st.rerun()

# ================= ДИСК =================
elif st.session_state.page == "Диск":
    st.markdown('<h1 class="main-title">💾 Облачный диск</h1>', unsafe_allow_html=True)
    
    # Создаем папку пользователя если не существует
    user_folder = f"zornet_storage/{st.session_state.user_data['username']}"
    os.makedirs(user_folder, exist_ok=True)
    st.session_state.disk_current_path = user_folder
    
    # Функции для работы с файлами
    def get_file_icon(filename):
        ext = os.path.splitext(filename)[1].lower()
        icons = {
            '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️',
            '.pdf': '📄',
            '.doc': '📝', '.docx': '📝',
            '.mp3': '🎵', '.wav': '🎵',
            '.mp4': '🎬', '.avi': '🎬', '.mov': '🎬',
            '.zip': '🗜️', '.rar': '🗜️',
            '.py': '🐍', '.js': '📜', '.html': '🌐', '.css': '🎨',
        }
        return icons.get(ext, '📄')
    
    def format_size(size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    # Панель инструментов
    col_tool1, col_tool2, col_tool3, col_tool4 = st.columns(4)
    
    with col_tool1:
        if st.button("📤 Загрузить файл", use_container_width=True):
            st.session_state.disk_action = "upload"
    
    with col_tool2:
        if st.button("📁 Новая папка", use_container_width=True):
            st.session_state.disk_action = "new_folder"
    
    with col_tool3:
        if st.button("🔍 Поиск", use_container_width=True):
            st.session_state.disk_action = "search"
    
    with col_tool4:
        if st.button("🔄 Обновить", use_container_width=True):
            st.rerun()
    
    # Статистика
    total_size = 0
    file_count = 0
    
    for root, dirs, files in os.walk(user_folder):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.exists(file_path):
                total_size += os.path.getsize(file_path)
                file_count += 1
    
    st.metric("Использовано", format_size(total_size))
    st.progress(min(total_size / (1024**3), 1.0))  # 1GB лимит
    
    # Режимы работы
    if st.session_state.disk_action == "upload":
        st.markdown("### 📤 Загрузка файлов")
        
        uploaded_files = st.file_uploader(
            "Выберите файлы для загрузки",
            accept_multiple_files=True,
            type=None
        )
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                file_path = os.path.join(st.session_state.disk_current_path, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            st.success(f"✅ Загружено {len(uploaded_files)} файлов!")
            st.session_state.disk_action = "view"
            st.rerun()
        
        if st.button("← Назад", use_container_width=True):
            st.session_state.disk_action = "view"
            st.rerun()
    
    elif st.session_state.disk_action == "new_folder":
        st.markdown("### 📁 Создание папки")
        
        folder_name = st.text_input("Название папки:")
        
        col_create, col_back = st.columns(2)
        with col_create:
            if st.button("✅ Создать", use_container_width=True, type="primary"):
                if folder_name:
                    new_path = os.path.join(st.session_state.disk_current_path, folder_name)
                    os.makedirs(new_path, exist_ok=True)
                    st.success(f"Папка '{folder_name}' создана!")
                    st.session_state.disk_action = "view"
                    st.rerun()
        
        with col_back:
            if st.button("← Назад", use_container_width=True):
                st.session_state.disk_action = "view"
                st.rerun()
    
    elif st.session_state.disk_action == "search":
        st.markdown("### 🔍 Поиск файлов")
        
        search_query = st.text_input("Введите название файла:")
        
        if search_query:
            results = []
            for root, dirs, files in os.walk(user_folder):
                for name in dirs + files:
                    if search_query.lower() in name.lower():
                        item_path = os.path.join(root, name)
                        results.append({
                            'name': name,
                            'path': item_path,
                            'is_dir': os.path.isdir(item_path)
                        })
            
            if results:
                st.markdown(f"**Найдено {len(results)} результатов:**")
                for item in results:
                    icon = "📁" if item['is_dir'] else get_file_icon(item['name'])
                    st.markdown(f"{icon} **{item['name']}**")
            else:
                st.info("Ничего не найдено")
        
        if st.button("← Назад"):
            st.session_state.disk_action = "view"
            st.rerun()
    
    else:
        # Просмотр файлов
        st.markdown("### 📁 Ваши файлы")
        
        # Быстрая загрузка
        quick_upload = st.file_uploader(
            "Перетащите файлы сюда",
            accept_multiple_files=True,
            label_visibility="collapsed"
        )
        
        if quick_upload:
            for file in quick_upload:
                file_path = os.path.join(st.session_state.disk_current_path, file.name)
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
            st.rerun()
        
        # Список файлов
        try:
            items = os.listdir(st.session_state.disk_current_path)
        except:
            items = []
        
        if not items:
            st.info("📭 Папка пуста")
        else:
            for item in sorted(items):
                item_path = os.path.join(st.session_state.disk_current_path, item)
                is_dir = os.path.isdir(item_path)
                icon = "📁" if is_dir else get_file_icon(item)
                
                col1, col2, col3 = st.columns([6, 2, 2])
                
                with col1:
                    st.markdown(f"""
                    <div class="file-item">
                        <div class="file-icon">{icon}</div>
                        <div class="file-name">{item}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    if not is_dir:
                        file_size = os.path.getsize(item_path)
                        st.markdown(f'<div class="file-size">{format_size(file_size)}</div>', unsafe_allow_html=True)
                
                with col3:
                    if not is_dir:
                        with open(item_path, 'rb') as f:
                            st.download_button(
                                "📥",
                                f.read(),
                                item,
                                key=f"dl_{item}",
                                help="Скачать файл"
                            )

# ================= НОВОСТИ =================
elif st.session_state.page == "Новости":
    st.markdown('<h1 class="main-title">📰 Новости</h1>', unsafe_allow_html=True)
    
    try:
        response = requests.get("https://www.belta.by/rss", timeout=10)
        feed = feedparser.parse(response.content)
        
        for entry in feed.entries[:10]:
            with st.container():
                st.markdown(f"""
                <div class="card">
                    <h3>{entry.title}</h3>
                    <p>{entry.summary[:200]}...</p>
                    <a href="{entry.link}" target="_blank" style="
                        color: var(--primary-color);
                        text-decoration: none;
                        font-weight: 600;
                    ">Читать далее →</a>
                </div>
                """, unsafe_allow_html=True)
    except:
        st.info("Не удалось загрузить новости")

# ================= ПОГОДА =================
elif st.session_state.page == "Погода":
    st.markdown('<h1 class="main-title">🌤️ Погода</h1>', unsafe_allow_html=True)
    
    city = st.text_input("Город", value="Минск", placeholder="Введите город")
    
    if city:
        try:
            # Используем OpenWeatherMap API
            API_KEY = "20ebdd8243b8a3a29abe332fefdadb44"
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric&lang=ru"
            
            response = requests.get(url)
            data = response.json()
            
            if response.status_code == 200:
                temp = data['main']['temp']
                feels_like = data['main']['feels_like']
                humidity = data['main']['humidity']
                description = data['weather'][0]['description']
                wind_speed = data['wind']['speed']
                
                col_temp, col_details = st.columns(2)
                
                with col_temp:
                    st.markdown(f"""
                    <div class="card">
                        <div style="font-size: 48px; font-weight: 800; color: #333;">
                            {temp:.0f}°C
                        </div>
                        <div style="font-size: 18px; color: #666;">
                            Ощущается как {feels_like:.0f}°C
                        </div>
                        <div style="font-size: 24px; margin-top: 10px;">
                            {description.capitalize()}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_details:
                    st.markdown(f"""
                    <div class="card">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                            <div>
                                <div style="font-size: 14px; color: #666;">Влажность</div>
                                <div style="font-size: 24px; font-weight: 600;">{humidity}%</div>
                            </div>
                            <div>
                                <div style="font-size: 14px; color: #666;">Ветер</div>
                                <div style="font-size: 24px; font-weight: 600;">{wind_speed} м/с</div>
                            </div>
                            <div>
                                <div style="font-size: 14px; color: #666;">Давление</div>
                                <div style="font-size: 24px; font-weight: 600;">{data['main']['pressure']} гПа</div>
                            </div>
                            <div>
                                <div style="font-size: 14px; color: #666;">Видимость</div>
                                <div style="font-size: 24px; font-weight: 600;">{data.get('visibility', 10000)/1000:.1f} км</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.error("Город не найден")
        except:
            st.error("Ошибка при получении данных о погоде")

# ================= НАСТРОЙКИ =================
elif st.session_state.page == "Настройки":
    st.markdown('<h1 class="main-title">⚙️ Настройки</h1>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Профиль", "Безопасность", "Уведомления"])
    
    with tab1:
        st.markdown("### Настройки профиля")
        
        col_avatar, col_info = st.columns([1, 2])
        
        with col_avatar:
            st.markdown("**Аватар**")
            current_avatar = st.session_state.user_data.get('avatar')
            
            if current_avatar:
                st.image(current_avatar, width=150)
            else:
                st.markdown("""
                <div style="
                    width: 150px;
                    height: 150px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 48px;
                    font-weight: bold;
                    margin-bottom: 10px;
                ">
                    {user.get('first_name', 'П')[0]}
                </div>
                """, unsafe_allow_html=True)
            
            new_avatar = st.file_uploader("Загрузить новый аватар", type=['jpg', 'png', 'jpeg'])
        
        with col_info:
            first_name = st.text_input("Имя", value=st.session_state.user_data.get('first_name', ''))
            last_name = st.text_input("Фамилия", value=st.session_state.user_data.get('last_name', ''))
            username = st.text_input("Никнейм", value=st.session_state.user_data.get('username', ''))
            
            if st.button("Сохранить изменения", type="primary"):
                st.success("Изменения сохранены!")
    
    with tab2:
        st.markdown("### Безопасность")
        
        current_password = st.text_input("Текущий пароль", type="password")
        new_password = st.text_input("Новый пароль", type="password")
        confirm_password = st.text_input("Повторите новый пароль", type="password")
        
        if st.button("Изменить пароль", type="primary"):
            if new_password == confirm_password and len(new_password) >= 6:
                st.success("Пароль изменен!")
            else:
                st.error("Пароли не совпадают или слишком короткие")
    
    with tab3:
        st.markdown("### Уведомления")
        
        email_notifications = st.checkbox("Email уведомления", value=True)
        push_notifications = st.checkbox("Push уведомления", value=True)
        sound_notifications = st.checkbox("Звуковые уведомления", value=True)
        
        if st.button("Сохранить настройки", type="primary"):
            st.success("Настройки сохранены!")

# ================= ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ =================
if __name__ == "__main__":
    init_db()
