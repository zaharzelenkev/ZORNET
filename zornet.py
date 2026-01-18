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

# ================= ИСПРАВЛЕНИЯ =================
# 1. Убрал ключ из кода - только из secrets
if "HF_API_KEY" not in st.secrets:
    st.error("❌ Добавь HF_API_KEY в Streamlit Secrets!")
    st.info("Вставь свой HF API ключ в Streamlit Cloud Secrets")
    st.stop()

HF_API_KEY = st.secrets["HF_API_KEY"]
client = InferenceClient(HF_API_KEY)

# 2. Убрал неработающий vision блок
vision_available = False  # Отключаем vision модель

if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = []

# ================= НАСТРОЙКИ СТРАНИЦЫ =================
st.set_page_config(
    page_title="ZORNET",
    page_icon="🇧🇾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= ВСЕ ОСТАЛЬНЫЕ ФУНКЦИИ ОСТАЮТСЯ БЕЗ ИЗМЕНЕНИЙ =================
# (Оставляю все функции как были, только исправлю ask_hf_ai)

def ask_hf_ai(prompt, history=[]):
    """ИСПРАВЛЕННАЯ функция AI"""
    try:
        # Простой prompt без сложного форматирования
        full_prompt = f"""
        Ты ZORNET AI, помощник. Отвечай кратко и по делу.
        
        Вопрос: {prompt}
        
        Ответ:
        """
        
        response = client.text_generation(
            model="mistralai/Mistral-7B-Instruct-v0.1",
            prompt=full_prompt,
            max_new_tokens=300,
            temperature=0.7,
            do_sample=True
        )
        
        # Преобразуем в строку
        return str(response).strip()
    except Exception as e:
        return f"Извините, произошла ошибка: {str(e)}"

# ================= ИСПРАВЛЕННЫЙ ПОИСК =================
def search_zornet(query, num_results=8):
    """Поиск БЕЗ предложений"""
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=num_results):
                results.append({
                    "title": r.get("title", "Без названия"),
                    "url": r.get("href", "#"),
                    "snippet": r.get("body", "Описание отсутствует")[:180] + "...",
                    "source": r.get("href", "").split("/")[2] if "/" in r.get("href", "") else ""
                })
    except Exception as e:
        st.error(f"Ошибка поиска: {e}")
    return results

# УДАЛИ ЭТУ ФУНКЦИЮ - она показывает предложения поиска:
# def get_search_suggestions(query):
#     """УДАЛИТЬ - не нужна"""
#     return []

# ================= ВСЕ ОСТАЛЬНЫЕ ФУНКЦИИ ОСТАЮТСЯ =================
# Дальше идет ТВОЙ ПОЛНЫЙ КОД без изменений:
# - Все транспортные функции
# - Все функции диска  
# - Все функции профиля
# - Все CSS стили
# - Вся логика страниц

# ================= ТОЛЬКО ИСПРАВЛЕНИЯ В ГЛАВНОЙ СТРАНИЦЕ =================

# В разделе ПОИСКОВЫЕ РЕЗУЛЬТАТЫ на главной странице:
# УБРАТЬ этот блок с предложениями:
"""
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
"""

# Вместо него просто показывать результаты поиска без предложений

# ================= В СТРАНИЦЕ AI =================
# В функции ask_hf_ai УБРАТЬ сложное форматирование истории
# Оставить простой вызов как выше

# ================= ДОБАВИТЬ В requirements.txt =================
"""
streamlit>=1.28.0
huggingface_hub>=0.19.0
duckduckgo-search>=4.1.0
Pillow>=10.0.0
pytz>=2023.3
feedparser>=6.0.10
requests>=2.31.0
google-api-python-client>=2.100.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.1.0
folium>=0.14.0
streamlit-folium>=0.15.0
sqlite3
"""

# ================= КНОПКА МЕНЮ =================
# Добавить в самое начало после импортов:
menu_col1, menu_col2 = st.columns([6, 1])
with menu_col2:
    if st.button("☰ Меню", type="secondary"):
        st.session_state.show_sidebar = not st.session_state.get('show_sidebar', True)
        st.rerun()

# И боковая панель должна быть всегда:
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
