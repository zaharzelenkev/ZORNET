import streamlit as st
import sqlite3
import datetime
import os
import pytz
import json
import requests
import feedparser
from PIL import Image
import io
import base64
from pathlib import Path
import mimetypes
import streamlit.components.v1 as components

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
if "weather_data" not in st.session_state:
    st.session_state.weather_data = None
if "user_city" not in st.session_state:
    st.session_state.user_city = None
if "camera_mode" not in st.session_state:
    st.session_state.camera_mode = "object"
if "camera_result" not in st.session_state:
    st.session_state.camera_result = None
if "ai_tab" not in st.session_state:
    st.session_state.ai_tab = "chat"
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None

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
    
    .ai-chat-container {
        background: white;
        border-radius: 15px;
        padding: 20px;
        margin: 20px 0;
        border: 2px solid #FFD700;
        box-shadow: 0 8px 25px rgba(218, 165, 32, 0.15);
    }
    
    .ai-message-user {
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%);
        color: white;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        margin-left: auto;
        margin-bottom: 10px;
        max-width: 80%;
        float: right;
        clear: both;
    }
    
    .ai-message-bot {
        background: #f8f9fa;
        color: #1a1a1a;
        padding: 12px 18px;
        border-radius: 18px 18px 18px 4px;
        margin-right: auto;
        margin-bottom: 10px;
        max-width: 80%;
        border-left: 4px solid #DAA520;
        float: left;
        clear: both;
    }
    
    .camera-container {
        background: white;
        border-radius: 15px;
        padding: 25px;
        margin: 20px 0;
        border: 2px solid #4a90e2;
        box-shadow: 0 8px 25px rgba(74, 144, 226, 0.15);
    }
    
    .mode-btn {
        background: #4a90e2 !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px !important;
        margin: 5px !important;
        transition: all 0.3s ease !important;
    }
    
    .mode-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(74, 144, 226, 0.3) !important;
    }
    
    .mode-btn.active {
        background: #2c6cb0 !important;
        box-shadow: inset 0 2px 5px rgba(0,0,0,0.2) !important;
    }
    
    .result-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        border-left: 4px solid #DAA520;
    }
    
    .main-btn {
        background: linear-gradient(135deg, #DAA520 0%, #B8860B 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 15px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        margin: 5px 0 !important;
        transition: all 0.3s ease !important;
    }
    
    .main-btn:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 20px rgba(218, 165, 32, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= САЙДБАР =================
with st.sidebar:
    st.markdown("<h3 style='color:#DAA520;'>🇧🇾 ZORNET</h3>", unsafe_allow_html=True)

    pages = [
        ("🏠", "ГЛАВНАЯ", "Главная"),
        ("🤖", "ZORNET AI", "ZORNET AI"),
        ("📷", "УМНАЯ КАМЕРА", "Умная камера"),
        ("📰", "НОВОСТИ", "Новости"),
        ("🌤️", "ПОГОДА", "Погода"),
        ("💾", "ДИСК", "Диск"),
        ("👤", "ПРОФИЛЬ", "Профиль"),
    ]

    for i, (icon, text, page) in enumerate(pages):
        if st.button(f"{icon} {text}", key=f"nav_{i}_{page}", use_container_width=True):
            st.session_state.page = page
            st.rerun()

# ================= ФУНКЦИИ УМНОЙ КАМЕРЫ =================
def detect_objects_simple(image):
    """Простое распознавание объектов по цветам и формам"""
    # Конвертируем в RGB
    rgb_image = image.convert('RGB')
    pixels = list(rgb_image.getdata())
    
    # Анализ доминирующих цветов
    color_counts = {}
    for r, g, b in pixels[:1000]:  # Берем только первые 1000 пикселей для скорости
        # Группируем похожие цвета
        color_key = (r//50, g//50, b//50)
        color_counts[color_key] = color_counts.get(color_key, 0) + 1
    
    # Определяем что это может быть
    dominant_color = max(color_counts, key=color_counts.get)
    
    # Простая логика распознавания
    width, height = image.size
    aspect_ratio = width / height
    
    if aspect_ratio > 1.5:
        shape = "горизонтальный объект (возможно экран или книга)"
    elif aspect_ratio < 0.7:
        shape = "вертикальный объект (возможно человек или здание)"
    else:
        shape = "квадратный объект"
    
    # Определение по доминирующему цвету
    r, g, b = dominant_color
    if g > r and g > b:
        color_desc = "зеленый объект (возможно природа, растения)"
    elif r > g and r > b:
        color_desc = "красный объект"
    elif b > r and b > g:
        color_desc = "синий объект (возможно небо или вода)"
    else:
        color_desc = "нейтральный объект"
    
    return [f"📏 Размер: {width}x{height} пикселей",
            f"🎨 {color_desc}",
            f"📐 {shape}",
            "💡 Совет: Для точного распознавания используйте четкие фото при хорошем освещении"]

def extract_text_simple(image):
    """Простейшее извлечение текста (заглушка)"""
    return ["🔍 Режим распознавания текста",
           "⚠️ Для работы этой функции установите библиотеку pytesseract:",
           "pip install pytesseract",
           "📝 И установите Tesseract OCR с русского языком"]

def translate_text_simple(text):
    """Простой перевод через API (заглушка)"""
    return ["🌐 Режим перевода",
           "⚠️ Для работы этой функции установите:",
           "pip install googletrans==4.0.0-rc1",
           "📚 Или используйте Google Translate онлайн"]

def process_camera_image(image, mode):
    """Обработка изображения"""
    if mode == "object":
        return detect_objects_simple(image)
    elif mode == "text":
        return extract_text_simple(image)
    elif mode == "translate":
        return translate_text_simple("пример текста")
    elif mode == "qr":
        return ["📱 QR-код распознан!", 
                "Для работы с QR-кодами установите:",
                "pip install qrcode[pil]",
                "pip install pyzbar",
                "pip install pillow"]
    return ["Выберите режим работы"]

# ================= AI ФУНКЦИИ =================
def ask_simple_ai(prompt: str) -> str:
    """Простой AI на основе правил"""
    prompt_lower = prompt.lower()
    
    # Правила для ответов
    if any(word in prompt_lower for word in ["привет", "здравствуй", "добрый"]):
        return "Привет! Я ZORNET AI 🤖\nЧем могу помочь?"
    
    elif any(word in prompt_lower for word in ["погода", "дождь", "солнце", "температура"]):
        return "🌤️ Погоду можно узнать на вкладке 'Погода'!\nТам точные данные для вашего города."
    
    elif any(word in prompt_lower for word in ["новости", "события", "происшествия"]):
        return "📰 Новости на вкладке 'Новости' - свежие статьи из проверенных источников!"
    
    elif any(word in prompt_lower for word in ["время", "час", "сколько время"]):
        current_time = datetime.datetime.now(pytz.timezone('Europe/Minsk'))
        return f"🕒 Сейчас в Минске: {current_time.strftime('%H:%M:%S')}"
    
    elif any(word in prompt_lower for word in ["помощь", "помоги", "как пользоваться"]):
        return """📚 ZORNET включает:
1. 🤖 AI-помощник (это я!)
2. 📷 Умную камеру
3. 📰 Новости
4. 🌤️ Погоду
5. 💾 Облачный диск
6. 👤 Профиль

Выберите нужную вкладку в меню слева!"""
    
    elif any(word in prompt_lower for word in ["беларусь", "минск", "белоруссия"]):
        return "🇧🇾 ZORNET создан в Беларуси!\nГорода: Минск, Гомель, Витебск, Брест, Гродно, Могилёв."
    
    else:
        # Общий ответ
        responses = [
            "Интересный вопрос! Рекомендую поискать на вкладке 'Главная'.",
            "Хороший вопрос! ZORNET постоянно развивается.",
            "Сейчас у меня нет точного ответа, но вы можете:\n1. Использовать поиск\n2. Проверить новости\n3. Узнать погоду",
            "🤖 Я еще учусь! Спросите о погоде, новостях или времени."
        ]
        import random
        return random.choice(responses)

# ================= СТРАНИЦА ZORNET AI =================
if st.session_state.page == "ZORNET AI":
    st.markdown('<div class="gold-title">🤖 ZORNET AI</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="ai-chat-container">
        <h3 style="color: #DAA520; text-align: center;">✨ Ваш персональный AI-помощник</h3>
        <p style="text-align: center; color: #666;">Задавайте вопросы — я помогу!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Быстрые кнопки
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💬 Чат", use_container_width=True):
            st.session_state.ai_tab = "chat"
    
    with col2:
        if st.button("🎨 Рисовать", use_container_width=True):
            st.session_state.ai_tab = "draw"
    
    with col3:
        if st.button("📝 Текст", use_container_width=True):
            st.session_state.ai_tab = "text"
    
    # ЧАТ С AI
    if st.session_state.ai_tab == "chat":
        st.markdown("### 💬 Чат с ZORNET AI")
        
        # Показ истории
        for msg in st.session_state.ai_messages[-10:]:  # Последние 10 сообщений
            if msg["role"] == "user":
                st.markdown(f'<div class="ai-message-user">{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="ai-message-bot">{msg["content"]}</div>', unsafe_allow_html=True)
        
        # Поле ввода
        user_input = st.text_area("Ваше сообщение:", height=100, 
                                  placeholder="Напишите что-нибудь...")
        
        col_send, col_clear = st.columns(2)
        
        with col_send:
            if st.button("🚀 Отправить", type="primary", use_container_width=True):
                if user_input.strip():
                    # Добавляем сообщение пользователя
                    st.session_state.ai_messages.append({"role": "user", "content": user_input})
                    
                    # Получаем ответ
                    response = ask_simple_ai(user_input)
                    st.session_state.ai_messages.append({"role": "assistant", "content": response})
                    
                    st.rerun()
        
        with col_clear:
            if st.button("🗑️ Очистить", use_container_width=True):
                st.session_state.ai_messages = []
                st.rerun()
    
    # РИСОВАНИЕ
    elif st.session_state.ai_tab == "draw":
        st.markdown("### 🎨 Генератор рисунков")
        
        drawing_mode = st.selectbox("Выберите тип:", ["Пейзаж", "Портрет", "Абстракция", "Техника"])
        color = st.color_picker("Выберите цвет:", "#DAA520")
        
        if st.button("✨ Создать рисунок", type="primary", use_container_width=True):
            # Создаем простой рисунок
            img = Image.new('RGB', (400, 300), color=color)
            
            # Добавляем простые фигуры
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            
            if drawing_mode == "Пейзаж":
                draw.rectangle([0, 200, 400, 300], fill="#228B22")  # Трава
                draw.rectangle([100, 100, 300, 200], fill="#87CEEB")  # Озеро
                draw.polygon([(150, 50), (250, 50), (200, 10)], fill="#8B4513")  # Гора
                
            elif drawing_mode == "Портрет":
                draw.ellipse([150, 50, 250, 150], fill="#FFE4B5")  # Лицо
                draw.ellipse([170, 80, 190, 100], fill="#000000")  # Глаз 1
                draw.ellipse([210, 80, 230, 100], fill="#000000")  # Глаз 2
                draw.arc([180, 120, 220, 140], start=0, end=180, fill="#FF0000", width=3)  # Улыбка
                
            st.image(img, caption=f"Созданный рисунок: {drawing_mode}", use_column_width=True)
            
            # Сохранение
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.download_button(
                label="📥 Скачать рисунок",
                data=byte_im,
                file_name="zornet_drawing.png",
                mime="image/png",
                use_container_width=True
            )
    
    # ГЕНЕРАТОР ТЕКСТА
    elif st.session_state.ai_tab == "text":
        st.markdown("### 📝 Генератор текста")
        
        text_type = st.selectbox("Тип текста:", 
                                ["Приветствие", "Описание", "Сообщение", "Идея"])
        
        topic = st.text_input("Тема:", placeholder="О чём написать?")
        
        if st.button("✍️ Сгенерировать", type="primary", use_container_width=True):
            if topic:
                # Шаблоны текстов
                templates = {
                    "Приветствие": f"Добро пожаловать в тему '{topic}'! Рад вас видеть здесь.",
                    "Описание": f"Тема '{topic}' очень интересна. Она включает различные аспекты...",
                    "Сообщение": f"По теме '{topic}' хочу сообщить важную информацию...",
                    "Идея": f"Идея по теме '{topic}': можно реализовать проект, который..."
                }
                
                text = templates.get(text_type, f"Текст на тему '{topic}'")
                
                st.markdown(f"""
                <div class="result-card">
                    <h4>📄 Результат:</h4>
                    <p style="margin-top: 10px;">{text}</p>
                </div>
                """, unsafe_allow_html=True)

# ================= СТРАНИЦА УМНОЙ КАМЕРЫ =================
elif st.session_state.page == "Умная камера":
    st.markdown('<div class="gold-title">📷 УМНАЯ КАМЕРА</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="camera-container">
        <h3 style="color: #4a90e2; text-align: center;">🔍 Сфотографируйте что угодно</h3>
        <p style="text-align: center; color: #666;">Распознавание объектов и многое другое</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Режимы
    st.markdown("### 🎯 Выберите режим")
    
    modes = [
        ("🔍 Распознавание объектов", "object"),
        ("📝 Сканирование текста", "text"),
        ("🌐 Перевод", "translate"),
        ("📱 QR-коды", "qr")
    ]
    
    cols = st.columns(4)
    for idx, (name, mode) in enumerate(modes):
        with cols[idx]:
            is_active = st.session_state.camera_mode == mode
            if st.button(name, 
                        key=f"mode_{mode}",
                        help=f"Режим: {name}",
                        use_container_width=True):
                st.session_state.camera_mode = mode
                st.rerun()
    
    # Загрузка изображения
    st.markdown("### 📸 Загрузите изображение")
    
    uploaded_file = st.file_uploader(
        "Выберите файл",
        type=['jpg', 'jpeg', 'png', 'bmp', 'gif'],
        help="Поддерживаются JPG, PNG, BMP, GIF"
    )
    
    if uploaded_file is not None:
        # Открываем и показываем изображение
        image = Image.open(uploaded_file)
        st.image(image, caption="Загруженное изображение", use_column_width=True)
        
        # Сохраняем в session state
        st.session_state.uploaded_image = image
        
        # Кнопка анализа
        if st.button("🚀 Анализировать изображение", type="primary", use_container_width=True):
            with st.spinner("Анализирую..."):
                results = process_camera_image(image, st.session_state.camera_mode)
                st.session_state.camera_result = results
        
        # Показ результатов
        if st.session_state.camera_result:
            st.markdown("### 📊 Результаты")
            
            for result in st.session_state.camera_result:
                st.markdown(f"""
                <div class="result-card">
                    <p>{result}</p>
                </div>
                """, unsafe_allow_html=True)
    
    # Примеры
    st.markdown("---")
    st.markdown("### 💡 Примеры использования")
    
    with st.expander("🛒 В магазине"):
        st.write("Сфотографируйте товар — узнайте что это")
        
    with st.expander("📖 В библиотеке"):
        st.write("Сфотографируйте текст — получите информацию")
        
    with st.expander("🏛️ В музее"):
        st.write("Наведите на экспонат — узнайте историю")

# ================= СТРАНИЦА ГЛАВНАЯ =================
if st.session_state.page == "Главная":
    st.markdown('<div class="gold-title">ZORNET</div>', unsafe_allow_html=True)

    current_time = datetime.datetime.now(pytz.timezone('Europe/Minsk'))
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.button(f"🕒 {current_time.strftime('%H:%M')}\nМинск", use_container_width=True)
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

    st.markdown("---")

    search_query = st.text_input(
        "",
        placeholder="Поиск в интернете...",
        key="main_search",
        label_visibility="collapsed"
    )

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

# ================= СТРАНИЦА ПОГОДЫ (ПРОСТО И РАБОЧЕ) =================
elif st.session_state.page == "Погода":
    st.markdown('<div class="gold-title">🌤️ ПОГОДА</div>', unsafe_allow_html=True)

    # По умолчанию показываем Минск
    default_city = "Минск"

    # Поисковая строка
    col1, col2 = st.columns([3, 1])
    with col1:
        city_input = st.text_input(
            "🔍 Введите ваш город",
            placeholder="Например: Минск, Гомель, Брест...",
            key="weather_city_input"
        )

    with col2:
        search_clicked = st.button("Найти", type="primary", use_container_width=True)

    # Определяем какой город показывать
    city_to_show = default_city
    if search_clicked and city_input:
        city_to_show = city_input
    elif 'user_city' in st.session_state:
        city_to_show = st.session_state.user_city

    # Получаем погоду для города
    with st.spinner(f"Получаю погоду для {city_to_show}..."):
        weather_data = get_weather_by_city(city_to_show)

        if not weather_data:
            # Если город не найден, показываем Минск
            st.error(f"Город '{city_to_show}' не найден. Показываю погоду в Минске.")
            weather_data = get_weather_by_city(default_city)
            city_to_show = default_city

        if weather_data:
            current = weather_data["current"]

            # Сохраняем город в сессии
            st.session_state.user_city = city_to_show
            st.session_state.weather_data = weather_data

            # Показываем город
            st.markdown(f"### 🌤️ Погода в {current['city']}, {current['country']}")

            # Основная информация
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

            # Детали погоды
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

            # Показываем детали в 2 колонки
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

            # Прогноз на 5 дней
            if weather_data.get("forecast"):
                st.markdown("#### 📅 Прогноз на 5 дней")

                forecast = weather_data["forecast"]["list"]
                days = {}

                for item in forecast:
                    date = item["dt_txt"].split(" ")[0]
                    if date not in days:
                        days[date] = item

                # Берем максимум 5 дней
                forecast_dates = list(days.keys())[:5]

                # Показываем прогноз в ряд
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

    # Блок с городами Беларуси
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

    # Показываем города в 3 колонки
    cols = st.columns(3)
    for idx, (city, description) in enumerate(belarus_cities):
        with cols[idx % 3]:
            if st.button(f"**{city}**", key=f"city_{city}", help=description, use_container_width=True):
                # При нажатии на кнопку города, ищем погоду для него
                st.session_state.user_city = city
                st.rerun()

# ================= ПРОФЕССИОНАЛЬНЫЙ ОБЛАЧНЫЙ ДИСК ZORNET DISK =================
elif st.session_state.page == "Диск":
    st.markdown('<div class="gold-title">💾 ДИСК</div>', unsafe_allow_html=True)

    # Инициализация сессионных переменных
    if "disk_current_path" not in st.session_state:
        st.session_state.disk_current_path = "zornet_cloud"

    if "disk_action" not in st.session_state:
        st.session_state.disk_action = "view"  # view, upload, new_folder, search

    # Создаем корневую папку если не существует
    import os

    os.makedirs(st.session_state.disk_current_path, exist_ok=True)

    # CSS стили для диска
    st.markdown("""
    <style>
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
    </style>
    """, unsafe_allow_html=True)


    # Функции для работы с диском
    def get_file_icon(filename):
        """Возвращает иконку для файла"""
        if filename.endswith('/'):
            return "📁"
        elif filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            return "🖼️"
        elif filename.lower().endswith('.pdf'):
            return "📄"
        elif filename.lower().endswith(('.doc', '.docx')):
            return "📝"
        elif filename.lower().endswith(('.mp3', '.wav')):
            return "🎵"
        elif filename.lower().endswith(('.mp4', '.avi', '.mov')):
            return "🎬"
        elif filename.lower().endswith(('.zip', '.rar', '.7z')):
            return "🗜️"
        elif filename.lower().endswith(('.py', '.js', '.html', '.css')):
            return "💻"
        else:
            return "📄"


    def format_file_size(size_bytes):
        """Форматирует размер файла"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


    def get_disk_stats():
        """Получает статистику диска"""
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

    # СТАТИСТИКА ХРАНИЛИЩА
    stats = get_disk_stats()
    used_gb = stats['total_size'] / (1024 * 1024 * 1024)
    used_percent = min(100, (used_gb / 1.0) * 100)  # Предполагаем 1GB лимит

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
                for item in found_items[:10]:  # Показываем первые 10
                    icon = "📁" if item['is_dir'] else get_file_icon(item['name'])
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

        # Быстрая загрузка (всегда доступна)
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
        if st.session_state.disk_current_path != "zornet_cloud":
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
                    icon = "📁" if is_dir else get_file_icon(item)

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
                                # Превью файла
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

# ================= СТРАНИЦА ПРОФИЛЯ (ПРОФЕССИОНАЛЬНАЯ ВЕРСИЯ) =================
elif st.session_state.page == "Профиль":

    # CSS для профиля
    st.markdown("""
    <style>
    /* ЗОЛОТОЙ ЗАГОЛОВОК */
    .profile-gold-title {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(135deg, #FFD700 0%, #B8860B 50%, #DAA520 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 3px;
        margin: 20px 0 40px 0;
        padding: 10px;
    }

    /* КОНТЕЙНЕРЫ */
    .profile-container {
        background: white;
        border-radius: 20px;
        padding: 30px;
        margin: 20px 0;
        box-shadow: 0 10px 40px rgba(218, 165, 32, 0.1);
        border: 1px solid rgba(218, 165, 32, 0.2);
    }

    .login-container {
        background: linear-gradient(135deg, #ffffff 0%, #fffaf0 100%);
        border-radius: 20px;
        padding: 40px;
        margin: 20px auto;
        max-width: 500px;
        box-shadow: 0 15px 50px rgba(218, 165, 32, 0.15);
        border: 1px solid #FFD700;
    }

    /* КАРТОЧКИ */
    .profile-card {
        background: #f9f9f9;
        border-radius: 15px;
        padding: 25px;
        margin: 15px 0;
        border-left: 5px solid #DAA520;
        transition: transform 0.3s ease;
    }

    .profile-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(218, 165, 32, 0.15);
    }

    /* КНОПКИ */
    .gold-button {
        background: linear-gradient(135deg, #FFD700 0%, #DAA520 100%) !important;
        border: none !important;
        color: white !important;
        border-radius: 10px !important;
        padding: 12px 30px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        box-shadow: 0 5px 20px rgba(218, 165, 32, 0.3) !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }

    .gold-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(218, 165, 32, 0.4) !important;
    }

    .outline-button {
        background: transparent !important;
        border: 2px solid #DAA520 !important;
        color: #DAA520 !important;
        border-radius: 10px !important;
        padding: 12px 30px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }

    .outline-button:hover {
        background: rgba(218, 165, 32, 0.1) !important;
    }

    /* ПОЛЯ ВВОДА */
    .stTextInput > div > div > input {
        border-radius: 10px !important;
        border: 2px solid #e0e0e0 !important;
        padding: 12px 15px !important;
        font-size: 16px !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #DAA520 !important;
        box-shadow: 0 0 0 3px rgba(218, 165, 32, 0.1) !important;
    }

    /* ПЕРЕКЛЮЧАТЕЛИ */
    .stCheckbox > div > label {
        font-weight: 500;
        color: #333;
    }

    /* АВАТАРКА */
    .avatar-container {
        width: 180px;
        height: 180px;
        border-radius: 50%;
        background: linear-gradient(135deg, #FFD700, #DAA520);
        padding: 5px;
        margin: 0 auto 25px auto;
    }

    .avatar-img {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        object-fit: cover;
        border: 4px solid white;
    }

    /* СТАТУС */
    .status-online {
        display: inline-block;
        width: 12px;
        height: 12px;
        background: #4CAF50;
        border-radius: 50%;
        margin-right: 8px;
        vertical-align: middle;
    }

    /* ИКОНКИ СТАТИСТИКИ */
    .stat-icon {
        font-size: 2.5rem;
        color: #DAA520;
        margin-bottom: 10px;
    }

    /* БЭДЖИ */
    .gold-badge {
        background: linear-gradient(135deg, #FFD700, #DAA520);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
        display: inline-block;
        margin: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Инициализация состояния профиля
    if "user_logged_in" not in st.session_state:
        st.session_state.user_logged_in = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "user_avatar" not in st.session_state:
        st.session_state.user_avatar = None
    if "show_login" not in st.session_state:
        st.session_state.show_login = True
    if "show_register" not in st.session_state:
        st.session_state.show_register = False


    # Функции базы данных для профилей
    def init_profile_db():
        """Инициализация базы данных профилей"""
        conn = sqlite3.connect("zornet_profiles.db")
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                username TEXT,
                password_hash TEXT,
                avatar_path TEXT,
                gender TEXT,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                bio TEXT,
                settings TEXT
            )
        """)
        conn.commit()
        conn.close()


    def register_user(email, username, password):
        """Регистрация нового пользователя"""
        try:
            conn = sqlite3.connect("zornet_profiles.db")
            c = conn.cursor()
            # Простой хэш (в реальном приложении используйте hashlib)
            password_hash = password  # Здесь должен быть реальный хэш
            c.execute("""
                INSERT INTO profiles (email, username, password_hash)
                VALUES (?, ?, ?)
            """, (email, username, password_hash))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False  # Пользователь уже существует
        except Exception as e:
            print(f"Ошибка регистрации: {e}")
            return False


    def login_user(email, password):
        """Авторизация пользователя"""
        try:
            conn = sqlite3.connect("zornet_profiles.db")
            c = conn.cursor()
            c.execute("""
                SELECT username, password_hash FROM profiles 
                WHERE email = ?
            """, (email,))
            result = c.fetchone()
            conn.close()

            if result and result[1] == password:  # Сравнение хэшей
                return result[0]  # Возвращаем имя пользователя
            return None
        except:
            return None


    def update_profile(email, username, gender, bio):
        """Обновление профиля"""
        try:
            conn = sqlite3.connect("zornet_profiles.db")
            c = conn.cursor()
            c.execute("""
                UPDATE profiles 
                SET username = ?, gender = ?, bio = ?
                WHERE email = ?
            """, (username, gender, bio, email))
            conn.commit()
            conn.close()
            return True
        except:
            return False


    def save_avatar(email, avatar_path):
        """Сохранение пути к аватарке"""
        try:
            conn = sqlite3.connect("zornet_profiles.db")
            c = conn.cursor()
            c.execute("""
                UPDATE profiles 
                SET avatar_path = ?
                WHERE email = ?
            """, (avatar_path, email))
            conn.commit()
            conn.close()
            return True
        except:
            return False


    def get_user_profile(email):
        """Получение профиля пользователя"""
        try:
            conn = sqlite3.connect("zornet_profiles.db")
            c = conn.cursor()
            c.execute("""
                SELECT username, gender, bio, avatar_path, join_date 
                FROM profiles 
                WHERE email = ?
            """, (email,))
            result = c.fetchone()
            conn.close()

            if result:
                return {
                    "username": result[0],
                    "gender": result[1],
                    "bio": result[2],
                    "avatar_path": result[3],
                    "join_date": result[4]
                }
            return None
        except:
            return None


    # Инициализация БД
    init_profile_db()

    st.markdown('<div class="profile-gold-title">👤 ПРОФИЛЬ</div>', unsafe_allow_html=True)

    # Если пользователь не авторизован, показываем форму входа/регистрации
    if not st.session_state.user_logged_in:
        col_login, col_register = st.columns(2)

        with col_login:
            if st.session_state.show_login:
                st.markdown("""
                <div class="login-container">
                    <h2 style="text-align: center; color: #DAA520; margin-bottom: 30px;">🔐 Вход в систему</h2>
                """, unsafe_allow_html=True)

                with st.form("login_form"):
                    login_email = st.text_input("📧 Email", placeholder="your@email.com")
                    login_password = st.text_input("🔑 Пароль", type="password", placeholder="••••••••")

                    col_submit, col_switch = st.columns(2)
                    with col_submit:
                        login_submit = st.form_submit_button("🚀 Войти", use_container_width=True)
                    with col_switch:
                        if st.form_submit_button("📝 Регистрация", use_container_width=True):
                            st.session_state.show_login = False
                            st.session_state.show_register = True
                            st.rerun()

                    if login_submit and login_email and login_password:
                        with st.spinner("Вход в систему..."):
                            username = login_user(login_email, login_password)
                            if username:
                                st.session_state.user_logged_in = True
                                st.session_state.user_email = login_email
                                st.session_state.user_name = username
                                st.success(f"Добро пожаловать, {username}!")
                                st.rerun()
                            else:
                                st.error("Неверный email или пароль")

                st.markdown("</div>", unsafe_allow_html=True)

        with col_register:
            if st.session_state.show_register:
                st.markdown("""
                <div class="login-container">
                    <h2 style="text-align: center; color: #DAA520; margin-bottom: 30px;">✨ Регистрация</h2>
                """, unsafe_allow_html=True)

                with st.form("register_form"):
                    reg_email = st.text_input("📧 Email", placeholder="your@email.com")
                    reg_username = st.text_input("👤 Имя пользователя", placeholder="Ваше имя")
                    reg_password = st.text_input("🔑 Пароль", type="password", placeholder="••••••••")
                    reg_password_confirm = st.text_input("🔐 Подтвердите пароль", type="password",
                                                         placeholder="••••••••")
                    reg_gender = st.selectbox("⚧ Пол", ["Не указан", "Мужской", "Женский"])

                    col_submit_reg, col_switch_reg = st.columns(2)
                    with col_submit_reg:
                        reg_submit = st.form_submit_button("🎯 Зарегистрироваться", use_container_width=True)
                    with col_switch_reg:
                        if st.form_submit_button("← Назад к входу", use_container_width=True):
                            st.session_state.show_login = True
                            st.session_state.show_register = False
                            st.rerun()

                    if reg_submit:
                        if not all([reg_email, reg_username, reg_password, reg_password_confirm]):
                            st.error("Заполните все поля!")
                        elif reg_password != reg_password_confirm:
                            st.error("Пароли не совпадают!")
                        else:
                            with st.spinner("Регистрация..."):
                                if register_user(reg_email, reg_username, reg_password):
                                    st.success("Регистрация успешна! Теперь войдите в систему.")
                                    st.session_state.show_login = True
                                    st.session_state.show_register = False
                                    st.rerun()
                                else:
                                    st.error("Пользователь с таким email уже существует")

                st.markdown("</div>", unsafe_allow_html=True)

    # Если пользователь авторизован, показываем профиль
    else:
        # Загружаем данные профиля
        profile_data = get_user_profile(st.session_state.user_email)

        # Кнопка выхода
        if st.sidebar.button("🚪 Выйти", use_container_width=True):
            st.session_state.user_logged_in = False
            st.session_state.user_email = ""
            st.session_state.user_name = ""
            st.session_state.user_avatar = None
            st.rerun()

        # Основной контейнер профиля
        with st.container():
            st.markdown('<div class="profile-container">', unsafe_allow_html=True)

            col_profile_left, col_profile_right = st.columns([1, 2])

            with col_profile_left:
                # Аватарка пользователя
                st.markdown("""
                <div class="avatar-container">
                    <img src="https://via.placeholder.com/200/FFD700/FFFFFF?text=""" +
                            (st.session_state.user_name[0] if st.session_state.user_name else "Z") +
                            """&font-size=80" class="avatar-img">
                        </div>
                        """, unsafe_allow_html=True)

                # Загрузка аватарки
                uploaded_avatar = st.file_uploader("📷 Загрузить фото профиля",
                                                   type=['jpg', 'jpeg', 'png'],
                                                   key="avatar_uploader")

                if uploaded_avatar:
                    # Сохраняем временно в session state
                    st.session_state.user_avatar = uploaded_avatar
                    # Сохраняем в базу данных
                    avatar_path = f"avatars/{st.session_state.user_email}_{uploaded_avatar.name}"
                    save_avatar(st.session_state.user_email, avatar_path)
                    st.success("Фото профиля обновлено!")
                    st.rerun()

                # Статус
                st.markdown("""
                <div style="text-align: center; margin: 20px 0;">
                    <span class="status-online"></span>
                    <span style="color: #4CAF50; font-weight: 600;">Онлайн</span>
                </div>
                """, unsafe_allow_html=True)

            with col_profile_right:
                # Информация профиля
                with st.form("profile_info_form"):
                    st.markdown("### 📝 Информация профиля")

                    username = st.text_input("👤 Имя пользователя",
                                             value=profile_data[
                                                 "username"] if profile_data else st.session_state.user_name)

                    email = st.text_input("📧 Email",
                                          value=st.session_state.user_email,
                                          disabled=True)

                    gender = st.selectbox("⚧ Пол",
                                          ["Не указан", "Мужской", "Женский"],
                                          index=["Не указан", "Мужской", "Женский"].index(
                                              profile_data["gender"] if profile_data and profile_data[
                                                  "gender"] else "Не указан"
                                          ))

                    bio = st.text_area("📖 О себе",
                                       value=profile_data["bio"] if profile_data and profile_data["bio"] else "",
                                       height=100,
                                       placeholder="Расскажите о себе...")

                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        save_profile = st.form_submit_button("💾 Сохранить изменения", use_container_width=True)
                    with col_cancel:
                        st.form_submit_button("Отмена", use_container_width=True)

                    if save_profile:
                        if update_profile(st.session_state.user_email, username, gender, bio):
                            st.session_state.user_name = username
                            st.success("Профиль успешно обновлен!")
                            st.rerun()
                        else:
                            st.error("Ошибка при обновлении профиля")

            st.markdown('</div>', unsafe_allow_html=True)

        # Статистика в отдельном контейнере
        st.markdown('<div class="profile-container">', unsafe_allow_html=True)
        st.markdown("### 📊 Статистика")

        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

        with col_stat1:
            st.markdown("""
            <div style="text-align: center;">
                <div class="stat-icon">📅</div>
                <h3>365</h3>
                <p>Дней с нами</p>
            </div>
            """, unsafe_allow_html=True)

        with col_stat2:
            st.markdown("""
            <div style="text-align: center;">
                <div class="stat-icon">📂</div>
                <h3>128</h3>
                <p>Файлов в облаке</p>
            </div>
            """, unsafe_allow_html=True)

        with col_stat3:
            st.markdown("""
            <div style="text-align: center;">
                <div class="stat-icon">🤖</div>
                <h3>2.4K</h3>
                <p>Запросов к AI</p>
            </div>
            """, unsafe_allow_html=True)

        with col_stat4:
            st.markdown("""
            <div style="text-align: center;">
                <div class="stat-icon">🎯</div>
                <h3>95%</h3>
                <p>Активность</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Настройки в отдельном контейнере
        st.markdown('<div class="profile-container">', unsafe_allow_html=True)
        st.markdown("### ⚙️ Настройки")

        settings_col1, settings_col2 = st.columns(2)

        with settings_col1:
            st.markdown("**🔔 Уведомления**")
            email_notif = st.checkbox("Email уведомления", value=True)
            push_notif = st.checkbox("Push-уведомления", value=True)
            ai_notif = st.checkbox("Уведомления от AI", value=True)

        with settings_col2:
            st.markdown("**🔒 Безопасность**")
            two_factor = st.checkbox("Двухфакторная аутентификация")
            login_history = st.button("📋 История входов", use_container_width=True)

        if st.button("💾 Сохранить настройки", type="primary", use_container_width=True):
            st.success("Настройки сохранены!")

        st.markdown('</div>', unsafe_allow_html=True)

        # Информация о подписке
        st.markdown('<div class="profile-container">', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

# ================= ИНИЦИАЛИЗАЦИЯ =================
if __name__ == "__main__":
    init_db()
    init_disk_db()
