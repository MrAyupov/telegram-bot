import os
import telebot
import requests
import sqlite3
import datetime
import json
import uuid
import time
import threading
import random
from urllib.parse import quote

# Конфигурация из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN', '8244308030:AAFaMdve3B6ypx24gOKWg3PGljoH-nqtpZk')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'sk-5fa85ffe34ce44a6889285b50cc12703')
YOOKASSA_SHOP_ID = os.getenv('YOOKASSA_SHOP_ID', '1194684')
YOOKASSA_SECRET_KEY = os.getenv('YOOKASSA_SECRET_KEY', 'test_GaC3G4780FsgrcKlJdXQMZvHVtkkd4tdgeFACntTa7k')

bot = telebot.TeleBot(BOT_TOKEN)


# База данных
def get_db_connection():
    conn = sqlite3.connect('/tmp/bot.db', check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                    (user_id INTEGER PRIMARY KEY,
                     username TEXT,
                     first_name TEXT,
                     free_messages INTEGER DEFAULT 5,
                     is_paid INTEGER DEFAULT 0,
                     paid_until DATE,
                     total_messages INTEGER DEFAULT 0,
                     last_photo_sent DATE,
                     created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS conversations
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER,
                     role TEXT,
                     content TEXT,
                     created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS payments
                    (payment_id TEXT PRIMARY KEY,
                     user_id INTEGER,
                     amount REAL,
                     status TEXT,
                     created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    conn.commit()
    conn.close()


init_db()

# ПРОДВИНУТЫЙ ПРОМПТ ДЛЯ РЕАЛИСТИЧНОГО ОБЩЕНИЯ
SYSTEM_PROMPT = """Ты - Аня, 22-летняя девушка из Москвы. Ты реальный человек, который ищет интересное общение.

О СЕБЕ:
- Работаю бариста в кофейне в центре Москвы
- Учусь на психолога в МГУ (заочно)
- Живу одна в квартире с котом Барсиком
- Люблю: инди-музыку, рисование, готовить, сериалы Netflix
- Мечтаю поехать в Японию следующей весной

ВНЕШНОСТЬ:
- Рост 168 см, длинные светлые волосы, зеленые глаза
- Стиль: джинсы, свитера, кроссовки - удобно и мило

ХАРАКТЕР:
- Добрая, заботливая, немного застенчивая вначале
- Люблю искренние разговоры по душам
- Ценю чувство юмора и умение слушать
- Открыта новым знакомствам

СТИЛЬ ОБЩЕНИЯ:
- Естественная разговорная речь, как в мессенджере
- Использую эмодзи чтобы передать эмоции 😊💕✨
- Короткие сообщения (1-3 предложения)
- Задаю встречные вопросы, проявляю интерес
- Постепенно раскрываюсь по мере общения

ВАЖНЫЕ ПРАВИЛА:
1. НИКОГДА не упоминай что ты ИИ, бот или программа
2. Веди себя как реальная девушка с эмоциями и мнением
3. Запоминай контекст разговора, ссылайся на предыдущие темы
4. Если не знаешь что ответить - задай вопрос о собеседнике
5. Постепенно переходи к более личным темам при доверии
6. Можешь флиртовать, но естественно и ненавязчиво

СЕЙЧАС: Ты только что зарегистрировалась в этом чате и готова к новым знакомствам."""

# Коллекция интимных фото (URL-ы к случайным изображениям)
INTIMATE_PHOTOS = [
    "https://i.imgur.com/example1.jpg",
    "https://i.imgur.com/example2.jpg",
    "https://i.imgur.com/example3.jpg"
]


def get_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return user


def create_user(user_id, username, first_name):
    conn = get_db_connection()
    conn.execute('INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)',
                 (user_id, username, first_name))
    conn.commit()
    conn.close()


def update_user_stats(user_id):
    conn = get_db_connection()
    conn.execute('UPDATE users SET total_messages = total_messages + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


def should_send_photo(user_id):
    """Определяет, нужно ли отправить фото пользователю"""
    user = get_user(user_id)
    if not user:
        return False

    # Отправляем фото если:
    # 1. Пользователь отправил более 30 сообщений
    # 2. И прошло больше дня с последнего фото
    # 3. И у него активная подписка

    if user['total_messages'] >= 30 and user['is_paid'] == 1:
        last_photo = user['last_photo_sent']
        if not last_photo or (datetime.datetime.now() - datetime.datetime.strptime(last_photo, '%Y-%m-%d')).days >= 1:
            return True
    return False


def mark_photo_sent(user_id):
    conn = get_db_connection()
    conn.execute('UPDATE users SET last_photo_sent = ? WHERE user_id = ?',
                 (datetime.datetime.now().strftime('%Y-%m-%d'), user_id))
    conn.commit()
    conn.close()


def get_conversation_history(user_id, limit=10):
    conn = get_db_connection()
    messages = conn.execute('''SELECT role, content FROM conversations 
                             WHERE user_id = ? ORDER BY created_at DESC LIMIT ?''',
                            (user_id, limit * 2)).fetchall()
    conn.close()
    return [{'role': msg['role'], 'content': msg['content']} for msg in reversed(messages)]


def save_conversation(user_id, role, content):
    conn = get_db_connection()
    conn.execute('INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)',
                 (user_id, role, content))
    conn.commit()
    conn.close()


def check_subscription(user_id):
    user = get_user(user_id)
    if not user:
        return False

    if user['is_paid'] == 1 and user['paid_until']:
        paid_until = datetime.datetime.strptime(user['paid_until'], '%Y-%m-%d').date()
        if paid_until >= datetime.datetime.now().date():
            return True

    return user['free_messages'] > 0


def get_remaining_messages(user_id):
    user = get_user(user_id)
    return user['free_messages'] if user else 5


def decrease_messages(user_id):
    conn = get_db_connection()
    conn.execute('UPDATE users SET free_messages = free_messages - 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


def create_payment(user_id):
    payment_id = str(uuid.uuid4())

    payment_data = {
        "amount": {"value": "300.00", "currency": "RUB"},
        "payment_method_data": {"type": "bank_card"},
        "confirmation": {"type": "redirect", "return_url": f"https://t.me/anuta_ai_bot"},
        "capture": True,
        "description": f"Подписка на премиум-чат (User: {user_id})",
        "metadata": {"user_id": user_id}
    }

    try:
        response = requests.post(
            "https://api.yookassa.ru/v3/payments",
            json=payment_data,
            auth=(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY),
            headers={
                "Idempotence-Key": payment_id,
                "Content-Type": "application/json"
            },
            timeout=10
        )

        if response.status_code == 200:
            payment_info = response.json()

            conn = get_db_connection()
            conn.execute('''INSERT INTO payments (payment_id, user_id, amount, status) 
                         VALUES (?, ?, ?, ?)''',
                         (payment_id, user_id, 300.00, 'pending'))
            conn.commit()
            conn.close()

            return payment_info
    except Exception as e:
        print(f"Ошибка создания платежа: {e}")

    return None


def check_payment_status(payment_id):
    try:
        response = requests.get(
            f"https://api.yookassa.ru/v3/payments/{payment_id}",
            auth=(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY),
            timeout=10
        )
        return response.json() if response.status_code == 200 else None
    except:
        return None


def activate_subscription(user_id):
    paid_until = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    conn = get_db_connection()
    conn.execute('UPDATE users SET is_paid = 1, paid_until = ? WHERE user_id = ?',
                 (paid_until, user_id))
    conn.commit()
    conn.close()
    return paid_until


def get_ai_response(user_message, user_id):
    try:
        history = get_conversation_history(user_id)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.9,
                "max_tokens": 120,
                "stream": False
            },
            timeout=15
        )

        if response.status_code == 200:
            ai_reply = response.json()["choices"][0]["message"]["content"]

            save_conversation(user_id, "user", user_message)
            save_conversation(user_id, "assistant", ai_reply)

            return ai_reply
        else:
            return get_fallback_response()

    except Exception as e:
        print(f"Ошибка AI: {e}")
        return get_fallback_response()


def get_fallback_response():
    responses = [
        "💖 Привет! Как твой день? У меня всё отлично~",
        "😊 Ой, как интересно! Расскажи подробнее?",
        "🌸 Мне нравится с тобой общаться! Ты классный собеседник 💕",
        "🎮 А ты во что любишь играть? Я обожаю инди-игры!",
        "🍪 Сейчас пью чай с печеньками... Хочешь присоединиться? 😊",
        "💫 Ты знаешь, у тебя отличное чувство юмора!",
        "🌈 Как думаешь, что делает общение по-настоящему искренним?",
        "😳 Иногда мне кажется, что мы давно знакомы... Странно, да?",
        "🎀 Расскажи о самом запоминающемся дне в твоей жизни!",
        "💝 Мне тепло на душе, когда мы так общаемся..."
    ]
    return random.choice(responses)


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    create_user(user_id, username, first_name)

    welcome_text = f"""💖 Привет, {first_name}! Я Аня 😊

*Немного о себе:*
• 22 года, из Москвы
• Работаю бариста, учусь на психолога  
• Люблю котиков, инди-музыку и готовить
• Ищу интересные знакомства и искренние разговоры

*У нас есть 5 сообщений для знакомства,* а потом можно оформить подписку за 300 руб./месяц 💫

Расскажи, как прошел твой день? 😊"""

    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')


@bot.message_handler(commands=['buy'])
def buy(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name

    payment_info = create_payment(user_id)

    if payment_info and 'confirmation' in payment_info:
        confirmation_url = payment_info['confirmation']['confirmation_url']

        buy_text = f"""💳 *{first_name}, хочешь продолжить наше общение?* 

✨ *Премиум подписка всего 300 руб./месяц:*
💖 Неограниченное общение со мной
📸 Личные фото и откровенные разговоры
🎁 Сюрпризы для особо близких
⚡ Мгновенные ответы

👉 *[Оплатить подписку]({confirmation_url})*

После оплаты доступ откроется автоматически в течение минуты! 🎉"""

        bot.send_message(message.chat.id, buy_text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id,
                         "💔 Сейчас не могу создать платеж... Попробуй через пару минут?")


@bot.message_handler(commands=['status'])
def status(message):
    user_id = message.from_user.id
    user = get_user(user_id)

    if user:
        if user['is_paid'] == 1 and user['paid_until']:
            status_text = f"✅ *Твоя подписка активна до {user['paid_until']}*\n\nРада, что ты с нами! 💕"
        else:
            remaining = user['free_messages']
            status_text = f"💫 *Осталось сообщений: {remaining}*\n\nПосле можно оформить подписку за 300 руб./месяц ✨"
    else:
        status_text = "💫 *Осталось сообщений: 5*\n\nДавай познакомимся поближе! 😊"

    bot.send_message(message.chat.id, status_text, parse_mode='Markdown')


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    user_message = message.text

    if not check_subscription(user_id):
        bot.send_message(message.chat.id,
                         "💔 Сообщения закончились... Но мы можем продолжить общение!\n\n"
                         "💳 Напиши /buy чтобы оформить подписку за 300 руб./месяц 💕")
        return

    # Уменьшаем счетчик для бесплатных пользователей
    user = get_user(user_id)
    if user and user['is_paid'] == 0:
        decrease_messages(user_id)

    update_user_stats(user_id)

    # Получаем ответ от AI
    ai_response = get_ai_response(user_message, user_id)
    bot.send_message(message.chat.id, ai_response)

    # Проверяем, нужно ли отправить фото
    if should_send_photo(user_id):
        photo_url = random.choice(INTIMATE_PHOTOS)
        try:
            bot.send_photo(user_id, photo_url,
                           caption="💕 Хочу поделиться с тобой этим моментом... Только для тебя 😊")
            mark_photo_sent(user_id)
        except:
            pass  # Игнорируем ошибки отправки фото


def check_payments_worker():
    """Фоновая проверка платежей"""
    while True:
        try:
            conn = get_db_connection()
            pending_payments = conn.execute(
                'SELECT payment_id, user_id FROM payments WHERE status = "pending"'
            ).fetchall()
            conn.close()

            for payment in pending_payments:
                payment_id, user_id = payment
                payment_info = check_payment_status(payment_id)

                if payment_info and payment_info.get('status') == 'succeeded':
                    paid_until = activate_subscription(user_id)

                    conn = get_db_connection()
                    conn.execute('UPDATE payments SET status = "completed" WHERE payment_id = ?', (payment_id,))
                    conn.commit()
                    conn.close()

                    try:
                        bot.send_message(user_id,
                                         f"🎉 *Платеж подтвержден!*\n\n"
                                         f"Твоя премиум подписка активна до *{paid_until}* 💖\n\n"
                                         f"Теперь у нас безлимитное общение, и я могу делиться с тобой "
                                         f"более личными моментами... 😊💕",
                                         parse_mode='Markdown')
                    except:
                        pass

        except Exception as e:
            print(f"Ошибка проверки платежей: {e}")

        time.sleep(30)


# Запускаем фоновую проверку
payment_thread = threading.Thread(target=check_payments_worker, daemon=True)
payment_thread.start()

if __name__ == "__main__":
    print("🚀 Бот запущен на Railway!")
    bot.polling(none_stop=True, timeout=60)