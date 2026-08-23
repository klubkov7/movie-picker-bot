import asyncio
import os
import random
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command, CommandObject

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

movies = []                # список фильмов
user_movie_count = {}      # {user_id: сколько фильмов уже добавил}
user_names = {}            # {user_id: имя пользователя}
MAX_PROPOSALS = 2          # лимит на человека — поменяй на 1, если хочешь строже

veto_round = []            # список фильмов в текущем раунде вето
veto_votes = {}            # {фильм: количество голосов против}
voted_users = set()        # id пользователей, которые уже голосовали в этом раунде


@dp.message(Command("start"))
async def start_handler(message: Message):
    name = message.from_user.first_name
    await message.answer(
        f"🎬 Привет, {name}! Я бот для выбора фильма на выходные.\n\n"
        "Вот что я умею:\n"
        "/add [название] — добавить фильм\n"
        "/remove [номер] — удалить фильм\n"
        "/list — посмотреть весь список\n"
        "/who — кто сколько предложил\n"
        "/random — выбрать один фильм случайно\n"
        "/clear — очистить список\n"
        "/veto — запустить раунд вето\n"
        "/out [номер] — вычеркнуть фильм в раунде вето\n"
        "/vetoresult — узнать победителя вето\n\n"
        "⚠️ Вписывать запрещено:\n"
        "Аниме\n"
        "Сериалы"
    )


@dp.message(Command("add"))
async def add_handler(message: Message, command: CommandObject):
    user_id = message.from_user.id
    movie = command.args
    if movie is None:
        await message.answer("Напиши название после команды, например: /add Побег из Шоушенка")
        return
    if user_movie_count.get(user_id, 0) >= MAX_PROPOSALS:
        await message.answer(f"Ты уже предложил максимум фильмов ({MAX_PROPOSALS})")
        return
    if movie in movies:
        await message.answer("Такой фильм уже есть в списке")
        return
    movies.append(movie)
    user_movie_count[user_id] = user_movie_count.get(user_id, 0) + 1
    user_names[user_id] = message.from_user.first_name
    await message.answer(f"✅ Добавлено: {movie}")


@dp.message(Command("remove"))
async def remove_handler(message: Message, command: CommandObject):
    if command.args is None or not command.args.isdigit():
        await message.answer("Напиши номер фильма из /list, например: /remove 2")
        return
    index = int(command.args) - 1
    if index < 0 or index >= len(movies):
        await message.answer("Такого номера нет в списке")
        return
    removed = movies.pop(index)
    await message.answer(f"🗑 Удалено: {removed}")


@dp.message(Command("list"))
async def list_handler(message: Message):
    if not movies:
        await message.answer("Список пуст, добавь фильмы через /add")
        return
    text = "\n".join(f"{i+1}. {film}" for i, film in enumerate(movies))
    await message.answer(f"Список фильмов:\n{text}")


@dp.message(Command("who"))
async def who_handler(message: Message):
    if not user_movie_count:
        await message.answer("Пока никто ничего не предложил")
        return
    text = "\n".join(
        f"{user_names.get(uid, 'Кто-то')}: {count} фильм(ов)"
        for uid, count in user_movie_count.items()
    )
    await message.answer(f"👥 Статистика:\n{text}")


@dp.message(Command("clear"))
async def clear_handler(message: Message):
    movies.clear()
    user_movie_count.clear()
    user_names.clear()
    await message.answer("🗑 Список очищен")


@dp.message(Command("random"))
async def random_handler(message: Message):
    if not movies:
        await message.answer("Список пуст, сначала добавь фильмы через /add")
        return
    chosen = random.choice(movies)
    await message.answer(f"🎲 Сегодня смотрим: {chosen}")


@dp.message(Command("veto"))
async def veto_handler(message: Message):
    global veto_round, veto_votes, voted_users
    if len(movies) < 2:
        await message.answer("Нужно минимум 2 фильма в списке (добавь через /add)")
        return
    veto_round = random.sample(movies, min(5, len(movies)))
    veto_votes = {film: 0 for film in veto_round}
    voted_users = set()
    text = "\n".join(f"{i+1}. {film}" for i, film in enumerate(veto_round))
    await message.answer(f"🗳 Раунд вето начат! Голосуй через /out [номер]\n\n{text}")


@dp.message(Command("out"))
async def out_handler(message: Message, command: CommandObject):
    user_id = message.from_user.id
    if not veto_round:
        await message.answer("Сначала запусти /veto")
        return
    if user_id in voted_users:
        await message.answer("Ты уже голосовал в этом раунде")
        return
    if command.args is None or not command.args.isdigit():
        await message.answer("Напиши номер фильма, например: /out 2")
        return
    index = int(command.args) - 1
    if index < 0 or index >= len(veto_round):
        await message.answer("Такого номера нет в списке")
        return
    film = veto_round[index]
    veto_votes[film] += 1
    voted_users.add(user_id)
    await message.answer(f"❌ Голос против «{film}» засчитан")


@dp.message(Command("vetoresult"))
async def vetoresult_handler(message: Message):
    if not veto_round:
        await message.answer("Раунд вето ещё не запускался")
        return
    winner = min(veto_votes, key=veto_votes.get)
    await message.answer(f"🏆 Побеждает: {winner} (меньше всего вето)")


async def main():
    await dp.start_polling(bot)


asyncio.run(main())