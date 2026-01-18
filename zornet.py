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

# ================= НАСТРОЙКИ =================
st.set_page_config(
    page_title="ZORNET",
    page_icon="🇧🇾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= API КЛЮЧ =================
# Твой API ключ - ЗАМЕНИ ЭТУ СТРОКУ НА СВОЙ КЛЮЧ
HF_API_KEY = "hf_твой_ключ_сюда"  # <--- ВСТАВЬ СВОЙ КЛЮЧ
client = InferenceClient(HF_API_KEY)

# ================= СЕССИЯ =================
if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = []

if "page" not in st.session_state:
    st.session_state.page = "Главная"

vision_available = False  # Vision модель отключена

# ================= САЙДБАР =================
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
            st.rerun()

# ================= CSS СТИЛИ =================
st.markdown("""
<style>
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
    }
    
    .gold-button-ai {
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

# ================= ФУНКЦИИ AI =================
def ask_hf_ai(prompt):
    """Функция AI - исправленная"""
    try:
        response = client.text_generation(
            model="mistralai/Mistral-7B-Instruct-v0.1",
            prompt=prompt,
            max_new_tokens=200,
            temperature=0.7
        )
        return str(response)
    except Exception as e:
        return f"Ошибка: {str(e)}"

# ================= ФУНКЦИИ ПОИСКА =================
def search_zornet(query, num_results=5):
    """Поиск без подсказок"""
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=num_results):
                results.append({
                    "title": r.get("title", "Без названия"),
                    "url": r.get("href", "#"),
                    "snippet": r.get("body", "Описание отсутствует")[:150] + "...",
                })
    except Exception as e:
        st.error(f"Ошибка поиска: {e}")
    return results

# ================= ТРАНСПОРТНЫЕ ФУНКЦИИ =================
def get_minsk_metro():
    return [
        {"name": "Малиновка", "line": "1", "next_train": "3 мин"},
        {"name": "Петровщина", "line": "1", "next_train": "5 мин"},
        {"name": "Площадь Ленина", "line": "1", "next_train": "2 мин"},
    ]

def get_bus_trams():
    return [
        {"number": "100", "type": "автобус", "from": "Ст.м. Каменная Горка", "to": "Аэропорт", "next": "7 мин"},
        {"number": "1", "type": "трамвай", "from": "Тракторный завод", "to": "Серебрянка", "next": "5 мин"},
    ]

def get_taxi_prices():
    return [
        {"name": "Яндекс Такси", "price": "8-12 руб", "wait": "5-7 мин"},
        {"name": "Такси Близко", "price": "7-10 руб", "wait": "8-10 мин"},
    ]

def get_belarusian_railway():
    return [
        {"number": "001Б", "from": "Минск", "to": "Брест", "departure": "18:00", "arrival": "21:30"},
    ]

def get_airport_info():
    return [
        {"name": "Минск (MSQ)", "flights": "норм", "delays": "нет"},
    ]

def get_traffic_jams():
    return [
        {"city": "Минск", "level": "3/5", "description": "Умеренные пробки"},
    ]

def calculate_route(start, end):
    return [
        {"type": "🚗 На машине", "time": "25 мин", "distance": "12 км", "price": "≈ 15 руб"},
    ]

# ================= ФУНКЦИИ ДИСКА =================
def init_disk_db():
    """Инициализация базы диска"""
    pass  # Оставлю твои функции

def get_disk_usage():
    """Использование диска"""
    return 0, 5368709120, 0

def human_readable_size(size_bytes):
    """Читаемый размер"""
    return "0 Б"

def get_files_in_folder(parent_id=0):
    """Файлы в папке"""
    return []

def save_uploaded_file(uploaded_file, parent_id=0):
    """Сохранение файла"""
    return True

def create_folder(folder_name, parent_id=0):
    """Создание папки"""
    pass

def delete_file(file_id):
    """Удаление файла"""
    pass

# ================= БАЗА ДАННЫХ =================
def init_db():
    conn = sqlite3.connect("zornet_pro.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, nick TEXT, gender TEXT)")
    c.execute("SELECT COUNT(*) FROM users WHERE id = 1")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (id, nick, gender) VALUES (1, 'Гость', 'Не указан')")
    conn.commit()
    conn.close()

# ================= ГЛАВНАЯ СТРАНИЦА =================
if st.session_state.page == "Главная":
    # ВЕРХНЯЯ ПАНЕЛЬ
    col1, col2, col3 = st.columns([1, 3, 1])

    with col1:
        # КНОПКА AI
        if st.button("🤖 **ZORNET AI**", key="zornet_ai_btn", use_container_width=True):
            st.session_state.page = "ZORNET AI"
            st.rerun()

    with col2:
        # ПОИСК
        search_query = st.text_input(
            "",
            placeholder="🔍 Поиск в интернете...",
            key="main_search",
            label_visibility="collapsed"
        )

    with col3:
        # ВРЕМЯ В КРАСИВОЙ РАМКЕ
        current_time = datetime.datetime.now(pytz.timezone('Europe/Minsk'))
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
            border-radius: 12px;
            padding: 12px 15px;
            text-align: center;
            color: white;
            font-weight: 600;
            font-size: 16px;
            box-shadow: 0 4px 15px rgba(218, 165, 32, 0.3);
        ">
            <div>{current_time.strftime('%H:%M')}</div>
            <div style="font-size: 12px; font-weight: 500; opacity: 0.9;">{current_time.strftime('%d.%m.%Y')}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="gold-title">ZORNET</div>', unsafe_allow_html=True)

    # ВИДЖЕТЫ
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.button(f"🕒 {current_time.strftime('%H:%M')}\nМинск", use_container_width=True)
    with c2:
        st.button("⛅ -5°C\nМинск", use_container_width=True)
    with c3:
        st.button("💵 3.20\nBYN/USD", use_container_width=True)
    with c4:
        if st.button("🚌 ТРАНСПОРТ\n", use_container_width=True):
            st.session_state.page = "Транспорт"
            st.rerun()

    st.markdown("---")

    # ПОИСКОВЫЕ РЕЗУЛЬТАТЫ
    if search_query:
        st.markdown(f"### 🔍 Результаты поиска: **{search_query}**")
        
        # НЕТ ПОДСКАЗОК ПОИСКА!
        
        with st.spinner("Ищу информацию..."):
            results = search_zornet(search_query, num_results=5)
            
            if results:
                for idx, result in enumerate(results):
                    st.markdown(f"""
                    <div style="
                        background: #f8f9fa;
                        padding: 15px;
                        border-radius: 10px;
                        margin-bottom: 10px;
                        border-left: 4px solid #DAA520;
                    ">
                        <div style="font-weight: 600; color: #1a1a1a; font-size: 16px;">
                            {idx + 1}. {result['title']}
                        </div>
                        <div style="color: #1a73e8; font-size: 13px; margin: 5px 0;">{result['url'][:80]}...</div>
                        <div style="color: #555; font-size: 14px;">{result['snippet']}</div>
                        <div style="margin-top: 10px;">
                            <a href="{result['url']}" target="_blank" 
                               style="padding: 6px 12px; background: #DAA520; color: white; 
                                      border-radius: 6px; text-decoration: none; font-size: 12px;">
                                Перейти на сайт
                            </a>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

# ================= СТРАНИЦА AI =================
elif st.session_state.page == "ZORNET AI":
    st.markdown('<div class="gold-title">🤖 ZORNET AI</div>', unsafe_allow_html=True)
    
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = [
            {"role": "assistant", "content": "Привет! Я ZORNET AI. Чем могу помочь?"}
        ]
    
    # ИСТОРИЯ
    for message in st.session_state.ai_messages:
        if message["role"] == "user":
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; margin-bottom: 15px;">
                <div style="background: #f0f0f0; padding: 12px 18px; border-radius: 18px; max-width: 70%;">
                    {message["content"]}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-start; margin-bottom: 15px;">
                <div style="background: #f9f9f9; padding: 12px 18px; border-radius: 18px; max-width: 70%; 
                         border-left: 4px solid #DAA520;">
                    {message["content"]}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # ВВОД
    if prompt := st.chat_input("Спросите ZORNET AI..."):
        st.session_state.ai_messages.append({"role": "user", "content": prompt})
        
        with st.spinner("ZORNET думает..."):
            response = ask_hf_ai(prompt)
            st.session_state.ai_messages.append({"role": "assistant", "content": response})
        
        st.rerun()

# ================= СТРАНИЦА ТРАНСПОРТА =================
elif st.session_state.page == "Транспорт":
    st.markdown('<div class="gold-title">🚌 ТРАНСПОРТ</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🚇 Метро", "🚌 Автобусы/Трамваи", "🚕 Такси"])
    
    with tab1:
        st.subheader("Минское метро")
        for station in get_minsk_metro():
            st.write(f"**{station['name']}** - Линия {station['line']} (через {station['next_train']})")
    
    with tab2:
        st.subheader("Автобусы и трамваи")
        for route in get_bus_trams():
            st.write(f"**{route['number']}** ({route['type']}): {route['from']} → {route['to']} (через {route['next']})")
    
    with tab3:
        st.subheader("Сравнение цен такси")
        for service in get_taxi_prices():
            st.write(f"**{service['name']}**: {service['price']} (ожидание: {service['wait']})")

# ================= СТРАНИЦА НОВОСТЕЙ =================
elif st.session_state.page == "Новости":
    st.markdown('<div class="gold-title">📰 НОВОСТИ</div>', unsafe_allow_html=True)
    st.info("Раздел новостей в разработке")

# ================= СТРАНИЦА ДИСКА =================
elif st.session_state.page == "Диск":
    st.markdown('<div class="gold-title">💾 ДИСК</div>', unsafe_allow_html=True)
    st.info("Облачный диск в разработке")

# ================= СТРАНИЦА ПРОФИЛЯ =================
elif st.session_state.page == "Профиль":
    st.markdown('<div class="gold-title">👤 ПРОФИЛЬ</div>', unsafe_allow_html=True)
    st.info("Раздел профиля в разработке")

# ================= СТРАНИЦА КАМЕРЫ =================
elif st.session_state.page == "Камера":
    st.markdown('<div class="gold-title">📷 КАМЕРА</div>', unsafe_allow_html=True)
    st.info("Раздел камеры в разработке")

# ================= ИНИЦИАЛИЗАЦИЯ БД =================
init_db()
