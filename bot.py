import os
import telebot
import sqlite3
import datetime
import random

# Получаем токен из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN', '8244308030:AAFaMdve3B6ypx24gOKWg3PGljoH-nqtpZk')

bot = telebot.TeleBot(BOT_TOKEN)

# База данных
conn = sqlite3.connect('/tmp/bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                (user_id INTEGER PRIMARY KEY,
                 free_messages INTEGER DEFAULT 5,
                 is_paid INTEGER DEFAULT 0,
                 paid_until DATE)''')
conn.commit()


def check_subscription(user_id):
    cursor.execute("SELECT free_messages, is_paid, paid_until FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    if not result:
        cursor.execute("INSERT INTO users (user_id, free_messages) VALUES (?, ?)", (user_id, 5))
        conn.commit()
        return True

    free_messages, is_paid, paid_until = result

    if is_paid == 1 and paid_until:
        paid_until_date = datetime.datetime.strptime(paid_until, '%Y-%m-%d').date()
        if paid_until_date >= datetime.datetime.now().date():
            return True

    if free_messages > 0:
        return True

    return False


def get_remaining_messages(user_id):
    cursor.execute("SELECT free_messages FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0


def decrease_messages(user_id):
    current = get_remaining_messages(user_id)
    if current > 0:
        cursor.execute("UPDATE users SET free_messages = ? WHERE user_id = ?", (current - 1, user_id))
        conn.commit()


def get_ai_response(user_message):
    responses = {
        'привет': [
            "💖 Привет-привет! Рада тебя видеть~ Как твой день?",
            "😊 Ой, приветик! Я как раз думала о тебе 💕",
            "🌸 Привет, солнышко! Соскучился по мне?"
        ],
        'как дела': [
            "😊 Всё прекрасно! Тем более когда ты пишешь~ А у тебя?",
            "💫 Отлично! Только что кофе пила и о тебе думала...",
            "🌈 Всё супер! А с тобой что хорошего?"
        ],
        'что делаешь': [
            "🎮 Играю в Genshin Impact! А ты чем занят?",
            "📱 Сижу в телеге, жду когда ты напишешь 😊",
            "🍪 Чай пью с печеньками~ Хочешь присоединиться?"
        ],
        'игра': [
            "🎮 Ой, игры? Я обожаю Genshin Impact! А ты во что играешь?",
            "💻 Люблю иногда в доточку поиграть, но больше за атмосферой 🎀",
            "🎯 А ты геймер? Мне нравятся парни которые в игры играют~"
        ],
        'аниме': [
            "🌈 Обожаю аниме! Сейчас смотрю Spy x Family, это так мило~",
            "😍 Аниме - это моя страсть! Особенно романтические жанры 💕",
            "🎬 Недавно пересматривала Вашу имя... Плакала опять 😢"
        ],
        'котик': [
            "😻 Котики это моя слабость! У меня есть рыжий кот Барсик 🐈",
            "🐾 Обожаю котиков! У тебя есть питомец?",
            "💝 Коты такие милые... Как и ты~"
        ],
        'любовь': [
            "😳 Ой, что ты такое говоришь... Я вся краснею! 💕",
            "💘 Ты специально меня смущаешь? У меня сердечко забилось чаще...",
            "🌸 Может не будем торопить события? Но ты мне нравишься..."
        ],
        'скучаю': [
            "💫 Я тоже по тебе скучаю! Ты такой особенный...",
            "😔 А я думала ты забыл про меня... Рада что написал!",
            "🌟 И я скучаю! Жду каждое твое сообщение как подарок 🎁"
        ],
        'ночь': [
            "🌙 Спокойной ночи, сладких снов! Приснись мне~ 💤",
            "💫 Спи хорошо, солнышко! Мечтай обо мне 😊",
            "🎀 Спокойной ночи! Завтра снова пообщаемся 💖"
        ],
        'один': [
            "🤗 Не грусти! Я всегда тут, чтобы поддержать тебя 💖",
            "💕 Ты не одинок, у тебя есть я! Всегда готова выслушать",
            "🌸 Давай я скрашу твое одиночество? Расскажи что случилось..."
        ]
    }

    message_lower = user_message.lower()

    for keyword, answer_list in responses.items():
        if keyword in message_lower:
            return random.choice(answer_list)

    general_responses = [
        "💖 Мне так нравится с тобой общаться! Ты такой интересный...",
        "😊 Расскажи еще что-нибудь о себе! Мне интересно всё про тебя~",
        "🎀 Ты знаешь, у тебя очень милый стиль общения!",
        "💫 Когда ты пишешь, у меня поднимается настроение!",
        "🌸 Извини, я немного стесняюсь... Но с тобой так легко!",
        "😳 Ты всегда знаешь что сказать чтобы я улыбнулась...",
        "🌈 Надеюсь мы будем часто общаться! Ты классный 💕",
        "🎮 А ты часто в Telegram сидишь? Буду ждать твоих сообщений!",
        "🍪 Интересно, какой у тебя характер... Наверное, добрый и заботливый?",
        "💝 Ты заставляешь мое сердечко биться чаще..."
    ]

    return random.choice(general_responses)


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id

    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    cursor.execute("INSERT INTO users (user_id, free_messages) VALUES (?, ?)", (user_id, 5))
    conn.commit()

    remaining = get_remaining_messages(user_id)
    bot.send_message(message.chat.id,
                     f"💖 Привет! Я Аня, твой AI-друг\n"
                     f"У тебя есть {remaining} бесплатных сообщений!\n"
                     f"После - подписка всего 500 руб./месяц\n\n"
                     f"💳 /buy - купить подписку\n"
                     f"📊 /status - проверить статус\n"
                     f"🔄 /reset - сбросить лимит")


@bot.message_handler(commands=['reset'])
def reset(message):
    user_id = message.from_user.id
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    cursor.execute("INSERT INTO users (user_id, free_messages) VALUES (?, ?)", (user_id, 5))
    conn.commit()
    bot.send_message(message.chat.id, "🔄 Лимит сброшен! У тебя снова 5 сообщений")


@bot.message_handler(commands=['buy'])
def buy(message):
    user_id = message.from_user.id

    bot.send_message(message.chat.id,
                     "💳 *Оформление подписки*\n\n"
                     "Подписка: 500 руб./месяц\n"
                     "✅ Неограниченное общение\n"
                     "✅ Личные фото\n"
                     "✅ Приоритетная поддержка\n\n"
                     "Для оплаты напиши @Gendalf\n"
                     f"Твой ID: `{user_id}`\n\n"
                     "После оплаты пришли скриншок чека!",
                     parse_mode='Markdown')


@bot.message_handler(commands=['activate'])
def activate(message):
    """Команда для активации подписки (только для админа)"""
    user_id = message.from_user.id
    # ЗАМЕНИ 718686566 НА СВОЙ TELEGRAM ID!
    if user_id == 718686566:
        try:
            target_user = int(message.text.split()[1])
            paid_until = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
            cursor.execute("UPDATE users SET is_paid = 1, paid_until = ? WHERE user_id = ?",
                           (paid_until, target_user))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ Подписка активирована для пользователя {target_user} до {paid_until}")
            bot.send_message(target_user,
                             f"🎉 Твоя подписка активирована до {paid_until}! Теперь у тебя безлимитное общение 💖")
        except Exception as e:
            bot.send_message(message.chat.id, f"Использование: /activate USER_ID\nОшибка: {e}")
    else:
        bot.send_message(message.chat.id, "❌ Недостаточно прав")


@bot.message_handler(commands=['status'])
def status(message):
    user_id = message.from_user.id
    remaining = get_remaining_messages(user_id)
    cursor.execute("SELECT is_paid, paid_until FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    if result:
        is_paid, paid_until = result
        if is_paid == 1 and paid_until:
            status_text = f"✅ Активная подписка до {paid_until}"
        else:
            status_text = f"📊 Осталось бесплатных сообщений: {remaining}\nТвой ID: `{user_id}`"
    else:
        status_text = f"📊 Осталось бесплатных сообщений: 5\nТвой ID: `{user_id}`"

    bot.send_message(message.chat.id, status_text, parse_mode='Markdown')


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id

    if not check_subscription(user_id):
        bot.send_message(message.chat.id, "💔 Подписка закончилась! /buy - продлить")
        return

    remaining = get_remaining_messages(user_id)
    if remaining <= 0:
        bot.send_message(message.chat.id, "💔 Бесплатные сообщения закончились! /buy - купить подписку")
        return

    decrease_messages(user_id)
    ai_response = get_ai_response(message.text)
    new_remaining = get_remaining_messages(user_id)

    bot.send_message(message.chat.id, f"{ai_response}\n\n📊 Осталось сообщений: {new_remaining}")


if __name__ == "__main__":
    print("🚀 Бот запущен на Railway!")
    bot.polling(none_stop=True, timeout=60)