# movie-picker-bot

A Telegram bot that helps a group of friends agree on what to watch. Everyone adds movies to a shared list, and the bot picks one — either randomly or through a veto round where people rule out the ones they don't want to watch.

I built this as a learning project while picking up Python (variables, loops, functions, dicts, then aiogram and SQLite). It's not meant to be a polished product, more a way to practice with something I'd actually use with my own friends.

## How it works

The bot works per chat: if you use it in a group, that group has its own movie list; if you message it privately, that's a separate list. Nothing is shared between chats.

Commands:

- `/add [title]` — add a movie to the list
- `/remove [number]` — remove a movie by its number in `/list`
- `/list` — show the current list
- `/random` — pick a random movie from the list
- `/who` — see who proposed how many movies
- `/veto` — start a veto round: the bot picks up to 5 movies, and each person can rule one out
- `/out [number]` — vote against a movie during a veto round
- `/vetoresult` — see which movie survived the veto round
- `/clear` — wipe the list
- `/help` — list all commands

There's a limit on how many movies one person can add at a time, so the list doesn't get flooded by one enthusiastic friend.

## History

The first version kept the movie list in memory (a plain Python list) — it worked, but everything reset every time the bot restarted. The current version stores movies in SQLite instead, so the list survives restarts, plus it added the `/help` command.

Inline buttons (so you can tap instead of typing a movie number) are next — not built yet.

## Setup

1. Clone the repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Create a bot with [@BotFather](https://t.me/BotFather) and get a token.
3. Create a `.env` file in the project root:
   ```
   BOT_TOKEN=your_token_here
   ```
4. Run it:
   ```bash
   python filmbot.py
   ```

The database file (`bot.db`) is created automatically on first run and isn't tracked in the repo.

## Built with

Python, [aiogram](https://docs.aiogram.dev/) for the Telegram side, SQLite for storage, `python-dotenv` to keep the token out of the code.
