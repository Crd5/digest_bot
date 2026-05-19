# Telegram Digest Bot

A Telegram user bot that summarizes selected chats and channels into daily highlights using Telethon and Google Gemini.

The bot runs from your Telegram account, listens for commands in Saved Messages, and sends digest output back to Saved Messages.

## Features

- Daily scheduled digest at `22:00 UTC+3`.
- Manual `/digest` preview on demand.
- Dynamic tracked-chat management from Telegram.
- Per-chat cursors so one failing chat does not corrupt the others.
- Plain-text Telegram output for safer handling of AI-generated and user-controlled content.
- Local SQLite state with private file permission hardening.

## Privacy And Security

Tracked Telegram message text, sender names, and chat titles are sent to the Google Gemini API for summarization. Only add chats whose contents you are comfortable processing with an external AI service.

Keep `.env`, `*.session*`, and `*.db*` files private. They contain credentials, Telegram login state, or local chat tracking state.

```bash
chmod 600 .env *.session digest_bot.db* 2>/dev/null || true
```

## Requirements

- Python 3.9 or newer.
- Telegram API ID and API hash from https://my.telegram.org/.
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
```

Run the bot:

```bash
source venv/bin/activate
python main.py
```

On first run, Telethon asks for Telegram login details and creates `digest_session.session` locally.

## Telegram Commands

Send commands to your Saved Messages:

- `/add <chat_username_or_id>`: add a chat or channel. Tracking starts from the latest visible message at add time; older history is not backfilled.
- `/remove <chat_username_or_id>`: remove a tracked chat or channel.
- `/list`: list tracked chats.
- `/digest`: preview a digest without advancing scheduled digest cursors.

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
