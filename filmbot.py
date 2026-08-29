import asyncio
import os
import random
import sqlite3
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command, CommandObject

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

MAX_PROPOSALS = 2

# --- база данных ---

conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        title TEXT,
        added_by INTEGER,
        added_by_name TEXT
    )
""")
conn.commit()

# --- вето-раунды живут в памяти, отдельно на каждый chat_id ---

veto_rounds = {}     # {chat_id: [список фильмов раунда]}
veto_votes = {}       # {chat_id: {фильм: количество голосов}}
voted_users = {}      # {chat_id: set(user_id, ...)}


def get_movies(chat_id):
    cursor.execute("SELECT title FROM movies WHERE chat_id = ?", (chat_id,))
    return [row[0] for row in cursor.fetchall()]


def count_user_movies(chat_id, user_id):
    cursor.execute(
        "SELECT COUNT(*) FROM movies WHERE chat_id = ? AND added_by = ?",
        (chat_id, user_id),
    )
    return cursor.fetchone()[0]


HELP_TEXT = (
    "📋 Список команд:\n\n"
    "/add [название] — добавить фильм\n"
    "/remove [номер] — удалить фильм\n"
    "/list — посмотреть весь список\n"
    "/who — кто сколько предложил\n"
    "/random — выбрать один фильм случайно\n"
    "/clear — очистить список\n"
    "/veto — запустить раунд вето\n"
    "/out [номер] — вычеркнуть фильм в раунде вето\n"
    "/vetoresult — узнать победителя вето\n\n"
    "⚠️ Вписывать фильмы запрещено:\n"
    "Аниме\n"
    "Сериалы"
)


@dp.message(Command("start"))
async def start_handler(message: Message):
    name = message.from_user.first_name
    await message.answer(
        f"🎬 Привет, {name}! Я бот для выбора фильма на выходные.\n\n"
        "Напиши /help чтобы увидеть все команды."
    )


@dp.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(HELP_TEXT)


@dp.message(Command("add"))
async def add_handler(message: Message, command: CommandObject):
    chat_id = message.chat.id
    user_id = message.from_user.id
    movie = command.args

    if movie is None:
        await message.answer("Напиши название после команды, например: /add Побег из Шоушенка")
        return

    if count_user_movies(chat_id, user_id) >= MAX_PROPOSALS:
        await message.answer(f"Ты уже предложил максимум фильмов ({MAX_PROPOSALS})")
        return

    if movie in get_movies(chat_id):
        await message.answer("Такой фильм уже есть в списке")
        return

    cursor.execute(
        "INSERT INTO movies (chat_id, title, added_by, added_by_name) VALUES (?, ?, ?, ?)",
        (chat_id, movie, user_id, message.from_user.first_name),
    )
    conn.commit()
    await message.answer(f"✅ Добавлено: {movie}")


@dp.message(Command("remove"))
async def remove_handler(message: Message, command: CommandObject):
    chat_id = message.chat.id

    if command.args is None or not command.args.isdigit():
        await message.answer("Напиши номер фильма из /list, например: /remove 2")
        return

    movies = get_movies(chat_id)
    index = int(command.args) - 1

    if index < 0 or index >= len(movies):
        await message.answer("Такого номера нет в списке")
        return

    removed = movies[index]
    cursor.execute(
        "DELETE FROпM movies WHERE chat_id = ? AND title = ?  ",
        (chat_id, removed),
    )
    conn.commit()
    await message.answer(f"🗑 Удалено: {removed}")


@dp.message(Command("list"))
async def list_handler(message: Message):
    chat_id = message.chat.id
    movies = get_movies(chat_id)

    if not movies:
        await message.answer("Список пуст, добавь фильмы через /add")
        return

    text = "\n".join(f"{i+1}. {film}" for i, film in enumerate(movies))
    await message.answer(f"Список фильмов:\n{text}")


@dp.message(Command("who"))
async def who_handler(message: Message):
    chat_id = message.chat.id
    cursor.execute(
        "SELECT added_by_name, COUNT(*) FROM movies WHERE chat_id = ? GROUP BY added_by",
        (chat_id,),
    )
    rows = cursor.fetchall()

    if not rows:
        await message.answer("Пока никто ничего не предложил")
        return

    text = "\n".join(f"{name}: {count} фильм(ов)" for name, count in rows)
    await message.answer(f"👥 Статистика:\n{text}")


@dp.message(Command("clear"))
async def clear_handler(message: Message):
    chat_id = message.chat.id
    cursor.execute("DELETE FROM movies WHERE chat_id = ?", (chat_id,))
    conn.commit()
    await message.answer("🗑 Список очищен")


@dp.message(Command("random"))
async def random_handler(message: Message):
    chat_id = message.chat.id
    movies = get_movies(chat_id)

    if not movies:
        await message.answer("Список пуст, сначала добавь фильмы через /add")
        return

    chosen = random.choice(movies)
    await message.answer(f"🎲 Сегодня смотрим: {chosen}")


@dp.message(Command("veto"))
async def veto_handler(message: Message):
    chat_id = message.chat.id
    movies = get_movies(chat_id)

    if len(movies) < 2:
        await message.answer("Нужно минимум 2 фильма в списке (добавь через /add)")
        return

    round_movies = random.sample(movies, min(5, len(movies)))
    veto_rounds[chat_id] = round_movies
    veto_votes[chat_id] = {film: 0 for film in round_movies}
    voted_users[chat_id] = set()

    text = "\n".join(f"{i+1}. {film}" for i, film in enumerate(round_movies))
    await message.answer(f"🗳 Раунд вето начат! Голосуй через /out [номер]\n\n{text}")


@dp.message(Command("out"))
async def out_handler(message: Message, command: CommandObject):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if chat_id not in veto_rounds:
        await message.answer("Сначала запусти /veto")
        return

    if user_id in voted_users[chat_id]:
        await message.answer("Ты уже голосовал в этом раунде")
        return

    if command.args is None or not command.args.isdigit():
        await message.answer("Напиши номер фильма, например: /out 2")
        return

    round_movies = veto_rounds[chat_id]
    index = int(command.args) - 1

    if index < 0 or index >= len(round_movies):
        await message.answer("Такого номера нет в списке")
        return

    film = round_movies[index]
    veto_votes[chat_id][film] += 1
    voted_users[chat_id].add(user_id)
    await message.answer(f"❌ Голос против «{film}» засчитан")


@dp.message(Command("vetoresult"))
async def vetoresult_handler(message: Message):
    chat_id = message.chat.id

    if chat_id not in veto_rounds:
        await message.answer("Раунд вето ещё не запускался")
        return

    votes = veto_votes[chat_id]
    winner = min(votes, key=votes.get)
    await message.answer(f"🏆 Побеждает: {winner} (меньше всего вето)")


async def main():
    await dp.start_polling(bot)


asyncio.run(main())