# Telegram Read-Only AI Assistant

An owner-only Telegram AI assistant with a Telegram Bot API front end and a read-only Telethon back end.

The assistant can reply only to your configured Bot API owner account. Telethon is used only to read selected chats and channels into a local SQLite index; it must not send, delete, forward, edit, react, join, or otherwise mutate Telegram state.

## Features

- Private Telegram Bot API interface restricted by `OWNER_TELEGRAM_USER_ID`.
- Explicit tracked-chat management.
- Read-only Telethon ingestion for selected chats/channels.
- Local SQLite message index with FTS search.
- Gemini-powered Q&A and on-demand digests grounded in indexed Telegram messages.
- No scheduled proactive sends in V1; the bot replies only when you ask.
- Private file permission hardening for `.env`, sessions, and SQLite state.

## Privacy And Security

Tracked Telegram message text, sender names, and chat titles are stored locally in SQLite. Retrieved snippets are sent to the Google Gemini API when you ask questions or generate digests. Only track chats whose contents you are comfortable processing this way.

Keep `.env`, `*.session*`, and `*.db*` files private. They contain credentials, Telegram login state, or indexed chat content.

```bash
chmod 600 .env *.session digest_bot.db* 2>/dev/null || true
```

## Requirements

- Python 3.9 or newer.
- Telegram API ID and API hash from https://my.telegram.org/.
- Telegram Bot API token from BotFather.
- Your numeric Telegram user ID for `OWNER_TELEGRAM_USER_ID`.
- Google Gemini API key.

## Quickstart

Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```bash
cp .env.example .env
```

Fill in:

```text
API_ID=your_api_id
API_HASH=your_api_hash
GEMINI_API_KEY=your_gemini_api_key
BOT_TOKEN=your_bot_api_token
OWNER_TELEGRAM_USER_ID=your_numeric_telegram_user_id
```

Run the assistant:

```bash
source venv/bin/activate
python main.py
```

On first run, Telethon asks for Telegram login details and creates `digest_session.session` locally.

## Telegram Commands

Send commands to your private Bot API chat:

- `/start` or `/help`: show available commands.
- `/track_add <chat_username_or_id>`: add a chat or channel. Tracking starts from the latest visible message at add time.
- `/track_remove <chat_username_or_id>`: remove a tracked chat or channel.
- `/track_list`: list tracked chats.
- `/sync`: read new messages from tracked chats into the local SQLite index.
- `/search <query>`: search locally indexed messages.
- `/ask <question>`: answer from indexed Telegram evidence.
- `/digest [today|since YYYY-MM-DD]`: generate an on-demand digest from indexed messages.

Plain text owner messages are treated like `/ask`.

## Linux Service

After completing first-run Telegram authentication, generate a `systemd` service file:

```bash
./setup_service.sh
```

Then follow the script output to install and start the service.

## Testing

Run the automated tests with:

```bash
venv/bin/python -m unittest discover -s tests
```

## Developer Docs

- [Docs index](docs/index.md)
- [Development guide](docs/development.md)
- [Architecture guide](docs/architecture.md)
- [Operations guide](docs/operations.md)
- [Future-agent notes](docs/agent-notes.md)
