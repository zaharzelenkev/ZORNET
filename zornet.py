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
import uuid
import re
import hashlib
import streamlit.components.v1 as components
import urllib.parse

# ================= СКРЫТИЕ ЭЛЕМЕНТОВ STREAMLIT =================
st.markdown("""
<style>
    /* Скрываем иконку Streamlit внизу справа */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display: none;}
    
    /* Скрываем элементы GitHub сверху справа */
    header .st-emotion-cache-18ni7ap {display: none !important;}
    header .st-emotion-cache-1dp5vir {display: none !important;}
    header .st-emotion-cache-1f3w8xq {display: none !important;}
    header [data-testid="stStatusWidget"] {display: none !important;}
    
    /* Скрываем Fork, троеточие и другие элементы */
    button[title="View source"] {display: none !important;}
    button[title="Report bug"] {display: none !important;}
    button[title="Fork this app"] {display: none !important;}
    button[title="Share"] {display: none !important;}
    button[title="Manage app"] {display: none !important;}
    
    /* Скрываем весь header */
    header {visibility: hidden !important; height: 0 !important;}
    
    /* Убираем отступ сверху */
    .stApp > header {display: none !important;}
    .main > div {padding-top: 0 !important;}
    
    /* Скрываем деплоймент кнопки */
    .stDeployButton {display: none !important;}
    
    /* Скрываем все, что связано с Streamlit в интерфейсе */
    .st-emotion-cache-1dp5vir {display: none !important;}
    .st-emotion-cache-18ni7ap {display: none !important;}
    .st-emotion-cache-1f3w8xq {display: none !important;}
    .st-emotion-cache-1mi2ry5 {display: none !important;}
    
    /* Сохраняем кнопку для открытия/закрытия панели со вкладками */
    button[data-testid="baseButton-header"] {
        display: flex !important;
        visibility: visible !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= ПЕРСИСТЕНТНОЕ ХРАНЕНИЕ =================
def load_storage():
    """Загружает данные из файла"""
    storage_file = Path("zornet_storage.json")
    if storage_file.exists():
        try:
            with open(storage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_storage(data):
    """Сохраняет данные в файл"""
    storage_file = Path("zornet_storage.json")
    with open(storage_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_quick_links(links):
    """Сохраняет быстрые ссылки для текущего пользователя"""
    storage = load_storage()
    if st.session_state.is_logged_in:
        username = st.session_state.user_data.get("username")
        if username:
            if "users" not in storage:
                storage["users"] = {}
            if username not in storage["users"]:
                storage["users"][username] = {}
            storage["users"][username]["quick_links"] = links
            save_storage(storage)

def load_quick_links():
    """Загружает быстрые ссылки для текущего пользователя"""
    if st.session_state.is_logged_in:
        username = st.session_state.user_data.get("username")
        if username:
            storage = load_storage()
            user_links = storage.get("users", {}).get(username, {}).get("quick_links")
            if user_links:
                return user_links
    return None

# ================= НАСТРОЙКИ =================
st.set_page_config(
    page_title="ZORNET",
    page_icon="🌐",
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
if "user_data" not in st.session_state:
    st.session_state.user_data = {}
if "user_photo" not in st.session_state:
    st.session_state.user_photo = None
if "disk_current_path" not in st.session_state:
    st.session_state.disk_current_path = None
if "disk_action" not in st.session_state:
    st.session_state.disk_action = "view"
if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
if "messages" not in st.session_state:
    st.session_state.messages = {}
if "chat_partner" not in st.session_state:
    st.session_state.chat_partner = None
if "room_messages" not in st.session_state:
    st.session_state.room_messages = {}
# Загружаем состояние входа, если есть
storage = load_storage()
if "current_auth" in storage and storage["current_auth"]["is_logged_in"]:
    st.session_state.is_logged_in = True
    st.session_state.user_data = storage["current_auth"]["user_data"]
    # Устанавливаем путь для диска при входе
    if st.session_state.user_data.get("username"):
        st.session_state.disk_current_path = f"zornet_cloud/{st.session_state.user_data['username']}"
if "quick_links" not in st.session_state:
    # Загружаем сохраненные ссылки, если пользователь авторизован
    if st.session_state.is_logged_in:
        saved_links = load_quick_links()
        if saved_links:
            st.session_state.quick_links = saved_links
        else:
            # Если нет сохраненных, используем стандартные
            st.session_state.quick_links = [
                {"name": "YouTube", "url": "https://www.youtube.com", "icon": "📺"},
                {"name": "Gmail", "url": "https://mail.google.com", "icon": "📧"},
            ]
    else:
        # Для неавторизованных пользователей - стандартные ссылки
        st.session_state.quick_links = [
            {"name": "YouTube", "url": "https://www.youtube.com", "icon": "📺"},
            {"name": "Gmail", "url": "https://mail.google.com", "icon": "📧"},
        ]

if "show_add_link" not in st.session_state:
    st.session_state.show_add_link = False
if "registration_success" not in st.session_state:
    st.session_state.registration_success = False
if "registration_message" not in st.session_state:
    st.session_state.registration_message = ""
if "new_user_email" not in st.session_state:
    st.session_state.new_user_email = ""
if "new_user_username" not in st.session_state:
    st.session_state.new_user_username = ""
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "search_results" not in st.session_state:
    st.session_state.search_results = []

# ================= ОБНОВЛЕННЫЕ CSS СТИЛИ =================
st.markdown("""
<style>
    /* ОСНОВНЫЕ СТИЛИ */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
        box-sizing: border-box;
    }
    
    /* АДАПТИВНОСТЬ ДЛЯ МОБИЛЬНЫХ УСТРОЙСТВ */
    @media (max-width: 768px) {
        .gold-title {
            font-size: 2.5rem !important;
        }
        .stButton > button {
            font-size: 0.9rem !important;
            padding: 10px !important;
        }
        .link-card {
            padding: 15px 10px !important;
        }
        .link-icon {
            font-size: 2.5rem !important;
        }
        .link-name {
            font-size: 0.9rem !important;
        }
    }
    
    @media (max-width: 480px) {
        .gold-title {
            font-size: 2rem !important;
        }
        div[data-testid="column"] {
            min-width: 100% !important;
        }
        .weather-temp {
            font-size: 3rem !important;
        }
        .weather-icon {
            font-size: 3rem !important;
        }
        .header-with-button {
            flex-direction: column !important;
            align-items: flex-start !important;
        }
    }
    
    /* ГЛАВНЫЙ ЗАГОЛОВОК */
    .gold-title {
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(135deg, #D4AF37 0%, #F5E6B3 50%, #D4AF37 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
        margin: 15px 0 25px 0;
        text-shadow: 0 5px 15px rgba(212, 175, 55, 0.2);
    }
    
    /* САЙДБАР */
    .sidebar-title {
        font-size: 2rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(135deg, #D4AF37 0%, #F5E6B3 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 10px 0 30px 0;
        letter-spacing: 2px;
    }
    
    /* СТИЛИ ДЛЯ ВСЕХ КНОПОК - СЛАБЫЙ ЗОЛОТОЙ ЦВЕТ */
    .stButton > button {
        background: white !important;
        border: 2px solid rgba(212, 175, 55, 0.3) !important;
        border-radius: 16px !important;
        color: #1a1a1a !important;
        padding: 12px 16px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 10px rgba(212, 175, 55, 0.05) !important;
        height: auto !important;
        min-height: 55px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #D4AF37, #B8860B) !important;
        color: white !important;
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(212, 175, 55, 0.2) !important;
        border-color: transparent !important;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #D4AF37, #B8860B) !important;
        color: white !important;
        border: none !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 30px rgba(212, 175, 55, 0.3) !important;
    }
    
    /* КНОПКИ В САЙДБАРЕ */
    div[data-testid="stSidebar"] div.stButton > button {
        background: transparent !important;
        border: 2px solid transparent !important;
        border-radius: 12px !important;
        color: #1a1a1a !important;
        padding: 14px 16px !important;
        font-weight: 500 !important;
        text-align: left !important;
        transition: all 0.3s ease !important;
        margin: 4px 0 !important;
        font-size: 1rem !important;
        min-height: 55px !important;
    }
    
    div[data-testid="stSidebar"] div.stButton > button:hover {
        background: linear-gradient(135deg, rgba(212, 175, 55, 0.1) 0%, rgba(212, 175, 55, 0.2) 100%) !important;
        border-color: rgba(212, 175, 55, 0.5) !important;
        transform: translateX(5px);
        color: #D4AF37 !important;
    }
    
    /* ВИДЖЕТ ВРЕМЕНИ НА ГЛАВНОЙ */
    .time-widget {
        background: white;
        border: 2px solid rgba(212, 175, 55, 0.3);
        border-radius: 16px;
        padding: 12px 16px;
        text-align: center;
        box-shadow: 0 4px 10px rgba(212, 175, 55, 0.05);
        height: 55px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        transition: all 0.3s ease;
        cursor: default;
        width: 100%;
    }
    
    .time-widget:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(212, 175, 55, 0.15);
        border-color: rgba(212, 175, 55, 0.5);
    }
    
    .time-icon {
        font-size: 1.3rem;
        color: #D4AF37;
    }
    
    .time-display {
        font-weight: 600;
        font-size: 1.1rem;
        color: #1a1a1a;
    }
    
    /* КАРТОЧКИ БЫСТРЫХ ССЫЛОК */
    .link-card {
        background: white;
        border-radius: 24px;
        padding: 25px 20px 15px 20px;
        margin: 10px 0;
        border: 2px solid rgba(212, 175, 55, 0.3);
        text-align: center;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        position: relative;
        overflow: hidden;
        box-shadow: 0 10px 25px rgba(212, 175, 55, 0.05);
    }
    
    .link-card:hover {
        transform: translateY(-5px) scale(1.02);
        border-color: rgba(212, 175, 55, 0.8);
        box-shadow: 0 20px 35px rgba(212, 175, 55, 0.15);
    }
    
    .link-icon {
        font-size: 3.5rem;
        margin-bottom: 15px;
        display: inline-block;
        transition: transform 0.3s ease;
        color: #D4AF37;
    }
    
    .link-card:hover .link-icon {
        transform: scale(1.1) rotate(5deg);
    }
    
    .link-name {
        font-weight: 700;
        font-size: 1.1rem;
        color: #1a1a1a;
        margin-bottom: 15px;
        letter-spacing: 0.3px;
    }
    
    /* КНОПКА ОТКРЫТИЯ */
    .open-link-btn {
        background: linear-gradient(135deg, #D4AF37, #B8860B) !important;
        color: white !important;
        border: none !important;
        border-radius: 40px !important;
        padding: 12px 25px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.3s ease !important;
        margin-top: 10px !important;
        margin-bottom: 5px !important;
        width: 100% !important;
        box-shadow: 0 8px 20px rgba(212, 175, 55, 0.2) !important;
    }
    
    /* КНОПКА УДАЛЕНИЯ */
    .delete-btn {
        background: linear-gradient(135deg, #ff4444, #cc0000) !important;
        color: white !important;
        border: none !important;
        border-radius: 30px !important;
        padding: 8px 12px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
        box-shadow: 0 4px 10px rgba(255, 68, 68, 0.1) !important;
    }
    
    /* ПОИСКОВАЯ СТРОКА */
    .search-container {
        margin: 30px 0;
        max-width: 600px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .search-box {
        width: 100%;
        padding: 18px 25px;
        font-size: 18px;
        border: 2px solid rgba(212, 175, 55, 0.3);
        border-radius: 30px;
        outline: none;
        transition: all 0.3s ease;
        box-shadow: 0 4px 10px rgba(212, 175, 55, 0.05);
        background-color: #ffffff;
        color: #333;
        text-align: center;
    }
    
    .search-box:focus {
        border-color: rgba(212, 175, 55, 0.8);
        box-shadow: 0 0 15px rgba(212, 175, 55, 0.15);
    }
    
    .search-box::placeholder {
        color: #999;
        font-size: 16px;
    }
    
    /* РЕЗУЛЬТАТЫ ПОИСКА */
    .search-result {
        background: white;
        border: 2px solid rgba(212, 175, 55, 0.3);
        border-radius: 20px;
        padding: 20px;
        margin-bottom: 15px;
        transition: all 0.3s ease;
    }
    
    .search-result:hover {
        transform: translateY(-3px);
        border-color: rgba(212, 175, 55, 0.8);
        box-shadow: 0 10px 25px rgba(212, 175, 55, 0.1);
    }
    
    .search-result-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #D4AF37;
        margin-bottom: 5px;
        text-decoration: none;
        display: block;
    }
    
    .search-result-title:hover {
        text-decoration: underline;
    }
    
    .search-result-url {
        color: #006621;
        font-size: 0.85rem;
        margin-bottom: 8px;
        word-break: break-all;
    }
    
    .search-result-description {
        color: #545454;
        line-height: 1.5;
        font-size: 0.95rem;
    }
    
    .search-header {
        background: linear-gradient(135deg, #D4AF37, #B8860B);
        padding: 15px 30px;
        border-radius: 30px;
        color: white;
        margin-bottom: 30px;
        text-align: center;
        font-size: 1.5rem;
        font-weight: 700;
    }
    
    .search-stats {
        color: #666;
        margin-bottom: 20px;
        font-size: 0.95rem;
    }
    
    .search-back-button {
        display: inline-block;
        background: white;
        border: 2px solid rgba(212, 175, 55, 0.3);
        color: #D4AF37;
        padding: 10px 20px;
        border-radius: 30px;
        font-weight: 600;
        text-decoration: none;
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    
    .search-back-button:hover {
        background: linear-gradient(135deg, #D4AF37, #B8860B);
        color: white;
        border-color: transparent;
    }
    
    /* КАРТОЧКИ ПОГОДЫ */
    .weather-main-card {
        background: linear-gradient(135deg, #D4AF37 0%, #B8860B 100%);
        border-radius: 24px;
        padding: 30px;
        color: white;
        box-shadow: 0 20px 40px rgba(212, 175, 55, 0.2);
        border: 2px solid rgba(255, 255, 255, 0.2);
        margin-bottom: 20px;
    }
    
    .weather-temp {
        font-size: 5rem;
        font-weight: 800;
        line-height: 1;
        text-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    .weather-icon {
        font-size: 5rem;
        filter: drop-shadow(0 10px 20px rgba(0,0,0,0.2));
    }
    
    .weather-detail-item {
        background: white;
        border: 2px solid rgba(212, 175, 55, 0.3);
        border-radius: 16px;
        padding: 15px;
        color: #1a1a1a;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: 0 4px 10px rgba(212, 175, 55, 0.05);
    }
    
    .weather-detail-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(212, 175, 55, 0.15);
        border-color: rgba(212, 175, 55, 0.8);
    }
    
    /* КАРТОЧКИ НОВОСТЕЙ */
    .news-card {
        background: white;
        border-radius: 20px;
        padding: 25px;
        margin-bottom: 20px;
        border: 2px solid rgba(212, 175, 55, 0.3);
        transition: all 0.3s ease;
        box-shadow: 0 5px 20px rgba(212, 175, 55, 0.05);
    }
    
    .news-card:hover {
        transform: translateY(-5px);
        border-color: rgba(212, 175, 55, 0.8);
        box-shadow: 0 15px 30px rgba(212, 175, 55, 0.15);
    }
    
    .news-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 15px;
        line-height: 1.4;
    }
    
    .news-summary {
        color: #666;
        line-height: 1.6;
        font-size: 0.95rem;
    }
    
    /* ЧАТ МЕССЕНДЖЕРА */
    .contact-item {
        padding: 15px 20px;
        border: 2px solid rgba(212, 175, 55, 0.2);
        border-radius: 12px;
        margin-bottom: 8px;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 12px;
        background: white;
    }
    
    .contact-item:hover {
        border-color: rgba(212, 175, 55, 0.8);
        transform: translateX(5px);
        box-shadow: 0 5px 15px rgba(212, 175, 55, 0.1);
    }
    
    .contact-item.active {
        background: linear-gradient(135deg, rgba(212, 175, 55, 0.1), rgba(212, 175, 55, 0.15));
        border-color: rgba(212, 175, 55, 0.8);
    }
    
    .contact-avatar {
        width: 45px;
        height: 45px;
        border-radius: 12px;
        background: linear-gradient(135deg, #D4AF37, #B8860B);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 700;
        font-size: 1.2rem;
    }
    
    .message-bubble {
        max-width: 70%;
        padding: 12px 18px;
        border-radius: 20px;
        margin-bottom: 10px;
        position: relative;
        animation: messageAppear 0.3s ease;
        border: 2px solid transparent;
    }
    
    .message-bubble.you {
        background: linear-gradient(135deg, #D4AF37, #B8860B);
        color: white;
        margin-left: auto;
        border-bottom-right-radius: 4px;
    }
    
    .message-bubble.other {
        background: white;
        color: #1a1a1a;
        margin-right: auto;
        border-bottom-left-radius: 4px;
        border-color: rgba(212, 175, 55, 0.3);
    }
    
    /* ДИСК */
    .disk-stats-card {
        background: linear-gradient(135deg, #D4AF37, #B8860B);
        border-radius: 20px;
        padding: 25px;
        color: white;
        margin-bottom: 20px;
        border: 2px solid rgba(255, 255, 255, 0.2);
    }
    
    .file-item {
        background: white;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        border: 2px solid rgba(212, 175, 55, 0.3);
        transition: all 0.3s ease;
        margin-bottom: 10px;
    }
    
    .file-item:hover {
        transform: translateY(-5px);
        border-color: rgba(212, 175, 55, 0.8);
        box-shadow: 0 10px 25px rgba(212, 175, 55, 0.15);
    }
    
    /* ПРОФИЛЬ */
    .profile-card {
        background: transparent;
        padding: 20px;
        text-align: center;
        max-width: 500px;
        margin: 0 auto;
    }
    
    .profile-avatar {
        width: 120px;
        height: 120px;
        border-radius: 30px;
        background: linear-gradient(135deg, #D4AF37, #B8860B);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 3rem;
        font-weight: 700;
        margin: 0 auto 20px;
        border: 4px solid rgba(212, 175, 55, 0.5);
        box-shadow: 0 10px 30px rgba(212, 175, 55, 0.2);
    }
    
    .profile-name {
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 5px;
        background: linear-gradient(135deg, #D4AF37, #B8860B);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .profile-username {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 20px;
    }
    
    .profile-email {
        background: linear-gradient(135deg, rgba(212, 175, 55, 0.1), rgba(184, 134, 11, 0.1));
        padding: 12px 20px;
        border-radius: 50px;
        display: inline-block;
        color: #D4AF37;
        font-weight: 600;
        border: 2px solid rgba(212, 175, 55, 0.3);
    }
    
    /* ФОРМЫ ВХОДА/РЕГИСТРАЦИИ */
    .auth-container {
        max-width: 450px;
        margin: 0 auto;
        background: white;
        border-radius: 30px;
        padding: 40px;
        box-shadow: 0 20px 40px rgba(212, 175, 55, 0.1);
        border: 2px solid rgba(212, 175, 55, 0.3);
    }
    
    /* ИНПУТЫ */
    .stTextInput > div > div > input {
        border-radius: 16px !important;
        border: 2px solid rgba(212, 175, 55, 0.3) !important;
        padding: 12px 20px !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
        background: white !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: rgba(212, 175, 55, 0.8) !important;
        box-shadow: 0 0 0 4px rgba(212, 175, 55, 0.1) !important;
    }
    
    /* РАЗДЕЛИТЕЛИ */
    hr {
        margin: 30px 0 !important;
        border: none !important;
        height: 2px !important;
        background: linear-gradient(90deg, transparent, rgba(212, 175, 55, 0.3), transparent) !important;
    }
    
    /* АНИМАЦИИ */
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .fade-in {
        animation: fadeIn 0.5s ease;
    }
    
    /* ЗАГОЛОВОК НОВОСТЕЙ */
    .news-header {
        font-size: 2rem;
        font-weight: 700;
        color: #D4AF37;
        margin-bottom: 20px;
        text-align: center;
    }
    
    /* КОНТЕЙНЕР ДЛЯ ЗАГОЛОВКА С КНОПКОЙ */
    .header-with-button {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        flex-wrap: wrap;
        gap: 10px;
    }
    
    .header-with-button h3 {
        margin: 0;
        color: #D4AF37;
        font-size: 1.5rem;
        font-weight: 600;
    }
    
    /* КНОПКА В ЗАГОЛОВКЕ */
    .header-button {
        background: white !important;
        border: 2px solid rgba(212, 175, 55, 0.3) !important;
        color: #D4AF37 !important;
        padding: 8px 20px !important;
        border-radius: 30px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 10px rgba(212, 175, 55, 0.05) !important;
        height: 40px !important;
        min-height: 40px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    .header-button:hover {
        background: linear-gradient(135deg, #D4AF37, #B8860B) !important;
        color: white !important;
        transform: translateY(-2px);
        border-color: transparent !important;
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
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Сообщения мессенджера
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_username TEXT NOT NULL,
            receiver_username TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Комнаты совместного просмотра
    c.execute("""
        CREATE TABLE IF NOT EXISTS watch_rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            youtube_url TEXT NOT NULL,
            password TEXT NOT NULL,
            owner_username TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Сообщения в комнатах
    c.execute("""
        CREATE TABLE IF NOT EXISTS room_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL,
            username TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def register_user(email, username, first_name, last_name, password):
    """Регистрация пользователя"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    try:
        # Проверяем почту
        c.execute("SELECT email FROM users WHERE LOWER(email) = LOWER(?)", (email,))
        if c.fetchone():
            return {"success": False, "message": "Email уже используется"}
        
        # Проверяем никнейм (без учета регистра)
        c.execute("SELECT username FROM users WHERE LOWER(username) = LOWER(?)", (username,))
        if c.fetchone():
            return {"success": False, "message": "Никнейм уже занят"}
        
        # Проверяем длину пароля
        if len(password) < 6:
            return {"success": False, "message": "Пароль должен быть не менее 6 символов"}
        
        # Проверяем валидность email
        if '@' not in email or '.' not in email:
            return {"success": False, "message": "Неверный формат email"}
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        c.execute("""
            INSERT INTO users (email, username, first_name, last_name, password_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (email.strip(), username.strip(), first_name.strip(), 
              last_name.strip() if last_name else "", password_hash))
        
        conn.commit()
        
        # Создаем папку для пользователя в облачном хранилище
        user_folder = Path(f"zornet_cloud/{username}")
        user_folder.mkdir(parents=True, exist_ok=True)
        
        return {
            "success": True, 
            "message": "Аккаунт успешно создан!",
            "email": email,
            "username": username
        }
    except sqlite3.IntegrityError as e:
        error_msg = str(e)
        if "UNIQUE constraint failed: users.email" in error_msg:
            return {"success": False, "message": "Email уже используется"}
        elif "UNIQUE constraint failed: users.username" in error_msg:
            return {"success": False, "message": "Никнейм уже занят"}
        else:
            return {"success": False, "message": f"Ошибка регистрации: {error_msg}"}
    except Exception as e:
        return {"success": False, "message": f"Ошибка: {str(e)}"}
    finally:
        conn.close()

def login_user(email, password):
    """Вход пользователя"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    try:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        c.execute("""
            SELECT id, email, username, first_name, last_name
            FROM users 
            WHERE email = ? AND password_hash = ?
        """, (email, password_hash))
        
        user = c.fetchone()
        
        if user:
            return {
                "id": user[0],
                "email": user[1],
                "username": user[2],
                "first_name": user[3],
                "last_name": user[4]
            }
        return None
    finally:
        conn.close()

def get_user_by_username(username):
    """Поиск пользователя по никнейму"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    c.execute("""
        SELECT id, email, username, first_name, last_name
        FROM users 
        WHERE username = ?
    """, (username,))
    
    user = c.fetchone()
    conn.close()
    
    if user:
        return {
            "id": user[0],
            "email": user[1],
            "username": user[2],
            "first_name": user[3],
            "last_name": user[4]
        }
    return None

def save_chat_message(sender, receiver, message):
    """Сохранение сообщения в чате"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO chat_messages (sender_username, receiver_username, message)
        VALUES (?, ?, ?)
    """, (sender, receiver, message))
    
    conn.commit()
    conn.close()

def save_room_message_to_db(room_id, username, message):
    """Сохранение сообщения в комнате в БД"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO room_messages (room_id, username, message)
        VALUES (?, ?, ?)
    """, (room_id, username, message))
    
    conn.commit()
    conn.close()

def save_room_message(room_id, username, message):
    """Сохранение сообщения в комнате"""
    if room_id not in st.session_state.room_messages:
        st.session_state.room_messages[room_id] = []
    
    st.session_state.room_messages[room_id].append({
        "username": username,
        "message": message,
        "timestamp": datetime.datetime.now().strftime("%H:%M")
    })

def get_chat_history(user1, user2):
    """Получение истории чата"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    c.execute("""
        SELECT sender_username, receiver_username, message, timestamp
        FROM chat_messages
        WHERE (sender_username = ? AND receiver_username = ?)
           OR (sender_username = ? AND receiver_username = ?)
        ORDER BY timestamp ASC
    """, (user1, user2, user2, user1))
    
    messages = c.fetchall()
    conn.close()
    
    return messages

def create_watch_room(room_id, name, youtube_url, password, owner_username):
    """Создание комнаты в БД"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    try:
        c.execute("""
            INSERT INTO watch_rooms (room_id, name, youtube_url, password, owner_username)
            VALUES (?, ?, ?, ?, ?)
        """, (room_id, name, youtube_url, password, owner_username))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка создания комнаты: {e}")
        return False
    finally:
        conn.close()

def get_watch_room(room_id, password):
    """Получение комнаты из БД"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    c.execute("""
        SELECT room_id, name, youtube_url, password, owner_username
        FROM watch_rooms 
        WHERE room_id = ? AND password = ?
    """, (room_id, password))
    
    room = c.fetchone()
    conn.close()
    
    if room:
        return {
            "id": room[0],
            "name": room[1],
            "youtube_url": room[2],
            "password": room[3],
            "owner": room[4]
        }
    return None

def get_all_watch_rooms():
    """Получение всех комнат из БД"""
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    
    c.execute("SELECT room_id, name, youtube_url, password, owner_username FROM watch_rooms")
    rooms = c.fetchall()
    conn.close()
    
    return [
        {
            "id": room[0],
            "name": room[1],
            "youtube_url": room[2],
            "password": room[3],
            "owner": room[4]
        }
        for room in rooms
    ]

# ================= ПОИСКОВАЯ СИСТЕМА ZORNET =================
def search_zornet(query):
    """Реальный поиск через Google Custom Search API"""
    if not query:
        return []
    
    try:
        # Используем публичный API для поиска
        # В реальном проекте нужно заменить на свой API ключ
        api_key = "AIzaSyD7VJxK3GqVxY5Q5X5Q5X5Q5X5Q5X5Q5X5"  # Замените на реальный ключ
        search_engine_id = "017576662512468239146:omuauf_lfve"  # Замените на свой ID
        
        url = f"https://www.googleapis.com/customsearch/v1?q={urllib.parse.quote(query)}&key={api_key}&cx={search_engine_id}&num=10"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            for item in data.get("items", []):
                results.append({
                    "title": item.get("title", "Без названия"),
                    "url": item.get("link", "#"),
                    "description": item.get("snippet", "Нет описания")
                })
            
            return results
        else:
            # Если API не работает, используем демо-результаты
            return get_demo_search_results(query)
            
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return get_demo_search_results(query)

def get_demo_search_results(query):
    """Демо-результаты для примера"""
    return [
        {
            "title": f"{query} — Википедия",
            "url": f"https://ru.wikipedia.org/wiki/{urllib.parse.quote(query)}",
            "description": f"Статья о {query} в свободной энциклопедии"
        },
        {
            "title": f"{query} — Яндекс",
            "url": f"https://yandex.ru/search/?text={urllib.parse.quote(query)}",
            "description": f"Результаты поиска в Яндексе по запросу {query}"
        },
        {
            "title": f"{query} — Google",
            "url": f"https://www.google.com/search?q={urllib.parse.quote(query)}",
            "description": f"Результаты поиска в Google по запросу {query}"
        },
        {
            "title": f"{query} — YouTube",
            "url": f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}",
            "description": f"Видео по запросу {query} на YouTube"
        },
        {
            "title": f"{query} — Habr",
            "url": f"https://habr.com/ru/search/?q={urllib.parse.quote(query)}",
            "description": f"Статьи и публикации о {query} на Habr"
        }
    ]

# ================= САЙДБАР =================
with st.sidebar:
    st.markdown('<div class="sidebar-title">ZORNET</div>', unsafe_allow_html=True)
    
    if st.session_state.is_logged_in:
        user = st.session_state.user_data
        st.markdown(f"""
        <div style="background: white; border: 2px solid rgba(212, 175, 55, 0.3); border-radius: 16px; padding: 15px; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="width: 45px; height: 45px; border-radius: 12px; background: linear-gradient(135deg, #D4AF37, #B8860B); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 1.2rem;">
                    {user.get('first_name', 'U')[0]}
                </div>
                <div>
                    <div style="font-weight: 700; color: #1a1a1a;">{user.get('first_name', '')} {user.get('last_name', '')}</div>
                    <div style="font-size: 0.8rem; color: #D4AF37;">@{user.get('username', '')}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    pages = [
        ("🏠", "Главная"),
        ("📰", "Новости"),
        ("🌤️", "Погода"),
        ("💬", "Мессенджер"),
        ("🎬", "Кинотеатр"),
        ("💾", "Диск"),
        ("👤", "Профиль"),
    ]
    
    for icon, page in pages:
        if st.button(f"{icon} {page}", key=f"nav_{page}", use_container_width=True):
            st.session_state.page = page
            st.rerun()

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

def get_weather_by_city(city_name):
    API_KEY = "20ebdd8243b8a3a29abe332fefdadb44"
    
    try:
        geocode_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={API_KEY}"
        geocode_response = requests.get(geocode_url, timeout=10)
        
        if geocode_response.status_code == 200 and geocode_response.json():
            city_data = geocode_response.json()[0]
            lat = city_data["lat"]
            lon = city_data["lon"]
            
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
    except Exception as e:
        print(f"Ошибка получения погоды: {e}")
    
    return None

# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================
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
    st.markdown('<div class="gold-title fade-in">ZORNET</div>', unsafe_allow_html=True)
    
    current_time = datetime.datetime.now(pytz.timezone('Europe/Minsk')).strftime('%H:%M')
    
    # Верхняя панель с кнопками
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="time-widget">
            <span class="time-icon">🕒</span>
            <span class="time-display">{current_time}</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.button("⛅ Погода", use_container_width=True):
            st.session_state.page = "Погода"
            st.rerun()
    
    with col3:
        if st.button("💬 Мессенджер", use_container_width=True):
            st.session_state.page = "Мессенджер"
            st.rerun()
    
    with col4:
        if st.button("📰 Новости", use_container_width=True):
            st.session_state.page = "Новости"
            st.rerun()
    
    st.markdown("---")
    
    # Поиск ZORNET
    with st.form("search_form"):
        col_search, col_button = st.columns([4, 1])
        with col_search:
            search_input = st.text_input("", placeholder="🔍 Поиск в ZORNET...", label_visibility="collapsed", key="main_search")
        with col_button:
            submitted = st.form_submit_button("Найти", use_container_width=True, type="primary")
        
        if submitted and search_input:
            st.session_state.search_query = search_input
            with st.spinner("🔍 Ищем..."):
                st.session_state.search_results = search_zornet(search_input)
            st.session_state.page = "Поиск"
            st.rerun()
    
    st.markdown("---")
    
    # Быстрые ссылки с кнопкой добавления на одном уровне
    col_header, col_button = st.columns([3, 1])
    
    with col_header:
        st.markdown("### 📌 Быстрые ссылки")
    
    with col_button:
        if st.button("➕ Добавить", key="add_link_main", use_container_width=True):
            st.session_state.show_add_link = not st.session_state.show_add_link
            st.rerun()
    
    quick_links = st.session_state.quick_links
    
    if not quick_links:
        st.info("📭 Нет быстрых ссылок. Добавьте первую!")
    else:
        # Показываем ссылки в сетке 4 колонки
        for i in range(0, len(quick_links), 4):
            cols = st.columns(4)
            row_links = quick_links[i:i+4]
            
            for j, link in enumerate(row_links):
                with cols[j]:
                    # Карточка ссылки
                    st.markdown(f"""
                    <div class="link-card">
                        <div class="link-icon">{link.get('icon', '🔗')}</div>
                        <div class="link-name">{link['name']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Две кнопки рядом
                    col_btn1, col_btn2 = st.columns([3, 1])
                    with col_btn1:
                        if st.button("🌐 Открыть", key=f"open_{link['name']}_{i}_{j}", use_container_width=True):
                            js_code = f'window.open("{link["url"]}", "_blank");'
                            components.html(f"<script>{js_code}</script>", height=0)
                    
                    with col_btn2:
                        if st.button("✕", key=f"delete_{link['name']}_{i}_{j}", use_container_width=True):
                            st.session_state.quick_links.remove(link)
                            save_quick_links(st.session_state.quick_links)
                            st.rerun()
    
    # Форма добавления ссылки
    if st.session_state.show_add_link:
        with st.form("add_link_form"):
            st.markdown("### Новая ссылка")
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Название")
                new_icon = st.selectbox("Иконка", ["🔍", "📺", "📧", "🤖", "💻", "🌐", "🎮", "📚", "🎵", "🛒"])
            with col2:
                new_url = st.text_input("URL")
            
            if st.form_submit_button("💾 Сохранить", use_container_width=True):
                if new_name and new_url:
                    if not new_url.startswith(('http://', 'https://')):
                        new_url = 'https://' + new_url
                    
                    st.session_state.quick_links.append({
                        "name": new_name,
                        "url": new_url,
                        "icon": new_icon
                    })
                    save_quick_links(st.session_state.quick_links)
                    st.session_state.show_add_link = False
                    st.rerun()

# ================= СТРАНИЦА ПОИСКА =================
elif st.session_state.page == "Поиск":
    # Кнопка возврата на главную
    if st.button("← Вернуться на главную", key="back_to_main", use_container_width=False):
        st.session_state.page = "Главная"
        st.rerun()
    
    # Заголовок поиска
    st.markdown(f"""
    <div class="search-header">
        🔍 ZORNET ПОИСК: {st.session_state.search_query}
    </div>
    """, unsafe_allow_html=True)
    
    # Строка поиска на странице результатов
    with st.form("search_results_form"):
        col_search, col_button = st.columns([4, 1])
        with col_search:
            new_search = st.text_input("", value=st.session_state.search_query, placeholder="Новый поиск...", label_visibility="collapsed")
        with col_button:
            new_submitted = st.form_submit_button("Найти", use_container_width=True, type="primary")
        
        if new_submitted and new_search:
            st.session_state.search_query = new_search
            with st.spinner("🔍 Ищем..."):
                st.session_state.search_results = search_zornet(new_search)
            st.rerun()
    
    st.markdown("---")
    
    # Результаты поиска
    if st.session_state.search_results:
        st.markdown(f"""
        <div class="search-stats">
            Найдено результатов: {len(st.session_state.search_results)}
        </div>
        """, unsafe_allow_html=True)
        
        for i, result in enumerate(st.session_state.search_results):
            st.markdown(f"""
            <div class="search-result">
                <a href="{result['url']}" target="_blank" class="search-result-title">{result['title']}</a>
                <div class="search-result-url">{result['url']}</div>
                <div class="search-result-description">{result['description']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Ничего не найдено. Попробуйте изменить запрос.")

# ================= МЕССЕНДЖЕР =================
elif st.session_state.page == "Мессенджер":
    st.markdown('<div class="gold-title fade-in">💬 МЕССЕНДЖЕР</div>', unsafe_allow_html=True)
    
    if not st.session_state.is_logged_in:
        st.warning("⚠️ Для использования мессенджера войдите в систему")
        if st.button("Перейти к входу", type="primary"):
            st.session_state.page = "Профиль"
            st.rerun()
        st.stop()
    
    # Создаем две колонки
    col_contacts, col_chat = st.columns([1, 2])
    
    with col_contacts:
        # Просто поиск без заголовка
        search_username = st.text_input("", placeholder="@username", label_visibility="collapsed")
        
        if st.button("🔍 Найти пользователя", use_container_width=True, type="primary"):
            if search_username:
                if search_username == st.session_state.user_data.get("username"):
                    st.error("Нельзя написать самому себе")
                else:
                    user = get_user_by_username(search_username)
                    if user:
                        st.session_state.chat_partner = user
                        st.success(f"✅ Найден: {user['first_name']}")
                    else:
                        st.error("❌ Пользователь не найден")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Контакты")
        
        # Пример контактов
        contacts = [
            {"id": 2, "username": "alex", "first_name": "Алексей", "last_name": "Петров"},
            {"id": 3, "username": "marina", "first_name": "Марина", "last_name": "Иванова"},
        ]
        
        for contact in contacts:
            is_active = st.session_state.chat_partner and st.session_state.chat_partner.get("username") == contact["username"]
            active_class = "active" if is_active else ""
            
            st.markdown(f"""
            <div class="contact-item {active_class}" onclick="document.getElementById('contact_{contact['id']}').click()">
                <div class="contact-avatar">{contact['first_name'][0]}</div>
                <div>
                    <div style="font-weight: 600;">{contact['first_name']} {contact['last_name']}</div>
                    <div style="font-size: 0.8rem; color: #D4AF37;">@{contact['username']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Скрытая кнопка для клика
            if st.button("", key=f"contact_{contact['id']}", help=contact['username']):
                st.session_state.chat_partner = contact
                st.rerun()
    
    with col_chat:
        if st.session_state.chat_partner:
            partner = st.session_state.chat_partner
            current_user = st.session_state.user_data.get("username", "")
            partner_user = partner.get("username", "")
            chat_key = f"{current_user}_{partner_user}"
            
            # Заголовок чата
            st.markdown(f"""
            <div style="background: white; border-radius: 20px; padding: 15px; margin-bottom: 20px; border: 2px solid rgba(212, 175, 55, 0.3); display: flex; align-items: center; gap: 15px;">
                <div style="width: 45px; height: 45px; border-radius: 12px; background: linear-gradient(135deg, #D4AF37, #B8860B); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 1.3rem;">
                    {partner.get('first_name', '?')[0]}
                </div>
                <div>
                    <div style="font-weight: 700; font-size: 1.1rem;">{partner.get('first_name', '')} {partner.get('last_name', '')}</div>
                    <div style="color: #D4AF37; font-size: 0.9rem;">@{partner.get('username', '')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Загружаем сообщения
            if chat_key not in st.session_state.messages:
                db_messages = get_chat_history(current_user, partner_user)
                st.session_state.messages[chat_key] = []
                for msg in db_messages:
                    st.session_state.messages[chat_key].append({
                        "sender": msg[0],
                        "receiver": msg[1],
                        "text": msg[2],
                        "time": msg[3]
                    })
            
            # Контейнер для сообщений
            messages_container = st.container(height=400)
            with messages_container:
                for msg in st.session_state.messages.get(chat_key, []):
                    is_you = msg.get("sender") == current_user
                    msg_text = msg.get("text", "")
                    msg_time = msg.get("time", "")
                    time_display = msg_time.split(" ")[1][:5] if " " in msg_time else msg_time[:5]
                    
                    st.markdown(f"""
                    <div class="message-bubble {'you' if is_you else 'other'}">
                        <div>{msg_text}</div>
                        <div class="message-time">{time_display}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Поле ввода
            col_input, col_send = st.columns([5, 1])
            with col_input:
                new_message = st.text_input("", placeholder="Введите сообщение...", key="chat_input", label_visibility="collapsed")
            with col_send:
                if st.button("📤", use_container_width=True, type="primary"):
                    if new_message:
                        save_chat_message(current_user, partner_user, new_message)
                        st.session_state.messages[chat_key].append({
                            "sender": current_user,
                            "receiver": partner_user,
                            "text": new_message,
                            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.rerun()
        else:
            st.markdown("""
            <div style="background: white; border-radius: 20px; padding: 60px 20px; text-align: center; border: 2px solid rgba(212, 175, 55, 0.3);">
                <div style="font-size: 4rem; margin-bottom: 20px;">💬</div>
                <h3>Выберите контакт для начала общения</h3>
                <p style="color: #D4AF37;">Найдите пользователя по никнейму или выберите из списка контактов</p>
            </div>
            """, unsafe_allow_html=True)

# ================= КИНОТЕАТР =================
elif st.session_state.page == "Кинотеатр":
    st.markdown('<div class="gold-title fade-in">🎬 КИНОТЕАТР</div>', unsafe_allow_html=True)
    
    if not st.session_state.is_logged_in:
        st.warning("⚠️ Для создания комнат войдите в систему")
        if st.button("Перейти к входу", type="primary"):
            st.session_state.page = "Профиль"
            st.rerun()
    else:
        # Если пользователь уже в комнате
        if st.session_state.get("watch_room"):
            room_id = st.session_state.watch_room
            
            # Получаем комнату
            room_data = None
            for room in st.session_state.rooms:
                if room["id"] == room_id:
                    room_data = room
                    break
            
            if room_data:
                # Извлекаем ID видео
                video_url = room_data.get("youtube_url", "")
                video_id = None
                
                patterns = [
                    r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([0-9A-Za-z_-]{11})',
                    r'youtube\.com\/embed\/([0-9A-Za-z_-]{11})',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, video_url)
                    if match:
                        video_id = match.group(1)
                        break
                
                # Информация о комнате
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #D4AF37, #B8860B); border-radius: 20px; padding: 20px; color: white; margin-bottom: 20px;">
                    <h2 style="margin: 0 0 5px 0;">{room_data['name']}</h2>
                    <p style="margin: 0; opacity: 0.9;">ID: {room_id} | Создатель: @{room_data['owner']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # YouTube плеер
                if video_id:
                    components.html(f"""
                    <div style="border-radius: 20px; overflow: hidden; margin-bottom: 20px; border: 2px solid rgba(212, 175, 55, 0.3);">
                        <iframe width="100%" height="500" 
                                src="https://www.youtube.com/embed/{video_id}?autoplay=1"
                                frameborder="0" 
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                                allowfullscreen>
                        </iframe>
                    </div>
                    """, height=520)
                
                # Чат комнаты
                st.markdown("### Чат комнаты")
                
                room_chat_key = f"room_{room_id}"
                if room_chat_key not in st.session_state.room_messages:
                    st.session_state.room_messages[room_chat_key] = [{
                        "username": "Система",
                        "message": f"Добро пожаловать в комнату!",
                        "timestamp": datetime.datetime.now().strftime("%H:%M")
                    }]
                
                # Контейнер для сообщений
                chat_container = st.container(height=200)
                with chat_container:
                    for msg in st.session_state.room_messages[room_chat_key]:
                        username = msg.get("username", "")
                        message = msg.get("message", "")
                        timestamp = msg.get("timestamp", "")
                        
                        st.markdown(f"""
                        <div style="background: {'#fff9e6' if username == 'Система' else 'white'}; border: 2px solid rgba(212, 175, 55, 0.3); padding: 10px 15px; border-radius: 15px; margin: 5px 0;">
                            <div><strong>{username}:</strong> {message}</div>
                            <div style="font-size: 0.7rem; color: #666; text-align: right;">{timestamp}</div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Отправка сообщения
                col_msg, col_send = st.columns([5, 1])
                with col_msg:
                    room_message = st.text_input("", placeholder="Сообщение...", key="room_msg", label_visibility="collapsed")
                with col_send:
                    if st.button("📤", use_container_width=True):
                        if room_message.strip():
                            username = st.session_state.user_data.get("username", "Гость")
                            save_room_message(room_chat_key, username, room_message)
                            st.rerun()
                
                # Кнопка выхода
                if st.button("← Выйти из комнаты", use_container_width=True, type="primary"):
                    st.session_state.watch_room = None
                    st.rerun()
                
                st.stop()
        
        # Создание/присоединение к комнате
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div style="background: white; border-radius: 20px; padding: 25px; border: 2px solid rgba(212, 175, 55, 0.3); margin-bottom: 20px;">
                <h3 style="color: #D4AF37;">🎥 Создать комнату</h3>
            </div>
            """, unsafe_allow_html=True)
            
            room_name = st.text_input("Название комнаты", value="Моя комната")
            youtube_url = st.text_input("YouTube ссылка", placeholder="https://youtube.com/watch?v=...")
            room_password = st.text_input("Пароль комнаты", type="password")
            
            if st.button("✨ Создать комнату", use_container_width=True, type="primary"):
                if room_name and youtube_url and room_password:
                    room_id = str(uuid.uuid4())[:8]
                    owner = st.session_state.user_data.get("username", "Гость")
                    
                    if create_watch_room(room_id, room_name, youtube_url, room_password, owner):
                        st.session_state.rooms.append({
                            "id": room_id,
                            "name": room_name,
                            "youtube_url": youtube_url,
                            "password": room_password,
                            "owner": owner
                        })
                        st.session_state.watch_room = room_id
                        st.success(f"✅ Комната создана! ID: {room_id}")
                        st.rerun()
        
        with col2:
            st.markdown("""
            <div style="background: white; border-radius: 20px; padding: 25px; border: 2px solid rgba(212, 175, 55, 0.3); margin-bottom: 20px;">
                <h3 style="color: #D4AF37;">🔗 Присоединиться</h3>
            </div>
            """, unsafe_allow_html=True)
            
            join_id = st.text_input("ID комнаты")
            join_password = st.text_input("Пароль комнаты", type="password")
            
            if st.button("🚪 Войти в комнату", use_container_width=True, type="primary"):
                if join_id and join_password:
                    room_data = get_watch_room(join_id, join_password)
                    
                    if room_data:
                        st.session_state.rooms.append({
                            "id": room_data["id"],
                            "name": room_data["name"],
                            "youtube_url": room_data["youtube_url"],
                            "password": room_data["password"],
                            "owner": room_data["owner"]
                        })
                        st.session_state.watch_room = room_data["id"]
                        st.rerun()
                    else:
                        st.error("❌ Комната не найдена или неверный пароль")

# ================= ДИСК =================
elif st.session_state.page == "Диск":
    st.markdown('<div class="gold-title fade-in">💾 ДИСК</div>', unsafe_allow_html=True)
    
    if not st.session_state.is_logged_in:
        st.warning("⚠️ Для использования диска войдите в систему")
        if st.button("Перейти к входу", type="primary"):
            st.session_state.page = "Профиль"
            st.rerun()
        st.stop()
    
    # Устанавливаем путь для пользователя
    username = st.session_state.user_data.get("username")
    if not st.session_state.disk_current_path:
        st.session_state.disk_current_path = f"zornet_cloud/{username}"
    
    # Создаем папку пользователя если не существует
    os.makedirs(st.session_state.disk_current_path, exist_ok=True)
    
    # Функции для работы с диском
    def format_size(size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def get_stats():
        total = 0
        files = 0
        folders = 0
        for root, dirs, files_list in os.walk(st.session_state.disk_current_path):
            folders += len(dirs)
            for file in files_list:
                files += 1
                total += os.path.getsize(os.path.join(root, file))
        return total, files, folders
    
    # Статистика
    total_size, file_count, folder_count = get_stats()
    
    st.markdown(f"""
    <div class="disk-stats-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
            <h3 style="margin: 0; color: white;">📊 Статистика {username}</h3>
            <span style="background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 30px;">{format_size(total_size)} / 1 GB</span>
        </div>
        <div style="background: rgba(255,255,255,0.2); height: 8px; border-radius: 4px; margin-bottom: 15px;">
            <div style="width: {min(100, (total_size / (1024**3)) * 100)}%; height: 100%; background: white; border-radius: 4px;"></div>
        </div>
        <div style="display: flex; gap: 20px; flex-wrap: wrap;">
            <div>📁 Папок: {folder_count}</div>
            <div>📄 Файлов: {file_count}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Панель инструментов
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📤 Загрузить", use_container_width=True):
            st.session_state.disk_action = "upload"
    
    with col2:
        if st.button("📁 Новая папка", use_container_width=True):
            st.session_state.disk_action = "new_folder"
    
    with col3:
        if st.button("🔍 Поиск", use_container_width=True):
            st.session_state.disk_action = "search"
    
    with col4:
        if st.button("🔄 Обновить", use_container_width=True):
            st.rerun()
    
    st.markdown("---")
    
    # Действия
    if st.session_state.disk_action == "upload":
        st.markdown("### 📤 Загрузка файлов")
        uploaded_files = st.file_uploader("Выберите файлы", accept_multiple_files=True)
        if uploaded_files:
            for file in uploaded_files:
                file_path = os.path.join(st.session_state.disk_current_path, file.name)
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
            st.success(f"✅ Загружено {len(uploaded_files)} файлов!")
            st.session_state.disk_action = "view"
            st.rerun()
    
    elif st.session_state.disk_action == "new_folder":
        st.markdown("### 📁 Создание папки")
        folder_name = st.text_input("Название папки")
        if st.button("✅ Создать", use_container_width=True, type="primary"):
            if folder_name:
                os.makedirs(os.path.join(st.session_state.disk_current_path, folder_name), exist_ok=True)
                st.success(f"✅ Папка '{folder_name}' создана!")
                st.session_state.disk_action = "view"
                st.rerun()
    
    elif st.session_state.disk_action == "search":
        st.markdown("### 🔍 Поиск")
        query = st.text_input("Введите название")
        if query:
            results = []
            for root, dirs, files in os.walk(st.session_state.disk_current_path):
                for name in dirs + files:
                    if query.lower() in name.lower():
                        results.append(os.path.join(root, name))
            
            if results:
                st.markdown(f"**Найдено {len(results)}:**")
                for res in results[:10]:
                    st.markdown(f"📄 {os.path.basename(res)}")
            else:
                st.info("Ничего не найдено")
    
    else:
        # Просмотр файлов
        st.markdown("### 📁 Файлы и папки")
        
        # Навигация
        current_path = st.session_state.disk_current_path
        if current_path != f"zornet_cloud/{username}":
            if st.button("← Назад", use_container_width=True):
                st.session_state.disk_current_path = os.path.dirname(current_path)
                st.rerun()
        
        try:
            items = os.listdir(current_path)
        except:
            items = []
        
        if not items:
            st.info("📭 Папка пуста")
        else:
            # Сортируем: папки сверху
            items.sort(key=lambda x: (not os.path.isdir(os.path.join(current_path, x)), x.lower()))
            
            # Показываем в сетке
            cols = st.columns(4)
            for idx, item in enumerate(items):
                with cols[idx % 4]:
                    item_path = os.path.join(current_path, item)
                    is_dir = os.path.isdir(item_path)
                    
                    if is_dir:
                        st.markdown(f"""
                        <div class="file-item">
                            <div class="file-icon">📁</div>
                            <div style="font-weight: 600;">{item[:20]}</div>
                            <div style="font-size: 0.8rem; color: #D4AF37;">Папка</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("📂 Открыть", key=f"open_{item}", use_container_width=True):
                            st.session_state.disk_current_path = item_path
                            st.rerun()
                    
                    else:
                        size = os.path.getsize(item_path)
                        icon = "🖼️" if item.lower().endswith(('.jpg','.png')) else "📄"
                        
                        st.markdown(f"""
                        <div class="file-item">
                            <div class="file-icon">{icon}</div>
                            <div style="font-weight: 600;">{item[:15]}</div>
                            <div style="font-size: 0.8rem; color: #D4AF37;">{format_size(size)}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        with open(item_path, 'rb') as f:
                            st.download_button("📥 Скачать", f.read(), item, use_container_width=True)

# ================= НОВОСТИ =================
elif st.session_state.page == "Новости":
    st.markdown('<div class="gold-title fade-in">📰 НОВОСТИ</div>', unsafe_allow_html=True)
    st.markdown('<div class="news-header">Последние новости</div>', unsafe_allow_html=True)
    
    with st.spinner("Загружаю новости..."):
        news = get_belta_news()
        
        for item in news:
            st.markdown(f"""
            <div class="news-card">
                <div class="news-title">{item.title}</div>
                <div class="news-summary">{item.summary[:200]}...</div>
                <div style="margin-top: 15px;">
                    <a href="{item.link}" target="_blank" style="color: #D4AF37; text-decoration: none; font-weight: 600;">Читать далее →</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ================= ПОГОДА =================
elif st.session_state.page == "Погода":
    st.markdown('<div class="gold-title fade-in">🌤️ ПОГОДА</div>', unsafe_allow_html=True)
    
    # Поиск города
    col1, col2 = st.columns([3, 1])
    with col1:
        city_input = st.text_input("", placeholder="Введите город...", label_visibility="collapsed")
    with col2:
        search_clicked = st.button("🔍 Найти", type="primary", use_container_width=True)
    
    city_to_show = st.session_state.user_city if st.session_state.user_city else "Минск"
    
    if search_clicked and city_input:
        city_to_show = city_input
        st.session_state.user_city = city_input
    
    with st.spinner(f"Получаю погоду..."):
        weather_data = get_weather_by_city(city_to_show)
        
        if not weather_data:
            st.error(f"❌ Город {city_to_show} не найден")
            weather_data = get_weather_by_city("Минск")
        
        if weather_data:
            current = weather_data["current"]
            
            # Основная карточка
            st.markdown(f"""
            <div class="weather-main-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
                    <h2 style="margin: 0; color: white;">{current['city']}, {current['country']}</h2>
                    <div style="font-size: 1.2rem; background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 30px;">
                        {current['description']}
                    </div>
                </div>
                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 20px;">
                    <div>
                        <div class="weather-temp">{current['temp']}°C</div>
                        <div style="font-size: 1.2rem;">Ощущается как {current['feels_like']}°C</div>
                    </div>
                    <div class="weather-icon">{get_weather_icon(current['icon'])}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Детали
            st.markdown("### Детали")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="weather-detail-item">
                    <div style="font-size: 1.5rem;">💧</div>
                    <div style="font-weight: 600;">{current['humidity']}%</div>
                    <div style="font-size: 0.9rem;">Влажность</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="weather-detail-item">
                    <div style="font-size: 1.5rem;">💨</div>
                    <div style="font-weight: 600;">{current['wind_speed']} м/с</div>
                    <div style="font-size: 0.9rem;">Ветер</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="weather-detail-item">
                    <div style="font-size: 1.5rem;">📊</div>
                    <div style="font-weight: 600;">{current['pressure']} гПа</div>
                    <div style="font-size: 0.9rem;">Давление</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="weather-detail-item">
                    <div style="font-size: 1.5rem;">☁️</div>
                    <div style="font-weight: 600;">{current['clouds']}%</div>
                    <div style="font-size: 0.9rem;">Облачность</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Прогноз
            if weather_data.get("forecast"):
                st.markdown("### Прогноз на 5 дней")
                
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
                        <div style="background: linear-gradient(135deg, #D4AF37, #B8860B); border-radius: 15px; padding: 15px; text-align: center; color: white;">
                            <div style="font-weight: 600;">{day_name}</div>
                            <div style="font-size: 2rem;">{get_weather_icon(day['weather'][0]['icon'])}</div>
                            <div style="font-size: 1.2rem; font-weight: 600;">{round(day['main']['temp'])}°C</div>
                        </div>
                        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🇧🇾 Города Беларуси")
    
    cities = ["Минск", "Гомель", "Витебск", "Могилёв", "Брест", "Гродно"]
    cols = st.columns(3)
    for idx, city in enumerate(cities):
        with cols[idx % 3]:
            if st.button(city, use_container_width=True):
                st.session_state.user_city = city
                st.rerun()

# ================= ПРОФИЛЬ =================
elif st.session_state.page == "Профиль":
    if st.session_state.is_logged_in:
        user = st.session_state.user_data
        
        st.markdown(f"""
        <div class="profile-card fade-in">
            <div class="profile-avatar">{user.get('first_name', 'U')[0]}</div>
            <div class="profile-name">{user.get('first_name', '')} {user.get('last_name', '')}</div>
            <div class="profile-username">@{user.get('username', '')}</div>
            <div class="profile-email">{user.get('email', '')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚪 Выйти из аккаунта", use_container_width=True, type="primary"):
            save_quick_links(st.session_state.quick_links)
            st.session_state.is_logged_in = False
            st.session_state.user_data = {}
            st.session_state.disk_current_path = None
            st.session_state.page = "Главная"
            st.rerun()
    
    else:
        st.markdown('<div class="gold-title fade-in">ZORNET ID</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔐 Вход", "📝 Регистрация"])
        
        with tab1:
            st.markdown("### Вход в аккаунт")
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Пароль", type="password", key="login_password")
            
            if st.button("Войти", type="primary", use_container_width=True):
                if login_email and login_password:
                    user = login_user(login_email, login_password)
                    if user:
                        st.session_state.user_data = user
                        st.session_state.is_logged_in = True
                        st.session_state.disk_current_path = f"zornet_cloud/{user['username']}"
                        
                        saved_links = load_quick_links()
                        if saved_links:
                            st.session_state.quick_links = saved_links
                        
                        st.success("✅ Вход выполнен!")
                        st.session_state.page = "Главная"
                        st.rerun()
                    else:
                        st.error("❌ Неверный email или пароль")
        
        with tab2:
            st.markdown("### Создать аккаунт")
            
            if st.session_state.registration_success:
                st.success(f"✅ {st.session_state.registration_message}")
                if st.button("➡️ Перейти ко входу", use_container_width=True):
                    st.session_state.registration_success = False
                    st.rerun()
            else:
                reg_email = st.text_input("Email", key="reg_email")
                reg_username = st.text_input("Никнейм", key="reg_username")
                reg_first_name = st.text_input("Имя", key="reg_first_name")
                reg_last_name = st.text_input("Фамилия", key="reg_last_name")
                reg_password = st.text_input("Пароль", type="password", key="reg_password")
                reg_password_confirm = st.text_input("Повторите пароль", type="password", key="reg_password_confirm")
                
                if st.button("Создать аккаунт", type="primary", use_container_width=True):
                    if not all([reg_email, reg_username, reg_first_name, reg_password, reg_password_confirm]):
                        st.error("❌ Заполните все обязательные поля")
                    elif reg_password != reg_password_confirm:
                        st.error("❌ Пароли не совпадают")
                    elif len(reg_password) < 6:
                        st.error("❌ Пароль должен быть не менее 6 символов")
                    else:
                        result = register_user(reg_email, reg_username, reg_first_name, reg_last_name, reg_password)
                        if result["success"]:
                            st.session_state.registration_success = True
                            st.session_state.registration_message = result["message"]
                            st.rerun()
                        else:
                            st.error(f"❌ {result['message']}")
        
        st.markdown('</div>', unsafe_allow_html=True)

# ================= ИНИЦИАЛИЗАЦИЯ =================
if __name__ == "__main__":
    init_db()
    
    # Создаем тестового пользователя
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE username = 'test'")
    if c.fetchone()[0] == 0:
        test_password = hashlib.sha256("test123".encode()).hexdigest()
        c.execute("INSERT INTO users (email, username, first_name, last_name, password_hash) VALUES (?, ?, ?, ?, ?)",
                 ("test@zornet.by", "test", "Тест", "Пользователь", test_password))
        conn.commit()
    conn.close()
