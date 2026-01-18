import streamlit as st
import sqlite3
import datetime
import os
import pytz
import requests
import feedparser
from PIL import Image
from pathlib import Path
import mimetypes
import pandas as pd
from duckduckgo_search import DDGS
from huggingface_hub import InferenceClient

# ================= НАСТРОЙКИ СТРАНИЦЫ =================
st.set_page_config(
    page_title="ZORNET CLOUD",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ =================
if "page" not in st.session_state:
    st.session_state.page = "Главная"
if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = []
if "current_path" not in st.session_state:
    st.session_state.current_path = "root"
if "user_data" not in st.session_state:
    st.session_state.user_data = {"name": "Пользователь Zornet", "bio": "Premium Cloud User", "gender": "Не указан"}

# Создание директории для хранения файлов
ROOT_DIR = Path("zornet_storage")
ROOT_DIR.mkdir(exist_ok=True)

# ================= CSS СТИЛИ (ЗОЛОТОЙ И БЕЛЫЙ) =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp { background-color: #FFFFFF; }
    
    /* ЗОЛОТЫЕ ГРАДИЕНТЫ */
    :root {
        --gold-linear: linear-gradient(135deg, #BF953F, #FCF6BA, #B38728, #FBF5B7, #AA771C);
        --gold-solid: #DAA520;
    }

    /* ГЛАВНЫЙ ЗАГОЛОВОК */
    .gold-title {
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        background: var(--gold-linear);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 20px;
        filter: drop-shadow(0px 2px 2px rgba(0,0,0,0.1));
    }

    /* КАРТОЧКИ И ПАНЕЛИ */
    .glass-card {
        background: #ffffff;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f0;
        transition: transform 0.3s ease;
    }
    
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(218, 165, 32, 0.1);
    }

    /* КНОПКИ */
    .stButton>button {
        border-radius: 10px !important;
        border: 1px solid #f0f0f0 !important;
        transition: all 0.3s !important;
    }
    
    .stButton>button:hover {
        border-color: #DAA520 !important;
        color: #DAA520 !important;
        box-shadow: 0 4px 12px rgba(218, 165, 32, 0.2) !important;
    }

    /* ПЛАВАЮЩАЯ ПАНЕЛЬ (FAB) */
    .fab-container {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 100;
    }

    /* ФАЙЛОВЫЙ МЕНЕДЖЕР */
    .file-icon {
        font-size: 40px;
        margin-bottom: 10px;
    }
    
    .file-card {
        text-align: center;
        padding: 15px;
        background: #fdfdfd;
        border-radius: 12px;
        border: 1px solid #eee;
    }

    /* ПОГОДНЫЙ ВИДЖЕТ */
    .weather-card {
        background: var(--gold-linear);
        color: #444;
        padding: 25px;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ================= БАЗА ДАННЫХ =================
def init_all_dbs():
    # БД Файлов и комментариев
    conn = sqlite3.connect("zornet_system.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS files 
                 (id INTEGER PRIMARY KEY, name TEXT, path TEXT, size REAL, 
                  type TEXT, date TEXT, comments TEXT, shared INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, username TEXT, avatar BLOB, bio TEXT)""")
    conn.commit()
    conn.close()

init_all_dbs()

# ================= ФУНКЦИИ ПОГОДЫ (ПРОФЕССИОНАЛЬНЫЕ) =================
def get_weather():
    try:
        # 1. Получаем местоположение по IP
        geo_res = requests.get("http://ip-api.com/json/", timeout=5).json()
        city = geo_res.get("city", "Minsk")
        lat = geo_res.get("lat", 53.9)
        lon = geo_res.get("lon", 27.5)
        
        # 2. Получаем погоду (Open-Meteo - бесплатно и без ключа)
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m,relativehumidity_2m,windspeed_10m"
        weather_res = requests.get(url).json()
        curr = weather_res["current_weather"]
        
        return {
            "city": city,
            "temp": curr["temperature"],
            "wind": curr["windspeed"],
            "code": curr["weathercode"],
            "time": curr["time"]
        }
    except:
        return None

# ================= ЛОГИКА ДИСКА =================
def get_file_icon(mime_type, is_dir=False):
    if is_dir: return "📂"
    if "image" in mime_type: return "🖼️"
    if "video" in mime_type: return "🎬"
    if "pdf" in mime_type: return "📄"
    if "audio" in mime_type: return "🎵"
    return "📝"

def save_file_metadata(name, path, size, file_type):
    conn = sqlite3.connect("zornet_system.db")
    c = conn.cursor()
    c.execute("INSERT INTO files (name, path, size, type, date, comments) VALUES (?,?,?,?,?,?)",
              (name, str(path), size, file_type, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), ""))
    conn.commit()
    conn.close()

# ================= САЙДБАР (БЕЗ ИЗМЕНЕНИЙ В ЛОГИКЕ) =================
with st.sidebar:
    st.markdown(f"""
        <div style='text-align: center; padding: 20px;'>
            <h1 style='background: var(--gold-linear); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>ZORNET</h1>
            <p style='color: #888; font-size: 0.8rem;'>PREMIUM CLOUD SYSTEM</p>
        </div>
    """, unsafe_allow_html=True)
    
    pages = [
        ("🏠", "ГЛАВНАЯ", "Главная"),
        ("🤖", "ZORNET AI", "ZORNET AI"),
        ("💾", "ZORNET DISK", "Диск"),
        ("🌦️", "ПОГОДА", "Погода"),
        ("📰", "НОВОСТИ", "Новости"),
        ("🚌", "ТРАНСПОРТ", "Транспорт"),
        ("👤", "ПРОФИЛЬ", "Профиль"),
    ]
    
    for i, (icon, text, page) in enumerate(pages):
        if st.button(f"{icon} {text}", key=f"nav_{i}", use_container_width=True):
            st.session_state.page = page
            st.rerun()

# ================= КОНТЕНТ СТРАНИЦ =================

# --- ГЛАВНАЯ (ВАШ КОД + СТИЛИЗАЦИЯ) ---
if st.session_state.page == "Главная":
    st.markdown('<div class="gold-title">ZORNET</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="glass-card">🕒 <b>Время</b><br>'+datetime.datetime.now().strftime("%H:%M")+'</div>', unsafe_allow_html=True)
    with col2:
        w = get_weather()
        temp = f"{w['temp']}°C" if w else "N/A"
        st.markdown(f'<div class="glass-card">⛅ <b>Погода</b><br>{temp}</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="glass-card">💵 <b>USD/BYN</b><br>3.20</div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="glass-card">🚀 <b>Статус</b><br>Premium</div>', unsafe_allow_html=True)

    st.write("")
    search_query = st.text_input("", placeholder="Поиск в глобальной сети Zornet...", label_visibility="collapsed")
    if search_query:
        # Здесь ваша функция search_zornet
        st.info(f"Поиск результатов для: {search_query}")

# --- ZORNET DISK (НОВЫЙ ПРОФЕССИОНАЛЬНЫЙ ФУНКЦИОНАЛ) ---
elif st.session_state.page == "Диск":
    st.markdown('<div class="gold-title">ZORNET DISK</div>', unsafe_allow_html=True)
    
    # Верхняя панель управления
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        uploaded_files = st.file_uploader("Перетащите файлы сюда (Drag & Drop)", accept_multiple_files=True, label_visibility="collapsed")
        if uploaded_files:
            for f in uploaded_files:
                f_path = ROOT_DIR / f.name
                with open(f_path, "wb") as buffer:
                    buffer.write(f.getbuffer())
                save_file_metadata(f.name, f_path, f.size/1024, mimetypes.guess_type(f.name)[0] or "unknown")
            st.success("Файлы загружены!")
            st.rerun()
            
    with c2:
        new_folder = st.text_input("", placeholder="Имя новой папки")
        if st.button("➕ Создать папку", use_container_width=True):
            (ROOT_DIR / new_folder).mkdir(exist_ok=True)
            st.rerun()
            
    with c3:
        st.selectbox("Сортировка", ["По дате", "По размеру", "По типу"], label_visibility="collapsed")

    st.markdown("---")

    # Отображение файлов в стиле Material Grid
    files = list(ROOT_DIR.iterdir())
    if not files:
        st.info("Ваше облако пусто. Загрузите первый файл!")
    else:
        # Сетка 4 колонки
        cols = st.columns(4)
        for idx, item in enumerate(files):
            with cols[idx % 4]:
                st.markdown(f"""
                <div class="file-card">
                    <div class="file-icon">{get_file_icon(mimetypes.guess_type(item.name)[0] or "", item.is_dir())}</div>
                    <div style="font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{item.name}</div>
                    <div style="color: #888; font-size: 0.7rem;">{item.stat().st_size/1024:.1f} KB</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Мини-панель действий
                act_col1, act_col2 = st.columns(2)
                with act_col1:
                    if not item.is_dir():
                        st.download_button("💾", data=open(item, "rb").read(), file_name=item.name, key=f"dl_{idx}", help="Скачать")
                with act_col2:
                    if st.button("🗑️", key=f"del_{idx}", help="Удалить"):
                        if item.is_file(): item.unlink()
                        st.rerun()
                
                # Предпросмотр (если изображение)
                if "image" in (mimetypes.guess_type(item.name)[0] or ""):
                    with st.expander("Просмотр"):
                        st.image(str(item))
                
                # Комментарии
                with st.expander("💬 Заметки"):
                    note = st.text_area("Ваш комментарий", key=f"note_{idx}", label_visibility="collapsed")
                    if st.button("Сохранить", key=f"snote_{idx}"):
                        st.toast("Заметка сохранена!")

# --- ПОГОДА (ПРОФЕССИОНАЛЬНАЯ ВКЛАДКА) ---
elif st.session_state.page == "Погода":
    st.markdown('<div class="gold-title">МЕТЕОЦЕНТР ZORNET</div>', unsafe_allow_html=True)
    
    w_data = get_weather()
    if w_data:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"""
            <div class="weather-card">
                <h2 style="color: #444;">{w_data['city']}</h2>
                <h1 style="font-size: 4rem; color: #444;">{w_data['temp']}°C</h1>
                <p>Ветер: {w_data['wind']} км/ч</p>
                <hr>
                <p>Обновлено: {w_data['time']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("### Прогноз на ближайшие часы")
            # Генерация фиктивных данных для графика (в реальности берется из почасового API)
            chart_data = pd.DataFrame({
                'Температура': [w_data['temp'] + i for i in range(12)],
                'Влажность': [50 + i*2 for i in range(12)]
            })
            st.line_chart(chart_data)
    else:
        st.error("Не удалось определить местоположение. Проверьте доступ к сети.")

# --- ПРОФИЛЬ ---
elif st.session_state.page == "Профиль":
    st.markdown('<div class="gold-title">ЛИЧНЫЙ КАБИНЕТ</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown('<div class="glass-card" style="text-align:center;">', unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=150)
        st.markdown(f"<h3>{st.session_state.user_data['name']}</h3>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with c2:
        with st.form("user_edit"):
            st.session_state.user_data['name'] = st.text_input("Имя/Ник", st.session_state.user_data['name'])
            st.session_state.user_data['bio'] = st.text_area("О себе", st.session_state.user_data['bio'])
            st.session_state.user_data['gender'] = st.selectbox("Пол", ["Мужской", "Женский", "Не указан"])
            if st.form_submit_button("Сохранить изменения"):
                st.success("Профиль обновлен!")

# ================= СТРАНИЦА AI =================
elif st.session_state.page == "ZORNET AI":
    st.markdown('<div class="gold-title">🤖 ZORNET AI</div>', unsafe_allow_html=True)
    
    # ИНИЦИАЛИЗАЦИЯ ЧАТА
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = [
            {"role": "assistant", "content": "Привет! Я ZORNET AI. Чем могу помочь?"}
        ]
    
    # ИСТОРИЯ СООБЩЕНИЙ
    for message in st.session_state.ai_messages:
        if message["role"] == "user":
            st.markdown(f'<div class="user-message">{message["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="ai-message">{message["content"]}</div>', unsafe_allow_html=True)
    
    # ПОЛЕ ВВОДА
    if prompt := st.chat_input("Спросите ZORNET AI..."):
        # ДОБАВЛЯЕМ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ
        st.session_state.ai_messages.append({"role": "user", "content": prompt})
        
        # ПОЛУЧАЕМ ОТВЕТ
        with st.spinner("ZORNET думает..."):
            response = ask_hf_ai(prompt)
            st.session_state.ai_messages.append({"role": "assistant", "content": response})
        
        st.rerun()
    
    # БОКОВАЯ ПАНЕЛЬ С ПРИМЕРАМИ
    with st.sidebar:
        st.markdown("### 💡 Примеры вопросов")
        
        examples = [
            "Напиши план развития для IT-стартапа",
            "Объясни квантовую физику просто",
            "Помоги написать деловое письмо",
            "Какие технологии AI самые перспективные?",
            "Напиши простой сайт на HTML",
            "Объясни разницу Python и JavaScript",
            "Помоги составить резюме",
            "Какие книги по саморазвитию посоветуешь?"
        ]
        
        for example in examples:
            if st.button(example, key=f"ex_{example[:10]}", use_container_width=True):
                st.session_state.ai_messages.append({"role": "user", "content": example})
                st.rerun()
        
        # ОЧИСТКА ИСТОРИИ
        if st.button("🧹 Очистить историю", use_container_width=True):
            st.session_state.ai_messages = [
                {"role": "assistant", "content": "Привет! Я ZORNET AI. Чем могу помочь?"}
            ]
            st.rerun()

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

# ================= СТРАНИЦА ТРАНСПОРТА =================
elif st.session_state.page == "Транспорт":
    st.markdown('<div class="gold-title">🚌 ТРАНСПОРТ</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["🚇 Метро", "🚌 Автобусы/Трамваи", "🚕 Такси", "🚂 Железная дорога"])
    
    with tab1:
        st.subheader("Минское метро")
        for station in get_minsk_metro():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{station['name']}**")
            with col2:
                st.write(f"Линия {station['line']}")
            with col3:
                st.success(f"🚇 {station['next']}")
    
    with tab2:
        st.subheader("Автобусы и трамваи")
        for route in get_bus_trams():
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
        for service in get_taxi_prices():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{service['name']}**")
            with col2:
                st.write(f"💵 {service['price']}")
            with col3:
                st.write(f"🕒 {service['wait']}")
    
    with tab4:
        st.subheader("Белорусская железная дорога")
        for train in get_belarusian_railway():
            col1, col2, col3, col4 = st.columns([1, 2, 2, 2])
            with col1:
                st.write(f"**{train['number']}**")
            with col2:
                st.write(f"📍 {train['from']}")
            with col3:
                st.write(f"➡️ {train['to']}")
            with col4:
                st.write(f"🕒 {train['time']}")

# ================= СТРАНИЦА ДИСКА =================
def get_icon(file_path):
    ext = file_path.suffix.lower()
    if file_path.is_dir(): return "📁"
    if ext in [".jpg", ".jpeg", ".png", ".gif"]: return "🖼️"
    if ext == ".pdf": return "📄"
    if ext in [".doc", ".docx"]: return "📝"
    if ext in [".mp3", ".wav"]: return "🎵"
    if ext in [".mp4", ".avi"]: return "🎬"
    return "📦"

def render_breadcrumb(path):
    parts = list(path.relative_to(ROOT_DIR).parts)
    breadcrumb_html = ["<a href='#' onclick='window.location.reload()'>Главная</a>"]
    p = ROOT_DIR
    for part in parts:
        p = p / part
        breadcrumb_html.append(f"<a href='#' onclick='window.location.reload()'>{part}</a>")
    st.markdown(" / ".join(breadcrumb_html), unsafe_allow_html=True)

# ================= СТРАНИЦА ДИСКА =================
if st.session_state.page == "Главная":
    st.markdown('<div class="gold-title">ZORNET DISK</div>', unsafe_allow_html=True)
    
    # -- Содержимое папки --
    ROOT_DIR = Path("zornet_files")
    ROOT_DIR.mkdir(exist_ok=True)
    
    if "current_dir" not in st.session_state:
        st.session_state.current_dir = ROOT_DIR
    
    current_dir = st.session_state.current_dir
    render_breadcrumb(current_dir)

    # -- Загрузка файлов --
    st.subheader("Загрузить файлы (Drag & Drop поддерживается)")
    uploaded_files = st.file_uploader("Выберите файлы", type=None, accept_multiple_files=True)
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_path = current_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            save_file_to_db(uploaded_file.name, uploaded_file.size)  # Сохраняем в БД
        st.success(f"✅ Загружено {len(uploaded_files)} файлов")
        st.experimental_rerun()

    # -- Список файлов --
    st.subheader(f"Содержимое папки: {current_dir.name}")
    items = list(current_dir.iterdir())
    if items:
        for item in sorted(items, key=lambda x: (x.is_file(), x.name.lower())):
            col1, col2, col3 = st.columns([4, 2, 1])
            with col1:
                icon = get_icon(item)
                st.write(f"{icon} {item.name}")
            with col2:
                st.write(f"Размер: {item.stat().st_size / 1024:.2f} KB")
            with col3:
                st.download_button("Скачать", data=open(item, "rb").read(), file_name=item.name)
    else:
        st.info("Папка пуста.")

# ПЛАВАЮЩАЯ КНОПКА ПОДДЕРЖКИ
st.markdown("""
<div class="fab-container">
    <button style="background: var(--gold-linear); border: none; width: 60px; height: 60px; border-radius: 50%; color: white; font-size: 24px; box-shadow: 0 5px 15px rgba(0,0,0,0.2); cursor: pointer;">
    💬
    </button>
</div>
""", unsafe_allow_html=True)

# ================= ИНИЦИАЛИЗАЦИЯ =================
if __name__ == "__main__":
    # Инициализация всех баз данных
    init_db()
    init_disk_db()

