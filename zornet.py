import streamlit as st
import sqlite3
import datetime
import os
import pytz
import json
import hashlib
import uuid
import re
import secrets
from pathlib import Path
import mimetypes
from PIL import Image
import requests
import feedparser
from duckduckgo_search import DDGS
import streamlit.components.v1 as components

# ================= НАСТРОЙКИ =================
st.set_page_config(
    page_title="ZORNET Messenger",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= СЕССИЯ =================
if "page" not in st.session_state:
    st.session_state.page = "Главная"
if "auth_status" not in st.session_state:
    st.session_state.auth_status = "not_logged_in"
if "user_data" not in st.session_state:
    st.session_state.user_data = {}
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = {}
if "search_username" not in st.session_state:
    st.session_state.search_username = ""
if "new_room_id" not in st.session_state:
    st.session_state.new_room_id = ""
if "new_room_password" not in st.session_state:
    st.session_state.new_room_password = ""
if "rooms" not in st.session_state:
    st.session_state.rooms = []
if "watch_room" not in st.session_state:
    st.session_state.watch_room = None

# ================= ОБНОВЛЕННЫЕ CSS СТИЛИ =================
st.markdown("""
<style>
    /* Основные стили */
    .gold-title {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(to bottom, #DAA520, #B8860B);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin: 10px 0 20px 0;
    }
    
    /* Убираем белую полосу под заголовком */
    .stApp > header {
        background-color: transparent;
    }
    
    .stApp {
        margin-top: -80px;
    }
    
    /* Стили для мессенджера */
    .messenger-container {
        display: flex;
        height: 700px;
        background: white;
        border-radius: 16px;
        border: 1px solid #e0e0e0;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
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
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .messages-container {
        flex: 1;
        padding: 20px;
        overflow-y: auto;
        background: #f0f2f5;
        display: flex;
        flex-direction: column;
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
        border-left: 4px solid #DAA520;
    }
    
    .message-bubble {
        max-width: 70%;
        padding: 10px 14px;
        border-radius: 18px;
        margin-bottom: 8px;
        word-wrap: break-word;
        position: relative;
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
    
    .message-time {
        font-size: 11px;
        color: #666;
        text-align: right;
        margin-top: 4px;
    }
    
    .online-status {
        font-size: 12px;
        color: #666;
    }
    
    .online-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #4CAF50;
        margin-right: 6px;
    }
    
    .offline-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #9E9E9E;
        margin-right: 6px;
    }
    
    .unread-badge {
        background: #DAA520;
        color: white;
        border-radius: 50%;
        width: 20px;
        height: 20px;
        text-align: center;
        line-height: 20px;
        font-size: 12px;
        margin-left: auto;
    }
    
    /* Стили для входа/регистрации */
    .login-container {
        max-width: 500px;
        margin: 50px auto;
        padding: 40px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
    }
    
    /* Кнопки */
    .stButton > button {
        transition: all 0.3s ease;
    }
    
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
</style>
""", unsafe_allow_html=True)

# ================= БАЗА ДАННЫХ =================
def init_db():
    """Инициализация базы данных с правильной структурой"""
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
            avatar TEXT,
            is_online BOOLEAN DEFAULT 0,
            last_seen TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Чаты (личные сообщения)
    c.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT UNIQUE NOT NULL,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user1_id) REFERENCES users (id),
            FOREIGN KEY (user2_id) REFERENCES users (id)
        )
    """)
    
    # Сообщения в чатах
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            is_read BOOLEAN DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats (id),
            FOREIGN KEY (sender_id) REFERENCES users (id)
        )
    """)
    
    # Комнаты для совместного просмотра
    c.execute("""
        CREATE TABLE IF NOT EXISTS watch_rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            youtube_url TEXT,
            password_hash TEXT NOT NULL,
            owner_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users (id)
        )
    """)
    
    # Сообщения в комнатах
    c.execute("""
        CREATE TABLE IF NOT EXISTS room_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()

def create_test_user():
    """Создание тестового пользователя"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
    c = conn.cursor()
    
    # Создаем тестового пользователя если его нет
    test_password_hash = hashlib.sha256("test123".encode()).hexdigest()
    
    try:
        c.execute("""
            INSERT OR IGNORE INTO users (email, username, first_name, last_name, password_hash)
            VALUES (?, ?, ?, ?, ?)
        """, ("test@zornet.by", "test_user", "Тестовый", "Пользователь", test_password_hash))
        
        # Создаем еще тестовых пользователей для демонстрации
        users = [
            ("user1@zornet.by", "marina", "Марина", "Иванова", hashlib.sha256("pass123".encode()).hexdigest()),
            ("user2@zornet.by", "alexey", "Алексей", "Петров", hashlib.sha256("pass123".encode()).hexdigest()),
            ("user3@zornet.by", "irina", "Ирина", "Сидорова", hashlib.sha256("pass123".encode()).hexdigest()),
            ("user4@zornet.by", "dmitry", "Дмитрий", "Козлов", hashlib.sha256("pass123".encode()).hexdigest()),
        ]
        
        for email, username, first_name, last_name, password_hash in users:
            c.execute("""
                INSERT OR IGNORE INTO users (email, username, first_name, last_name, password_hash)
                VALUES (?, ?, ?, ?, ?)
            """, (email, username, first_name, last_name, password_hash))
        
        conn.commit()
        print("✅ Тестовые пользователи созданы!")
    except Exception as e:
        print(f"Ошибка создания тестовых пользователей: {e}")
    
    conn.close()

def register_user(email, username, first_name, last_name, password):
    """Регистрация нового пользователя"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
    c = conn.cursor()
    
    try:
        # Проверяем, существует ли пользователь
        c.execute("SELECT id FROM users WHERE email = ? OR username = ?", (email, username))
        if c.fetchone():
            conn.close()
            return False, "Пользователь с таким email или username уже существует"
        
        # Хешируем пароль
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Создаем пользователя
        c.execute("""
            INSERT INTO users (email, username, first_name, last_name, password_hash, is_online, last_seen)
            VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
        """, (email, username, first_name, last_name, password_hash))
        
        user_id = c.lastrowid
        
        conn.commit()
        conn.close()
        
        return True, user_id
    except Exception as e:
        conn.close()
        return False, f"Ошибка регистрации: {str(e)}"

def login_user(email, password):
    """Вход пользователя"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
    c = conn.cursor()
    
    try:
        # Хешируем пароль для сравнения
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Ищем пользователя
        c.execute("""
            SELECT id, email, username, first_name, last_name, avatar 
            FROM users 
            WHERE email = ? AND password_hash = ?
        """, (email, password_hash))
        
        user = c.fetchone()
        
        if user:
            # Обновляем статус онлайн
            user_id = user[0]
            c.execute("UPDATE users SET is_online = 1, last_seen = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
            conn.commit()
            
            user_data = {
                "id": user[0],
                "email": user[1],
                "username": user[2],
                "first_name": user[3],
                "last_name": user[4],
                "avatar": user[5]
            }
            
            conn.close()
            return True, user_data
        else:
            conn.close()
            return False, "Неверный email или пароль"
    except Exception as e:
        conn.close()
        return False, f"Ошибка входа: {str(e)}"

def logout_user(user_id):
    """Выход пользователя"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
    c = conn.cursor()
    
    try:
        c.execute("UPDATE users SET is_online = 0, last_seen = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def get_user_by_username(username):
    """Поиск пользователя по username"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
    c = conn.cursor()
    
    c.execute("""
        SELECT id, username, first_name, last_name, is_online, last_seen 
        FROM users 
        WHERE username = ?
    """, (username,))
    
    user = c.fetchone()
    conn.close()
    
    if user:
        return {
            "id": user[0],
            "username": user[1],
            "first_name": user[2],
            "last_name": user[3],
            "is_online": bool(user[4]),
            "last_seen": user[5]
        }
    return None

def create_chat(user1_id, user2_id):
    """Создание нового чата между двумя пользователями"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
    c = conn.cursor()
    
    # Проверяем, существует ли уже чат
    room_id = f"chat_{min(user1_id, user2_id)}_{max(user1_id, user2_id)}"
    
    c.execute("SELECT id FROM chats WHERE room_id = ?", (room_id,))
    existing_chat = c.fetchone()
    
    if existing_chat:
        conn.close()
        return existing_chat[0], room_id
    
    # Создаем новый чат
    c.execute("""
        INSERT INTO chats (room_id, user1_id, user2_id)
        VALUES (?, ?, ?)
    """, (room_id, user1_id, user2_id))
    
    chat_id = c.lastrowid
    
    # Добавляем приветственное сообщение
    welcome_message = "👋 Добро пожаловать в чат! Начните общение."
    c.execute("""
        INSERT INTO chat_messages (chat_id, sender_id, content, is_read)
        VALUES (?, ?, ?, 1)
    """, (chat_id, user1_id, welcome_message))
    
    conn.commit()
    conn.close()
    
    return chat_id, room_id

def get_user_chats(user_id):
    """Получение всех чатов пользователя"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
    c = conn.cursor()
    
    c.execute("""
        SELECT 
            c.id,
            c.room_id,
            CASE 
                WHEN c.user1_id = ? THEN c.user2_id 
                ELSE c.user1_id 
            END as other_user_id,
            u.username,
            u.first_name,
            u.last_name,
            u.is_online,
            u.last_seen,
            (SELECT content FROM chat_messages 
             WHERE chat_id = c.id 
             ORDER BY timestamp DESC LIMIT 1) as last_message,
            (SELECT timestamp FROM chat_messages 
             WHERE chat_id = c.id 
             ORDER BY timestamp DESC LIMIT 1) as last_message_time,
            (SELECT COUNT(*) FROM chat_messages 
             WHERE chat_id = c.id AND sender_id != ? AND is_read = 0) as unread_count
        FROM chats c
        JOIN users u ON (c.user1_id = u.id OR c.user2_id = u.id) AND u.id != ?
        WHERE c.user1_id = ? OR c.user2_id = ?
        ORDER BY last_message_time DESC
    """, (user_id, user_id, user_id, user_id, user_id))
    
    chats = []
    for row in c.fetchall():
        chats.append({
            "id": row[0],
            "room_id": row[1],
            "other_user_id": row[2],
            "username": row[3],
            "first_name": row[4],
            "last_name": row[5],
            "is_online": bool(row[6]),
            "last_seen": row[7],
            "last_message": row[8] or "Нет сообщений",
            "last_message_time": row[9],
            "unread_count": row[10] or 0
        })
    
    conn.close()
    return chats

def get_chat_messages(chat_id, user_id):
    """Получение сообщений из чата"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
    c = conn.cursor()
    
    # Получаем сообщения
    c.execute("""
        SELECT 
            m.id,
            m.sender_id,
            u.username,
            u.first_name,
            m.content,
            m.timestamp,
            m.is_read
        FROM chat_messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.chat_id = ?
        ORDER BY m.timestamp ASC
    """, (chat_id,))
    
    messages = []
    for row in c.fetchall():
        is_you = row[1] == user_id
        messages.append({
            "id": row[0],
            "sender_id": row[1],
            "username": row[2],
            "first_name": row[3],
            "content": row[4],
            "timestamp": row[5],
            "is_read": bool(row[6]),
            "is_you": is_you
        })
    
    # Помечаем сообщения как прочитанные
    c.execute("""
        UPDATE chat_messages 
        SET is_read = 1 
        WHERE chat_id = ? AND sender_id != ? AND is_read = 0
    """, (chat_id, user_id))
    
    conn.commit()
    conn.close()
    
    return messages

def send_message(chat_id, sender_id, content):
    """Отправка сообщения в чат"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
    c = conn.cursor()
    
    try:
        c.execute("""
            INSERT INTO chat_messages (chat_id, sender_id, content)
            VALUES (?, ?, ?)
        """, (chat_id, sender_id, content))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        return False

def create_watch_room(name, youtube_url, password, owner_id):
    """Создание комнаты для совместного просмотра"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
    c = conn.cursor()
    
    try:
        room_id = str(uuid.uuid4())[:8]
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        c.execute("""
            INSERT INTO watch_rooms (room_id, name, youtube_url, password_hash, owner_id)
            VALUES (?, ?, ?, ?, ?)
        """, (room_id, name, youtube_url, password_hash, owner_id))
        
        # Добавляем приветственное сообщение
        welcome_msg = "🎬 Комната создана! Добро пожаловать! ID комнаты: {}, Пароль: {}".format(room_id, password)
        c.execute("""
            INSERT INTO room_messages (room_id, user_id, content)
            VALUES (?, ?, ?)
        """, (room_id, owner_id, welcome_msg))
        
        conn.commit()
        conn.close()
        return True, room_id, password
    except Exception as e:
        conn.close()
        return False, None, None

def join_watch_room(room_id, password):
    """Присоединение к комнате просмотра"""
    conn = sqlite3.connect("zornet.db", check_same_thread=False)
    c = conn.cursor()
    
    try:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        c.execute("""
            SELECT id, name, youtube_url, owner_id 
            FROM watch_rooms 
            WHERE room_id = ? AND password_hash = ?
        """, (room_id, password_hash))
        
        room = c.fetchone()
        
        if room:
            conn.close()
            return True, room
        else:
            conn.close()
            return False, None
    except:
        conn.close()
        return False, None

# ================= ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ =================
init_db()
create_test_user()

# ================= САЙДБАР =================
with st.sidebar:
    st.markdown("<h3 style='color:#DAA520;'>🇧🇾 ZORNET</h3>", unsafe_allow_html=True)
    
    pages = [
        ("🏠", "ГЛАВНАЯ", "Главная"),
        ("💬", "МЕССЕНДЖЕР", "Мессенджер"),
        ("🎬", "СОВМЕСТНЫЙ ПРОСМОТР", "Совместный просмотр"),
        ("👤", "ПРОФИЛЬ", "Профиль"),
    ]
    
    for i, (icon, text, page) in enumerate(pages):
        if st.button(f"{icon} {text}", key=f"nav_{i}_{page}", use_container_width=True):
            st.session_state.page = page
            st.rerun()

# ================= ПРОВЕРКА АВТОРИЗАЦИИ =================
def check_auth():
    """Проверка авторизации пользователя"""
    if st.session_state.auth_status != "logged_in":
        if st.session_state.page != "Профиль":
            st.session_state.page = "Профиль"
            st.rerun()
        return False
    return True

# ================= СТРАНИЦА ВХОДА/РЕГИСТРАЦИИ =================
if st.session_state.page == "Профиль" and st.session_state.auth_status != "logged_in":
    st.markdown('<div class="gold-title">ZORNET ID</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Вход", "Регистрация"])
    
    with tab1:
        st.markdown("### Вход в аккаунт")
        
        email = st.text_input("Email", placeholder="email@example.com", key="login_email")
        password = st.text_input("Пароль", type="password", placeholder="********", key="login_password")
        
        if st.button("Войти", type="primary", use_container_width=True):
            if email and password:
                success, result = login_user(email, password)
                if success:
                    st.session_state.user_data = result
                    st.session_state.auth_status = "logged_in"
                    st.session_state.page = "Главная"
                    st.success("✅ Вход выполнен!")
                    st.rerun()
                else:
                    st.error(result)
            else:
                st.error("Заполните все поля")
    
    with tab2:
        st.markdown("### Регистрация")
        
        first_name = st.text_input("Имя", placeholder="Иван", key="reg_first_name")
        last_name = st.text_input("Фамилия", placeholder="Иванов", key="reg_last_name")
        email = st.text_input("Email", placeholder="email@example.com", key="reg_email")
        username = st.text_input("Никнейм", placeholder="ivan_zornet", key="reg_username")
        password = st.text_input("Пароль", type="password", placeholder="********", key="reg_password")
        password_confirm = st.text_input("Повторите пароль", type="password", placeholder="********", key="reg_password_confirm")
        
        if st.button("Создать аккаунт", type="primary", use_container_width=True):
            if not all([first_name, last_name, email, username, password, password_confirm]):
                st.error("Заполните все поля")
            elif password != password_confirm:
                st.error("Пароли не совпадают")
            elif len(password) < 6:
                st.error("Пароль должен быть не менее 6 символов")
            else:
                success, result = register_user(email, username, first_name, last_name, password)
                if success:
                    # Автоматически входим после регистрации
                    login_success, user_data = login_user(email, password)
                    if login_success:
                        st.session_state.user_data = user_data
                        st.session_state.auth_status = "logged_in"
                        st.session_state.page = "Главная"
                        st.success("✅ Аккаунт создан и выполнен вход!")
                        st.rerun()
                else:
                    st.error(result)
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ================= СТРАНИЦА ГЛАВНАЯ =================
elif st.session_state.page == "Главная":
    if not check_auth():
        st.stop()
    
    st.markdown('<div class="gold-title">ZORNET</div>', unsafe_allow_html=True)
    
    current_time = datetime.datetime.now(pytz.timezone('Europe/Minsk')).strftime('%H:%M')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.button(f"🕒 {current_time}\nМинск", use_container_width=True)
    with col2:
        if st.button("💬 Мессенджер", use_container_width=True):
            st.session_state.page = "Мессенджер"
            st.rerun()
    with col3:
        if st.button("🎬 Совм. просмотр", use_container_width=True):
            st.session_state.page = "Совместный просмотр"
            st.rerun()
    with col4:
        if st.button("👤 Профиль", use_container_width=True):
            st.session_state.page = "Профиль"
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
        }

        input[type="text"]:focus {
            border-color: #DAA520;
            box-shadow: 0 0 15px rgba(218, 165, 32, 0.2);
        }
    </style>
    </head>
    <body>
        <div class="search-container">
            <form action="https://www.google.com/search" method="get" target="_top">
                <input type="text" name="q" placeholder="🔍 Введите запрос..." required autocomplete="off">
            </form>
        </div>
    </body>
    </html>
    """, height=100)

# ================= МЕССЕНДЖЕР (РАБОЧИЙ) =================
elif st.session_state.page == "Мессенджер":
    if not check_auth():
        st.stop()
    
    st.markdown('<div class="gold-title">💬 ZORNET МЕССЕНДЖЕР</div>', unsafe_allow_html=True)
    
    user = st.session_state.user_data
    user_id = user.get("id")
    
    # Получаем чаты пользователя
    chats = get_user_chats(user_id)
    
    # Две колонки: список чатов и окно чата
    col_contacts, col_chat = st.columns([1, 2])
    
    with col_contacts:
        st.markdown("### 💬 Мои чаты")
        
        # Поиск пользователя для нового чата
        with st.expander("🔍 Найти пользователя", expanded=True):
            search_username = st.text_input(
                "Введите username:",
                placeholder="@username",
                key="search_username_input"
            )
            
            if st.button("Начать чат", use_container_width=True):
                if search_username:
                    found_user = get_user_by_username(search_username)
                    if found_user:
                        if found_user["id"] == user_id:
                            st.error("Нельзя начать чат с самим собой")
                        else:
                            # Создаем чат
                            chat_id, room_id = create_chat(user_id, found_user["id"])
                            
                            # Добавляем в список чатов
                            new_chat = {
                                "id": chat_id,
                                "room_id": room_id,
                                "other_user_id": found_user["id"],
                                "username": found_user["username"],
                                "first_name": found_user["first_name"],
                                "last_name": found_user["last_name"],
                                "is_online": found_user["is_online"],
                                "last_seen": found_user["last_seen"],
                                "last_message": "👋 Чат создан",
                                "last_message_time": datetime.datetime.now(),
                                "unread_count": 0
                            }
                            
                            # Устанавливаем текущий чат
                            st.session_state.current_chat_id = chat_id
                            st.success(f"Чат с @{found_user['username']} создан!")
                            st.rerun()
                    else:
                        st.error("Пользователь не найден")
        
        st.markdown("---")
        
        # Список чатов
        if chats:
            for chat in chats:
                is_active = st.session_state.current_chat_id == chat["id"]
                
                # Форматируем время последнего сообщения
                if chat["last_message_time"]:
                    last_time = chat["last_message_time"]
                    if isinstance(last_time, str):
                        last_time = datetime.datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")
                    
                    time_diff = datetime.datetime.now() - last_time
                    if time_diff.days == 0:
                        time_str = last_time.strftime("%H:%M")
                    elif time_diff.days == 1:
                        time_str = "Вчера"
                    else:
                        time_str = last_time.strftime("%d.%m")
                else:
                    time_str = ""
                
                # Статус онлайн
                status_html = f'<span class="online-dot"></span> онлайн' if chat["is_online"] else f'<span class="offline-dot"></span> не в сети'
                
                # Бейдж непрочитанных сообщений
                unread_badge = ""
                if chat["unread_count"] > 0:
                    unread_badge = f'<span class="unread-badge">{chat["unread_count"]}</span>'
                
                # Отображаем чат
                if st.button(
                    f"**{chat['first_name']} {chat['last_name']}**\n"
                    f"@{chat['username']} • {time_str}\n"
                    f"{chat['last_message'][:30]}...",
                    key=f"chat_{chat['id']}",
                    use_container_width=True
                ):
                    st.session_state.current_chat_id = chat["id"]
                    st.rerun()
                
                # Показываем статус и непрочитанные
                st.markdown(f'<div style="display: flex; justify-content: space-between; margin-top: -10px; margin-bottom: 10px;">'
                           f'<span style="font-size: 12px; color: #666;">{status_html}</span>'
                           f'{unread_badge}'
                           f'</div>', unsafe_allow_html=True)
        else:
            st.info("📭 У вас пока нет чатов. Найдите пользователя, чтобы начать общение.")
    
    with col_chat:
        if st.session_state.current_chat_id:
            # Находим текущий чат
            current_chat = next((c for c in chats if c["id"] == st.session_state.current_chat_id), None)
            
            if current_chat:
                # Заголовок чата
                st.markdown(f"""
                <div class="chat-header">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="
                            width: 45px;
                            height: 45px;
                            border-radius: 50%;
                            background: linear-gradient(135deg, #DAA520, #B8860B);
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            color: white;
                            font-weight: bold;
                            font-size: 18px;
                        ">
                            {current_chat['first_name'][0] if current_chat['first_name'] else current_chat['username'][0]}
                        </div>
                        <div>
                            <div style="font-weight: 600; font-size: 18px;">
                                {current_chat['first_name']} {current_chat['last_name']}
                            </div>
                            <div style="font-size: 14px; color: #666;">
                                @{current_chat['username']} • 
                                {('<span class="online-dot"></span> онлайн' if current_chat['is_online'] 
                                  else '<span class="offline-dot"></span> не в сети')}
                            </div>
                        </div>
                    </div>
                    <div>
                        <button onclick="window.location.reload()" style="
                            background: transparent;
                            border: none;
                            font-size: 20px;
                            cursor: pointer;
                            color: #666;
                        ">🔄</button>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Получаем сообщения
                messages = get_chat_messages(current_chat["id"], user_id)
                
                # Контейнер для сообщений
                st.markdown('<div class="messages-container">', unsafe_allow_html=True)
                
                if messages:
                    for msg in messages:
                        message_class = "you" if msg["is_you"] else "other"
                        sender_name = "Вы" if msg["is_you"] else msg["first_name"]
                        
                        # Форматируем время
                        if isinstance(msg["timestamp"], str):
                            msg_time = datetime.datetime.strptime(msg["timestamp"], "%Y-%m-%d %H:%M:%S")
                        else:
                            msg_time = msg["timestamp"]
                        
                        time_str = msg_time.strftime("%H:%M")
                        
                        # Галочки прочтения
                        checkmarks = "✓✓" if msg["is_read"] else "✓"
                        
                        st.markdown(f"""
                        <div class="message-bubble {message_class}">
                            <div><strong>{sender_name}</strong></div>
                            <div style="margin: 5px 0;">{msg['content']}</div>
                            <div class="message-time">
                                {time_str} {checkmarks if msg['is_you'] else ''}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="text-align: center; padding: 40px; color: #666;">
                        <div style="font-size: 48px; margin-bottom: 20px;">💬</div>
                        <h3>Нет сообщений</h3>
                        <p>Начните общение первым!</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Поле ввода сообщения
                st.markdown('<div class="message-input-area">', unsafe_allow_html=True)
                
                col_input, col_send = st.columns([5, 1])
                
                with col_input:
                    new_message = st.text_input(
                        "💬 Введите сообщение...",
                        key=f"msg_input_{current_chat['id']}",
                        label_visibility="collapsed",
                        placeholder="Напишите сообщение..."
                    )
                
                with col_send:
                    if st.button("Отправить", type="primary", use_container_width=True):
                        if new_message.strip():
                            if send_message(current_chat["id"], user_id, new_message.strip()):
                                st.success("✅ Сообщение отправлено!")
                                st.rerun()
                            else:
                                st.error("❌ Ошибка отправки")
                
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("👈 Выберите чат из списка слева или найдите пользователя для начала нового чата")

# ================= СОВМЕСТНЫЙ ПРОСМОТР =================
elif st.session_state.page == "Совместный просмотр":
    if not check_auth():
        st.stop()
    
    st.markdown('<div class="gold-title">🎬 СОВМЕСТНЫЙ ПРОСМОТР</div>', unsafe_allow_html=True)
    
    user = st.session_state.user_data
    
    # Если выбрана комната, показываем плеер
    if st.session_state.get("watch_room"):
        st.markdown("### 🎥 Комната для совместного просмотра")
        
        # Получаем данные комнаты из базы
        success, room_data = join_watch_room(st.session_state.watch_room, st.session_state.get("room_password", ""))
        
        if success:
            room_id, room_name, youtube_url, owner_id = room_data
            
            # Извлекаем ID видео
            video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', youtube_url)
            video_id = video_id_match.group(1) if video_id_match else "dQw4w9WgXcQ"  # Fallback
            
            st.markdown(f"**Комната:** {room_name}")
            st.markdown(f"**ID комнаты:** `{room_id}`")
            
            # YouTube плеер
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
                    .room-info {{
                        padding: 20px;
                        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
                        color: white;
                        border-radius: 12px;
                        margin-bottom: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="watch-container">
                    <!-- Информация о комнате -->
                    <div class="room-info">
                        <h3 style="margin: 0 0 10px 0;">{room_name}</h3>
                        <p style="margin: 0; opacity: 0.9;">ID: {room_id} | Владелец: {user.get('username', 'Гость')}</p>
                    </div>
                    
                    <!-- YouTube плеер -->
                    <iframe 
                        width="100%" 
                        height="500" 
                        src="https://www.youtube.com/embed/{video_id}?autoplay=1&controls=1&modestbranding=1"
                        frameborder="0" 
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                        allowfullscreen
                        style="border-bottom: 1px solid #e0e0e0;">
                    </iframe>
                    
                    <!-- Чат комнаты -->
                    <div style="padding: 20px; background: white;">
                        <h3 style="margin: 0 0 15px 0; color: #333;">💬 Чат комнаты</h3>
                        
                        <div id="chatMessages" style="
                            height: 200px;
                            overflow-y: auto;
                            padding: 15px;
                            background: #f8f9fa;
                            border-radius: 10px;
                            margin-bottom: 15px;
                        ">
                            <div style="
                                background: white;
                                padding: 10px 14px;
                                border-radius: 18px;
                                margin-bottom: 8px;
                                max-width: 80%;
                                border-bottom-left-radius: 4px;
                                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                            ">
                                <div style="font-weight: 600; color: #DAA520;">{user.get('username', 'Гость')}</div>
                                <div>Комната создана! Добро пожаловать! 🎬</div>
                                <div style="font-size: 12px; color: #666; text-align: right;">{datetime.datetime.now().strftime('%H:%M')}</div>
                            </div>
                        </div>
                        
                        <div style="display: flex; gap: 10px;">
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
                            newMsg.innerHTML = `
                                <div style="
                                    background: #DCF8C6;
                                    padding: 10px 14px;
                                    border-radius: 18px;
                                    margin-bottom: 8px;
                                    max-width: 80%;
                                    margin-left: auto;
                                    border-bottom-right-radius: 4px;
                                ">
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
    
    else:
        # Создание или присоединение к комнате
        col_create, col_join = st.columns(2)
        
        with col_create:
            st.markdown("### Создать комнату")
            
            room_name = st.text_input("Название комнаты:", placeholder="Фильм с друзьями")
            youtube_url = st.text_input("Ссылка на YouTube:", placeholder="https://www.youtube.com/watch?v=...")
            room_password = st.text_input("Пароль комнаты:", type="password", placeholder="Придумайте пароль")
            
            if st.button("🎥 Создать комнату", type="primary", use_container_width=True):
                if room_name and youtube_url and room_password:
                    success, room_id, password = create_watch_room(
                        room_name, 
                        youtube_url, 
                        room_password, 
                        user.get("id")
                    )
                    
                    if success:
                        st.session_state.watch_room = room_id
                        st.session_state.room_password = room_password
                        st.success(f"✅ Комната создана!")
                        st.info(f"**ID комнаты:** `{room_id}`\n**Пароль:** `{password}`\n\nПередайте эти данные друзьям для подключения.")
                        st.rerun()
                else:
                    st.error("Заполните все поля")
        
        with col_join:
            st.markdown("### Присоединиться к комнате")
            
            join_room_id = st.text_input("ID комнаты:", placeholder="Введите ID комнаты")
            join_password = st.text_input("Пароль:", type="password", placeholder="Введите пароль")
            
            if st.button("🔗 Присоединиться", use_container_width=True):
                if join_room_id and join_password:
                    success, room_data = join_watch_room(join_room_id, join_password)
                    if success:
                        st.session_state.watch_room = join_room_id
                        st.session_state.room_password = join_password
                        st.success("✅ Вы присоединились к комнате!")
                        st.rerun()
                    else:
                        st.error("Неверный ID комнаты или пароль")

# ================= ПРОФИЛЬ (с выходом) =================
elif st.session_state.page == "Профиль":
    st.markdown('<div class="gold-title">👤 ПРОФИЛЬ</div>', unsafe_allow_html=True)
    
    if st.session_state.auth_status == "logged_in":
        user = st.session_state.user_data
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Аватар
            st.markdown(f"""
            <div style="text-align: center;">
                <div style="
                    width: 150px;
                    height: 150px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #DAA520, #B8860B);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 48px;
                    font-weight: bold;
                    margin: 0 auto 20px auto;
                ">
                    {user.get('first_name', 'U')[0].upper()}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚪 Выйти из аккаунта", type="primary", use_container_width=True):
                # Выход из системы
                if logout_user(user.get("id")):
                    st.session_state.auth_status = "not_logged_in"
                    st.session_state.user_data = {}
                    st.session_state.page = "Профиль"
                    st.success("✅ Вы вышли из аккаунта")
                    st.rerun()
        
        with col2:
            # Информация о пользователе
            st.markdown("### 📋 Информация о профиле")
            
            st.markdown(f"""
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span style="color: #666;">Имя:</span>
                    <span style="font-weight: 600;">{user.get('first_name', 'Не указано')}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span style="color: #666;">Фамилия:</span>
                    <span style="font-weight: 600;">{user.get('last_name', 'Не указано')}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span style="color: #666;">Email:</span>
                    <span style="font-weight: 600;">{user.get('email', 'Не указано')}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span style="color: #666;">Username:</span>
                    <span style="font-weight: 600;">@{user.get('username', 'Не указано')}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #666;">Статус:</span>
                    <span style="color: #4CAF50; font-weight: 600;">🟢 Онлайн</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Статистика
            conn = sqlite3.connect("zornet.db", check_same_thread=False)
            c = conn.cursor()
            
            # Количество чатов
            c.execute("""
                SELECT COUNT(*) FROM chats 
                WHERE user1_id = ? OR user2_id = ?
            """, (user.get("id"), user.get("id")))
            chat_count = c.fetchone()[0]
            
            # Количество сообщений
            c.execute("""
                SELECT COUNT(*) FROM chat_messages 
                WHERE sender_id = ?
            """, (user.get("id"),))
            message_count = c.fetchone()[0]
            
            conn.close()
            
            st.markdown("### 📊 Статистика")
            col_stat1, col_stat2 = st.columns(2)
            with col_stat1:
                st.metric("💬 Чатов", chat_count)
            with col_stat2:
                st.metric("📨 Сообщений", message_count)
    else:
        # Показываем форму входа
        st.warning("⚠️ Вы не авторизованы")
        if st.button("Войти в аккаунт"):
            st.session_state.page = "Профиль"
            st.rerun()

# ================= ЗАПУСК =================
if __name__ == "__main__":
    # Инициализация при первом запуске
    pass
