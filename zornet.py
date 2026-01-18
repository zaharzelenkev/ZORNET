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
from duckduckgo_search import DDGS
from huggingface_hub import InferenceClient

# ================= НАСТРОЙКИ =================
st.set_page_config(
    page_title="ZORNET",
    page_icon="🇧🇾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= СЕССИЯ =================
if "page" not in st.session_state:
    st.session_state.page = "Главная"
if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = []

# ================= CSS СТИЛИ =================
st.markdown("""
<style>
    /* ОБЩИЙ СТИЛЬ */
    .stApp { background-color: #ffffff; }
    
    /* СКРЫВАЕМ ЛИШНЕЕ */
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
</style>
""", unsafe_allow_html=True)

# ================= САЙДБАР =================
with st.sidebar:
    st.markdown("<h3 style='color:#DAA520;'>🇧🇾 ZORNET</h3>", unsafe_allow_html=True)
    
    pages = [
        ("🏠", "ГЛАВНАЯ", "Главная"),
        ("🤖", "ZORNET AI", "ZORNET AI"),
        ("📰", "НОВОСТИ", "Новости"),
        ("💾", "ДИСК", "Диск"),
        ("🚌", "ТРАНСПОРТ", "Транспорт"),
        ("👤", "ПРОФИЛЬ", "Профиль"),
    ]
    
    # Используем уникальные ключи с индексом
    for i, (icon, text, page) in enumerate(pages):
        if st.button(f"{icon} {text}", key=f"nav_{i}_{page}", use_container_width=True):
            st.session_state.page = page
            st.rerun()

# ================= НАСТРОЙКИ =================
HF_API_KEY = st.secrets["HF_API_KEY"]
CHAT_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"  # стабильная бесплатная модель
API_URL = "https://router.huggingface.co/api/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {HF_API_KEY}",
    "Content-Type": "application/json"
}

def ask_hf_ai(prompt: str) -> str:
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
        # получаем ответ
        text = data["choices"][0]["message"]["content"]
        return text.strip()

    except Exception:
        return "⚠️ Ошибка соединения с ZORNET AI."

# ================= ФУНКЦИИ ПОИСКА =================
def search_zornet(query, num_results=5):
    """Поиск в интернете - с запасными результатами"""
    results = []
    
    # Попытка поиска через DuckDuckGo
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
        st.error(f"Ошибка DuckDuckGo: {e}")
    
    # Если DuckDuckGo не работает, показываем запасные результаты
    fallback_results = [
        {
            "title": f"{query} - поиск в Google",
            "url": f"https://www.google.com/search?q={query}",
            "snippet": f"Нажмите для поиска '{query}' в Google. Это лучший способ найти информацию в интернете."
        },
        {
            "title": f"{query} в Википедии",
            "url": f"https://ru.wikipedia.org/wiki/{query}",
            "snippet": f"Ищите информацию о '{query}' в Википедии - свободной энциклопедии."
        },
        {
            "title": "Решебники и ГДЗ онлайн",
            "url": "https://reshak.ru/",
            "snippet": "Бесплатные решебники и готовые домашние задания по всем предметам."
        },
        {
            "title": "Образовательные ресурсы Беларуси",
            "url": "https://adu.by/",
            "snippet": "Официальный образовательный портал Министерства образования Республики Беларусь."
        },
        {
            "title": "Учебные материалы и пособия",
            "url": "https://nashol.com/",
            "snippet": "Большая библиотека учебников, решебников и учебных материалов."
        }
    ]
    
    # Фильтруем релевантные результаты
    relevant_results = []
    for res in fallback_results:
        if query.lower() in res["title"].lower() or query.lower() in res["snippet"].lower():
            relevant_results.append(res)
    
    # Если нет релевантных, берем первые 3
    if not relevant_results:
        relevant_results = fallback_results[:3]
    
    return relevant_results

