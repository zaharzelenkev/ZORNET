import streamlit as st
import sqlite3
import datetime
import pytz
import requests
import feedparser
from duckduckgo_search import DDGS

# ================= НАСТРОЙКИ СТРАНИЦЫ =================
st.set_page_config(
    page_title="ZORNET GOLD",
    page_icon="🇧🇾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= СЕССИЯ =================
if "page" not in st.session_state:
    st.session_state.page = "Главная"
if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = [
        {"role": "assistant", "content": "Привет! Я ZORNET AI. Я работаю бесплатно и быстро. Чем помочь?"}
    ]

# ================= CSS СТИЛИ (ЗОЛОТАЯ ТЕМА) =================
st.markdown("""
<style>
    /* ФОН И БАЗА */
    .stApp {
        background-color: #0e0e0e; /* Темный элитный фон */
        color: #ffffff;
    }
    
    /* ГЛАВНЫЙ ЗАГОЛОВОК */
    .gold-title {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 4rem;
        font-weight: 900;
        text-align: center;
        background: linear-gradient(180deg, #FFD700 0%, #B8860B 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0px 4px 10px rgba(255, 215, 0, 0.3);
        margin-bottom: 20px;
        letter-spacing: 4px;
        text-transform: uppercase;
    }
    
    /* ЗОЛОТЫЕ КНОПКИ */
    div.stButton > button {
        background: linear-gradient(145deg, #FFD700 0%, #D4AF37 50%, #B8860B 100%) !important;
        color: #000000 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 18px 20px !important;
        font-size: 18px !important;
        font-weight: 800 !important;
        box-shadow: 0 6px 15px rgba(218, 165, 32, 0.2) !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }
    
    div.stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 25px rgba(255, 215, 0, 0.4) !important;
        background: linear-gradient(145deg, #FFE033 0%, #FFD700 100%) !important;
    }

    /* ПОЛЯ ВВОДА */
    div[data-testid="stTextInput"] input {
        background-color: #1a1a1a !important;
        color: #FFD700 !important;
        border: 1px solid #B8860B !important;
    }

    /* ЧАТ */
    .user-message {
        background: #333;
        color: white;
        padding: 12px 18px;
        border-radius: 18px 18px 0 18px;
        margin-left: auto;
        max-width: 80%;
        margin-bottom: 10px;
        border: 1px solid #444;
    }
    
    .ai-message {
        background: linear-gradient(135deg, #2a2a2a, #1a1a1a);
        border-left: 4px solid #FFD700;
        color: #e0e0e0;
        padding: 12px 18px;
        border-radius: 18px 18px 18px 0;
        margin-right: auto;
        max-width: 80%;
        margin-bottom: 10px;
    }
    
    /* РЕЗУЛЬТАТЫ ПОИСКА */
    .search-result {
        background: #1a1a1a;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border-left: 3px solid #FFD700;
    }
    a { color: #FFD700 !important; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# ================= ЛОГИКА ZORNET AI (БЕСПЛАТНО) =================
def ask_zornet_ai(prompt: str) -> str:
    """Бесплатный AI через DuckDuckGo (без VPN и ключей)"""
    try:
        with DDGS() as ddgs:
            # Используем модель gpt-4o-mini (она быстрая и умная)
            response = ddgs.chat(prompt, model='gpt-4o-mini')
            return response
    except Exception as e:
        return f"⚠️ ZORNET AI перезагружается. Попробуйте через 5 секунд. (Ошибка: {e})"

# ================= ФУНКЦИИ ПОИСКА =================
def search_zornet(query, num_results=5):
    """Поиск в интернете + запасные варианты"""
    results = []
    
    # 1. Попытка реального поиска
    try:
        with DDGS() as ddgs:
            ddgs_results = list(ddgs.text(query, max_results=num_results, region='ru-ru'))
            if ddgs_results:
                for r in ddgs_results:
                    results.append({
                        "title": r.get("title", query),
                        "url": r.get("href", "#"),
                        "snippet": r.get("body", "")[:200] + "..."
                    })
                return results
    except Exception:
        pass # Если ошибка, идем к запасным
    
    # 2. Запасные результаты (как в старом коде)
    fallback_results = [
        {"title": f"{query} - Google Поиск", "url": f"https://www.google.com/search?q={query}", "snippet": "Искать в Google..."},
        {"title": "Решебники и ГДЗ", "url": "https://reshak.ru/", "snippet": "ГДЗ по всем предметам."},
        {"title": "Образование Беларуси", "url": "https://adu.by/", "snippet": "Официальный портал."},
        {"title": "Википедия", "url": f"https://ru.wikipedia.org/wiki/{query}", "snippet": "Свободная энциклопедия."}
    ]
    return fallback_results[:3]

# ================= ДАННЫЕ (ТРАНСПОРТ, НОВОСТИ) =================
def get_minsk_metro():
    return [
        {"name": "Малиновка", "line": "1", "next": "3 мин"},
        {"name": "Петровщина", "line": "1", "next": "5 мин"},
        {"name": "Площадь Ленина", "line": "1", "next": "2 мин"},
    ]

def get_bus_trams():
    return [
        {"number": "100", "type": "автобус", "from": "Центр", "to": "Аэропорт", "next": "7 мин"},
        {"number": "1", "type": "трамвай", "from": "Вокзал", "to": "Зеленый луг", "next": "5 мин"},
    ]

def get_belta_news():
    try:
        # Используем RSS BelTA или заглушку, если не грузит
        d = feedparser.parse("https://www.belta.by/rss")
        if d.entries:
            return d.entries[:6]
    except:
        pass
    return [
        {"title": "Новости Беларуси: Экономика растет", "link": "#", "summary": "Обзор экономических событий..."},
        {"title": "Спорт: Динамо Минск победило", "link": "#", "summary": "Обзор матча..."},
        {"title": "Погода на неделю", "link": "#", "summary": "Ожидается потепление..."}
    ]

# ================= БАЗА ДАННЫХ (ДИСК И ЮЗЕРЫ) =================
def init_dbs():
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS files (name TEXT, size INTEGER, date TEXT)")
    conn.commit()
    conn.close()

def save_file(name, size):
    conn = sqlite3.connect("zornet.db")
    c = conn.cursor()
    c.execute("INSERT INTO files VALUES (?, ?, ?)", (name, size, str(datetime.datetime.now())))
    conn.commit()
    conn.close()

def get_files():
    conn = sqlite3.connect("zornet.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM files ORDER BY date DESC")
    return c.fetchall()

# Инициализация при старте
init_dbs()

# ================= САЙДБАР =================
with st.sidebar:
    st.markdown("<h2 style='color:#FFD700;'>⚡ ZORNET</h2>", unsafe_allow_html=True)
    
    # Навигация через кнопки (более надежно)
    if st.button("🏠 ГЛАВНАЯ", key="nav_main", use_container_width=True): st.session_state.page = "Главная"
    if st.button("🤖 AI ЧАТ", key="nav_ai", use_container_width=True): st.session_state.page = "ZORNET AI"
    if st.button("📰 НОВОСТИ", key="nav_news", use_container_width=True): st.session_state.page = "Новости"
    if st.button("💾 ДИСК", key="nav_disk", use_container_width=True): st.session_state.page = "Диск"
    if st.button("🚌 ТРАНСПОРТ", key="nav_trans", use_container_width=True): st.session_state.page = "Транспорт"
    if st.button("👤 ПРОФИЛЬ", key="nav_prof", use_container_width=True): st.session_state.page = "Профиль"

# ================= ГЛАВНАЯ =================
if st.session_state.page == "Главная":
    st.markdown('<div class="gold-title">ZORNET</div>', unsafe_allow_html=True)
    
    # 1. ЗОЛОТЫЕ КНОПКИ БЫСТРОГО ДОСТУПА
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🤖 СПРОСИТЬ AI", use_container_width=True):
            st.session_state.page = "ZORNET AI"
            st.rerun()
    with col2:
        if st.button("💾 МОЙ ДИСК", use_container_width=True):
            st.session_state.page = "Диск"
            st.rerun()
    with col3:
        if st.button("🚌 РАСПИСАНИЕ", use_container_width=True):
            st.session_state.page = "Транспорт"
            st.rerun()

    st.markdown("---")

    # 2. ПОИСК (Работает лучше)
    search_query = st.text_input("", placeholder="🔍 Поиск в интернете...", label_visibility="collapsed")
    if search_query:
        st.markdown(f"### Результаты для: **{search_query}**")
        results = search_zornet(search_query)
        for res in results:
            st.markdown(f"""
            <div class="search-result">
                <a href="{res['url']}" target="_blank" style="font-size:18px; font-weight:bold;">{res['title']}</a>
                <p style="color:#ccc; margin-top:5px;">{res['snippet']}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # 3. РАЗВОРАЧИВАЮЩИЕСЯ ВКЛАДКИ (ТВОЯ ПРОСЬБА)
    st.subheader("📌 Инфо-панель")
    
    with st.expander("🌤️ Погода и Время (Развернуть)", expanded=True):
        tz = pytz.timezone('Europe/Minsk')
        now = datetime.datetime.now(tz)
        t_col1, t_col2, t_col3 = st.columns(3)
        t_col1.metric("Время (Минск)", now.strftime("%H:%M"))
        t_col2.metric("Погода", "-4°C", "Облачно")
        t_col3.metric("Дата", now.strftime("%d.%m.%Y"))

    with st.expander("💵 Курсы валют (Развернуть)"):
        c1, c2, c3 = st.columns(3)
        c1.metric("USD", "3.20 BYN", "+0.01")
        c2.metric("EUR", "3.45 BYN", "-0.02")
        c3.metric("RUB", "3.35 BYN", "0.00")

# ================= ZORNET AI (БЕЗ VPN) =================
elif st.session_state.page == "ZORNET AI":
    st.markdown('<div class="gold-title">🤖 ZORNET AI</div>', unsafe_allow_html=True)
    
    # История
    for msg in st.session_state.ai_messages:
        role_style = "user-message" if msg["role"] == "user" else "ai-message"
        st.markdown(f'<div class="{role_style}">{msg["content"]}</div>', unsafe_allow_html=True)
    
    # Ввод
    if prompt := st.chat_input("Напишите вопрос..."):
        st.session_state.ai_messages.append({"role": "user", "content": prompt})
        st.rerun()

    # Ответ AI (генерация после рерана)
    if st.session_state.ai_messages and st.session_state.ai_messages[-1]["role"] == "user":
        with st.spinner("ZORNET думает..."):
            last_msg = st.session_state.ai_messages[-1]["content"]
            response = ask_zornet_ai(last_msg)
            st.session_state.ai_messages.append({"role": "assistant", "content": response})
        st.rerun()

    if st.button("🗑️ Очистить диалог"):
        st.session_state.ai_messages = []
        st.rerun()

# ================= НОВОСТИ =================
elif st.session_state.page == "Новости":
    st.markdown('<div class="gold-title">📰 НОВОСТИ</div>', unsafe_allow_html=True)
    news = get_belta_news()
    for item in news:
        st.markdown(f"""
        <div style="background:#222; padding:15px; border-radius:10px; margin-bottom:15px; border-left:4px solid #FFD700;">
            <a href="{item.link}" style="font-size:20px; font-weight:bold; color:#FFD700;">{item.title}</a>
            <p style="margin-top:10px; color:#ddd;">{item.summary[:200]}...</p>
        </div>
        """, unsafe_allow_html=True)

# ================= ТРАНСПОРТ =================
elif st.session_state.page == "Транспорт":
    st.markdown('<div class="gold-title">🚌 ТРАНСПОРТ</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🚇 Метро", "🚌 Автобусы"])
    
    with tab1:
        for m in get_minsk_metro():
            st.success(f"🚇 **{m['name']}** (Линия {m['line']}) — через {m['next']}")
            
    with tab2:
        for b in get_bus_trams():
            st.info(f"🚌 **№{b['number']}** ({b['from']} - {b['to']}) — через {b['next']}")

# ================= ДИСК =================
elif st.session_state.page == "Диск":
    st.markdown('<div class="gold-title">💾 ДИСК</div>', unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader("Загрузить файл", accept_multiple_files=True)
    if uploaded_files:
        for f in uploaded_files:
            save_file(f.name, f.size)
        st.success("Файлы сохранены!")
        st.rerun()
        
    st.subheader("Ваши файлы")
    files = get_files()
    if files:
        for f in files:
            col1, col2 = st.columns([3, 1])
            col1.write(f"📄 **{f['name']}**")
            col2.write(f"{f['size']} байт")
            st.markdown("---")
    else:
        st.info("Диск пуст")

# ================= ПРОФИЛЬ =================
elif st.session_state.page == "Профиль":
    st.markdown('<div class="gold-title">👤 ПРОФИЛЬ</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown("""
        <div style="width:150px; height:150px; background:linear-gradient(45deg, #FFD700, #B8860B); 
        border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:60px; color:black; font-weight:bold;">Z</div>
        """, unsafe_allow_html=True)
    with c2:
        st.subheader("ZORNET USER")
        st.write("Статус: **Premium Gold**")
        st.write(f"Дата регистрации: {datetime.date.today()}")

    with st.expander("⚙️ Настройки"):
        st.text_input("Никнейм", value="User")
        st.button("Сохранить")
