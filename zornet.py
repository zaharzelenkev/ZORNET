import streamlit as st
import sqlite3
import datetime
import os
import pytz
import requests
import feedparser
from PIL import Image
from pathlib import Path
import hashlib
import uuid
import re
import time

# ================= НАСТРОЙКИ СТРАНИЦЫ =================
st.set_page_config(
    page_title="ZORNET",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🇧🇾"
)

# ================= CSS СТИЛИ (FIXED) =================
st.markdown("""
<style>
    /* Убираем лишние отступы сверху (белая полоса) */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    header {
        visibility: hidden !important;
    }
    
    /* Глобальные стили */
    .stApp {
        background-color: #f8f9fa;
    }

    /* Кнопка меню справа */
    button[data-testid="stSidebarCollapse"] {
        display: none !important;
    }

    /* Заголовки */
    .gold-title {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 3rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(to bottom, #DAA520, #B8860B);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin: 0 0 20px 0;
    }

    /* Карточки */
    .card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
    }

    /* Сообщения */
    .msg-container {
        height: 500px;
        overflow-y: auto;
        display: flex;
        flex-direction: column-reverse; /* Чтобы новые были внизу при прокрутке */
        padding: 10px;
        background: #e5ddd5;
        border-radius: 10px;
    }
    
    .msg-bubble {
        padding: 10px 15px;
        border-radius: 10px;
        margin-bottom: 8px;
        max-width: 70%;
        position: relative;
        word-wrap: break-word;
    }
    
    .msg-me {
        background-color: #dcf8c6;
        align-self: flex-end;
        margin-left: auto;
    }
    
    .msg-other {
        background-color: #ffffff;
        align-self: flex-start;
        margin-right: auto;
    }

    /* Кнопки */
    .stButton > button {
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
        color: white !important;
        border: none;
        border-radius: 8px;
    }
    .stButton > button:hover {
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# ================= БАЗА ДАННЫХ =================
def init_db():
    """Инициализация БД и создание таблиц, если их нет"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
    c = conn.cursor()
    
    # Пользователи
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            first_name TEXT,
            last_name TEXT,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Личные сообщения
    c.execute("""
        CREATE TABLE IF NOT EXISTS private_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users (id),
            FOREIGN KEY (receiver_id) REFERENCES users (id)
        )
    """)
    
    # Комнаты просмотра
    c.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_uid TEXT UNIQUE,
            name TEXT,
            video_id TEXT,
            password TEXT,
            owner_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Сообщения комнат
    c.execute("""
        CREATE TABLE IF NOT EXISTS room_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_uid TEXT,
            username TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Файлы
    c.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_username TEXT,
            filename TEXT,
            filepath TEXT,
            size INTEGER,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    return conn

conn = init_db()

# ================= СЕССИЯ =================
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "Вход"
if "current_chat_user" not in st.session_state:
    st.session_state.current_chat_user = None
if "watch_room_uid" not in st.session_state:
    st.session_state.watch_room_uid = None

# ================= ФУНКЦИИ LOGIC =================

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login(email, password):
    c = conn.cursor()
    pwd_hash = hash_pass(password)
    c.execute("SELECT id, email, username, first_name, last_name FROM users WHERE email=? AND password_hash=?", (email, pwd_hash))
    return c.fetchone()

def register(email, username, first_name, last_name, password):
    c = conn.cursor()
    try:
        pwd_hash = hash_pass(password)
        c.execute("INSERT INTO users (email, username, first_name, last_name, password_hash) VALUES (?, ?, ?, ?, ?)",
                  (email, username, first_name, last_name, pwd_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def get_user_by_username(username):
    c = conn.cursor()
    c.execute("SELECT id, username, first_name, last_name FROM users WHERE username=?", (username,))
    return c.fetchone()

def send_private_message(sender_id, receiver_id, content):
    c = conn.cursor()
    c.execute("INSERT INTO private_messages (sender_id, receiver_id, content) VALUES (?, ?, ?)", 
              (sender_id, receiver_id, content))
    conn.commit()

def get_private_messages(user1_id, user2_id):
    c = conn.cursor()
    c.execute("""
        SELECT sender_id, content, timestamp FROM private_messages 
        WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
        ORDER BY timestamp ASC
    """, (user1_id, user2_id, user2_id, user1_id))
    return c.fetchall()

def get_my_contacts(user_id):
    """Находит пользователей, с которыми была переписка"""
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT u.id, u.username, u.first_name 
        FROM users u
        JOIN private_messages pm ON (u.id = pm.sender_id OR u.id = pm.receiver_id)
        WHERE (pm.sender_id = ? OR pm.receiver_id = ?) AND u.id != ?
    """, (user_id, user_id, user_id))
    return c.fetchall()

# ================= ИНТЕРФЕЙС =================

# --- САЙДБАР ---
with st.sidebar:
    st.markdown("<h2 style='color:#DAA520; text-align:center;'>ZORNET</h2>", unsafe_allow_html=True)
    
    if st.session_state.user:
        user = st.session_state.user
        st.success(f"Вы вошли как: **{user[2]}**")
        
        menu_items = {
            "Главная": "🏠",
            "Мессенджер": "💬",
            "Совместный просмотр": "🎬",
            "Диск": "💾",
            "Новости": "📰",
            "Погода": "🌤️"
        }
        
        for name, icon in menu_items.items():
            if st.button(f"{icon} {name}", key=f"menu_{name}", use_container_width=True):
                st.session_state.page = name
                st.rerun()
                
        st.markdown("---")
        if st.button("🚪 Выйти", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = "Вход"
            st.rerun()
    else:
        st.info("Пожалуйста, войдите или зарегистрируйтесь.")

# --- СТРАНИЦА ВХОДА/РЕГИСТРАЦИИ ---
if not st.session_state.user:
    st.markdown("<div class='gold-title'>ZORNET ID</div>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Вход", "Регистрация"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Пароль", type="password")
            submit = st.form_submit_button("Войти")
            
            if submit:
                user = login(email, password)
                if user:
                    st.session_state.user = user
                    st.session_state.page = "Главная"
                    st.rerun()
                else:
                    st.error("Неверный email или пароль")

    with tab2:
        with st.form("reg_form"):
            new_email = st.text_input("Email")
            new_username = st.text_input("Никнейм (для поиска)")
            new_fname = st.text_input("Имя")
            new_lname = st.text_input("Фамилия")
            new_pass = st.text_input("Пароль", type="password")
            new_pass2 = st.text_input("Повторите пароль", type="password")
            reg_submit = st.form_submit_button("Создать аккаунт")
            
            if reg_submit:
                if new_pass != new_pass2:
                    st.error("Пароли не совпадают")
                elif len(new_pass) < 6:
                    st.error("Пароль слишком короткий")
                else:
                    if register(new_email, new_username, new_fname, new_lname, new_pass):
                        st.success("Аккаунт создан! Теперь войдите.")
                    else:
                        st.error("Такой email или никнейм уже занят.")

# --- ГЛАВНАЯ ---
elif st.session_state.page == "Главная":
    st.markdown("<div class='gold-title'>ZORNET</div>", unsafe_allow_html=True)
    user = st.session_state.user
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="card">
            <h3>👋 Добро пожаловать, {user[3]}!</h3>
            <p>Это ваша персональная панель управления.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
         st.markdown(f"""
        <div class="card">
            <h3>🕒 Время (Минск)</h3>
            <p style="font-size: 2rem; font-weight: bold; color: #DAA520;">
                {datetime.datetime.now(pytz.timezone('Europe/Minsk')).strftime('%H:%M')}
            </p>
        </div>
        """, unsafe_allow_html=True)

# --- МЕССЕНДЖЕР (РЕАЛЬНЫЙ) ---
elif st.session_state.page == "Мессенджер":
    st.markdown("<div class='gold-title'>💬 МЕССЕНДЖЕР</div>", unsafe_allow_html=True)
    
    col_contacts, col_chat = st.columns([1, 3])
    
    my_id = st.session_state.user[0]
    
    with col_contacts:
        st.markdown("### 🔎 Поиск")
        search_user = st.text_input("Введите никнейм:", placeholder="Например: admin")
        if search_user:
            found_user = get_user_by_username(search_user)
            if found_user:
                if found_user[0] == my_id:
                    st.warning("Это вы!")
                else:
                    if st.button(f"Написать {found_user[1]}", key="start_chat"):
                        st.session_state.current_chat_user = found_user
                        st.rerun()
            else:
                st.error("Пользователь не найден")
        
        st.markdown("---")
        st.markdown("### 👥 Чаты")
        contacts = get_my_contacts(my_id)
        if not contacts:
            st.info("Пока нет чатов")
        
        for c_user in contacts:
            c_id, c_username, c_fname = c_user
            btn_label = f"{c_fname} (@{c_username})"
            # Подсветка активного
            type_btn = "primary" if st.session_state.current_chat_user and st.session_state.current_chat_user[0] == c_id else "secondary"
            
            if st.button(btn_label, key=f"contact_{c_id}", type=type_btn, use_container_width=True):
                st.session_state.current_chat_user = (c_id, c_username, c_fname, "") # Формат кортежа как в поиске
                st.rerun()

    with col_chat:
        target = st.session_state.current_chat_user
        if target:
            st.markdown(f"### Чат с **{target[1]}**")
            
            # Контейнер сообщений
            messages = get_private_messages(my_id, target[0])
            
            # Используем container с фиксированной высотой (эмуляция CSS выше)
            with st.container(height=500):
                for msg in messages:
                    sender_id, content, timestamp = msg
                    is_me = (sender_id == my_id)
                    align = "text-align: right; background: #DAA520; color: white;" if is_me else "text-align: left; background: white; color: black; border: 1px solid #ddd;"
                    
                    st.markdown(f"""
                    <div style='{align} padding: 10px; border-radius: 10px; margin-bottom: 5px; width: fit-content; margin-left: {'auto' if is_me else '0'};'>
                        {content}
                        <div style='font-size: 0.7em; opacity: 0.8;'>{timestamp[11:16]}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Форма отправки
            with st.form("send_msg_form", clear_on_submit=True):
                col_input, col_btn = st.columns([5, 1])
                with col_input:
                    txt = st.text_input("Сообщение", label_visibility="collapsed", placeholder="Напишите сообщение...")
                with col_btn:
                    sent = st.form_submit_button("➤")
                
                if sent and txt:
                    send_private_message(my_id, target[0], txt)
                    st.rerun()
            
            # Автообновление (костыль для Streamlit)
            time.sleep(2)
            st.rerun()
            
        else:
            st.info("👈 Выберите пользователя слева или найдите его через поиск.")

# --- СОВМЕСТНЫЙ ПРОСМОТР ---
elif st.session_state.page == "Совместный просмотр":
    
    # Если мы уже в комнате
    if st.session_state.watch_room_uid:
        room_uid = st.session_state.watch_room_uid
        c = conn.cursor()
        c.execute("SELECT name, video_id, owner_username FROM rooms WHERE room_uid=?", (room_uid,))
        room_data = c.fetchone()
        
        if not room_data:
            st.error("Комната удалена.")
            st.session_state.watch_room_uid = None
            st.rerun()
            
        st.markdown(f"<div class='gold-title'>📺 {room_data[0]}</div>", unsafe_allow_html=True)
        if st.button("← Выйти из комнаты"):
            st.session_state.watch_room_uid = None
            st.rerun()
            
        col_video, col_rchat = st.columns([3, 1])
        
        with col_video:
            st.video(f"https://youtu.be/{room_data[1]}")
            
        with col_rchat:
            st.markdown("### Чат комнаты")
            
            # Чтение сообщений
            c.execute("SELECT username, content, timestamp FROM room_messages WHERE room_uid=? ORDER BY timestamp ASC", (room_uid,))
            r_msgs = c.fetchall()
            
            with st.container(height=400):
                for rm in r_msgs:
                    st.markdown(f"**{rm[0]}:** {rm[1]}")
            
            # Отправка
            with st.form("room_chat"):
                rmsg = st.text_input("Сообщение")
                if st.form_submit_button("Отправить") and rmsg:
                    c.execute("INSERT INTO room_messages (room_uid, username, content) VALUES (?, ?, ?)", 
                              (room_uid, st.session_state.user[2], rmsg))
                    conn.commit()
                    st.rerun()
            
            time.sleep(2)
            st.rerun()

    # Если мы в лобби
    else:
        st.markdown("<div class='gold-title'>🎬 КИНОЗАЛ</div>", unsafe_allow_html=True)
        
        col_create, col_join = st.columns(2)
        
        with col_create:
            st.markdown("### Создать комнату")
            with st.form("create_room"):
                r_name = st.text_input("Название комнаты")
                r_url = st.text_input("Ссылка YouTube")
                r_pass = st.text_input("Пароль комнаты")
                r_create = st.form_submit_button("Создать и войти")
                
                if r_create and r_url and r_pass:
                    # Парсинг ID видео
                    vid_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', r_url)
                    if vid_match:
                        vid = vid_match.group(1)
                        uid = str(uuid.uuid4())[:8]
                        
                        try:
                            c = conn.cursor()
                            c.execute("INSERT INTO rooms (room_uid, name, video_id, password, owner_username) VALUES (?, ?, ?, ?, ?)",
                                      (uid, r_name, vid, r_pass, st.session_state.user[2]))
                            
                            # ПЕРВОЕ СООБЩЕНИЕ (ПРИВЕТСТВИЕ)
                            welcome_msg = f"👋 Добро пожаловать! ID: **{uid}**, Пароль: **{r_pass}**. Передай другу!"
                            c.execute("INSERT INTO room_messages (room_uid, username, content) VALUES (?, ?, ?)",
                                      (uid, "ZORNET BOT", welcome_msg))
                            
                            conn.commit()
                            
                            # СРАЗУ ЗАХОДИМ
                            st.session_state.watch_room_uid = uid
                            st.rerun()
                        except Exception as e:
                            st.error(f"Ошибка: {e}")
                    else:
                        st.error("Некорректная ссылка YouTube")

        with col_join:
            st.markdown("### Войти в комнату")
            j_uid = st.text_input("ID комнаты")
            j_pass = st.text_input("Пароль", type="password")
            if st.button("Присоединиться"):
                c = conn.cursor()
                c.execute("SELECT password FROM rooms WHERE room_uid=?", (j_uid,))
                res = c.fetchone()
                if res and res[0] == j_pass:
                    st.session_state.watch_room_uid = j_uid
                    st.rerun()
                else:
                    st.error("Неверный ID или пароль")

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