# ================= ТРАНСПОРТНЫЕ ФУНКЦИИ =================
def get_minsk_metro():
    return [
        {"name": "Малиновка", "line": "1", "next": "3 мин"},
        {"name": "Петровщина", "line": "1", "next": "5 мин"},
        {"name": "Площадь Ленина", "line": "1", "next": "2 мин"},
        {"name": "Институт Культуры", "line": "1", "next": "4 мин"},
        {"name": "Молодёжная", "line": "2", "next": "6 мин"},
    ]

def get_bus_trams():
    return [
        {"number": "100", "type": "автобус", "from": "Ст.м. Каменная Горка", "to": "Аэропорт", "next": "7 мин"},
        {"number": "1", "type": "трамвай", "from": "Тракторный завод", "to": "Серебрянка", "next": "5 мин"},
        {"number": "3с", "type": "троллейбус", "from": "ДС Веснянка", "to": "ДС Серова", "next": "3 мин"},
        {"number": "40", "type": "автобус", "from": "Ст.м. Уручье", "to": "Дражня", "next": "10 мин"},
    ]

def get_taxi_prices():
    return [
        {"name": "Яндекс Такси", "price": "8-12 руб", "wait": "5-7 мин"},
        {"name": "Uber", "price": "9-13 руб", "wait": "4-6 мин"},
        {"name": "Такси Близко", "price": "7-10 руб", "wait": "8-10 мин"},
        {"name": "Такси Город", "price": "6-9 руб", "wait": "10-15 мин"},
    ]

def get_belarusian_railway():
    return [
        {"number": "001Б", "from": "Минск", "to": "Брест", "time": "18:00 - 21:30"},
        {"number": "735Б", "from": "Минск", "to": "Гомель", "time": "07:30 - 11:15"},
        {"number": "603Б", "from": "Минск", "to": "Витебск", "time": "14:20 - 18:45"},
    ]

# ================= БАЗА ДАННЫХ =================
def init_db():
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_user_count():
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

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

if st.session_state.page == "Главная":
    # ===================== ЗОЛОТАЯ НАДПИСЬ =====================
    st.markdown('<div class="gold-title">ZORNET</div>', unsafe_allow_html=True)

    # ===================== 4 ВИДЖЕТА =====================
    current_time = datetime.datetime.now(pytz.timezone('Europe/Minsk'))
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.button(f"🕒 {current_time.strftime('%H:%M')}\nМинск", use_container_width=True)
    with col2:
        st.button("⛅ -5°C\nМинск", use_container_width=True)
    with col3:
        st.button("💵 3.20\nBYN/USD", use_container_width=True)
    with col4:
        if st.button("🤖 ZORNET AI", use_container_width=True):
            st.session_state.page = "ZORNET AI"
            st.rerun()

    st.markdown("---")  # разделитель

    # ===================== ПОИСКОВАЯ СТРОКА =====================
    search_query = st.text_input(
        "",
        placeholder="Поиск в интернете...",
        key=f"main_search_{st.session_state.page}",
        label_visibility="collapsed"
    )

    # ===================== РЕЗУЛЬТАТЫ ПОИСКА =====================
    if search_query:
        st.markdown(f"### 🔍 Результаты поиска: **{search_query}**")
        with st.spinner("Ищу информацию..."):
            results = search_zornet(search_query, num_results=5)
            if results:
                for idx, result in enumerate(results):
                    st.markdown(f"""
                    <div class="search-result">
                        <div style="font-weight: 600; color: #1a1a1a; font-size: 16px;">
                            {idx + 1}. {result['title']}
                        </div>
                        <div style="color: #1a73e8; font-size: 13px; margin: 5px 0;">
                            {result['url'][:60]}...
                        </div>
                        <div style="color: #555; font-size: 14px;">
                            {result['snippet']}
                        </div>
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
                st.info("По вашему запросу ничего не найдено.")

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
elif st.session_state.page == "Диск":
    st.markdown('<div class="gold-title">💾 ДИСК</div>', unsafe_allow_html=True)
    
    # --- Папки и файлы на диске ---
    ROOT_DIR = Path("zornet_files")
    ROOT_DIR.mkdir(exist_ok=True)

    if "current_dir" not in st.session_state:
        st.session_state.current_dir = ROOT_DIR

    current_dir = st.session_state.current_dir

    # --- Breadcrumb ---
    def render_breadcrumb(path):
        parts = list(path.relative_to(ROOT_DIR).parts)
        breadcrumb_html = ["<a href='#' onclick='window.location.reload()'>Главная</a>"]
        p = ROOT_DIR
        for part in parts:
            p = p / part
            breadcrumb_html.append(f"<a href='#' onclick='window.location.reload()'>{part}</a>")
        st.markdown(" / ".join(breadcrumb_html), unsafe_allow_html=True)

    render_breadcrumb(current_dir)

    # --- Навигация вверх ---
    if current_dir != ROOT_DIR:
        if st.button("🔙 Назад"):
            st.session_state.current_dir = current_dir.parent
            st.experimental_rerun()

    # --- Создание новой папки ---
    st.subheader("Создать папку")
    new_folder = st.text_input("Название папки")
    if st.button("Создать папку"):
        if new_folder:
            folder_path = current_dir / new_folder
            folder_path.mkdir(exist_ok=True)
            st.success(f"Папка '{new_folder}' создана")
            st.experimental_rerun()

    # --- Загрузка файлов drag & drop ---
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

    # --- Иконки ---
    def get_icon(file_path):
        ext = file_path.suffix.lower()
        if file_path.is_dir(): return "📁"
        if ext in [".jpg", ".jpeg", ".png", ".gif"]: return "🖼️"
        if ext == ".pdf": return "📄"
        if ext in [".doc", ".docx"]: return "📝"
        if ext in [".mp3", ".wav"]: return "🎵"
        if ext in [".mp4", ".avi"]: return "🎬"
        return "📦"

    # --- Список файлов и папок ---
    st.subheader(f"Содержимое папки: {current_dir.name}")
    items = list(current_dir.iterdir())
    if items:
        for item in sorted(items, key=lambda x: (x.is_file(), x.name.lower())):
            col1, col2, col3, col4 = st.columns([4,2,2,2])
            with col1:
                icon = get_icon(item)
                if item.is_dir():
                    if st.button(f"{icon} {item.name}"):
                        st.session_state.current_dir = item
                        st.experimental_rerun()
                else:
                    st.markdown(f"<div class='file-item'>{icon} {item.name}</div>", unsafe_allow_html=True)
                    # Превью изображений
                    if item.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif"]:
                        image = Image.open(item)
                        st.image(image, width=150, caption=item.name)
                    # Превью PDF
                    if item.suffix.lower() == ".pdf":
                        st.write(f"📄 PDF файл: {item.name}")
                    # Превью видео
                    if item.suffix.lower() in [".mp4", ".avi"]:
                        st.video(str(item))
            with col2:
                if item.is_file():
                    st.download_button("Скачать", data=open(item, "rb").read(), file_name=item.name)
            with col3:
                # Переименование
                new_name = st.text_input(f"Переименовать {item.name}", key=f"rename_{item}")
                if st.button(f"Переименовать {item.name}", key=f"btn_rename_{item}"):
                    new_path = item.parent / new_name
                    item.rename(new_path)
                    st.experimental_rerun()
            with col4:
                if st.button(f"Удалить {item.name}", key=f"del_{item}"):
                    if item.is_dir():
                        for child in item.iterdir():
                            if child.is_file():
                                child.unlink()
                            else:
                                os.rmdir(child)
                        os.rmdir(item)
                    else:
                        item.unlink()
                    st.experimental_rerun()
    else:
        st.info("Папка пуста.")

# ================= ИНИЦИАЛИЗАЦИЯ =================
if __name__ == "__main__":
    # Инициализация всех баз данных
    init_db()
    init_disk_db()
