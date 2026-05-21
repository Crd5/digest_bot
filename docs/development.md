# Development

This project is a compact Python Telegram assistant. The runtime is composed from small modules instead of a single command-handler file.

## Requirements

- Python 3.9 or newer.
- Telegram API ID and API hash from https://my.telegram.org/.
- Telegram Bot API token from BotFather.
- Numeric Telegram owner user ID.
- Google Gemini API key.
- A local virtual environment named `venv`.

## Local Setup

Create the virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create the local environment file:

```bash
cp .env.example .env
```

Edit `.env` with:

```text
API_ID=your_api_id
API_HASH=your_api_hash
GEMINI_API_KEY=your_gemini_api_key
BOT_TOKEN=your_bot_api_token
OWNER_TELEGRAM_USER_ID=your_numeric_telegram_user_id
```

Keep `.env` private. It is ignored by git.

## Running The Assistant

After configuring `.env`, run:

```bash
source venv/bin/activate
python main.py
```

On first run, Telethon prompts for Telegram login and creates a local `digest_session.session` file. Treat that file like a credential.

## Running Tests

Run the complete test suite with:

```bash
venv/bin/python -m unittest discover -s tests
```

The tests use fakes for Bot API, Telethon, Gemini, and SQLite behavior where possible. They also verify repo hygiene, read-only Telethon safety, and the documented test command.

## Development Workflow

Before changing behavior:

1. Read [Architecture](architecture.md) for the Bot API, Telethon, index, and assistant boundaries.
2. Read [Agent Notes](agent-notes.md) for invariants that future agents must preserve.
3. Add or update tests for behavior changes.
4. Run `venv/bin/python -m unittest discover -s tests`.

For documentation-only changes, still run the test suite because repo hygiene tests inspect `README.md`, `GEMINI.md`, and `.env.example`.

## Code Map

- `main.py`: runtime initialization and service composition.
- `bot_frontend.py`: owner-only Bot API commands and plain-text replies.
- `telegram_gateway.py`: read-only Telethon history access and cursor-safe collection.
- `tracker_service.py`: tracked chat add/remove/list behavior.
- `sync_service.py`: tracked-chat ingestion into SQLite.
- `assistant_service.py`: FTS retrieval, Gemini prompts, search formatting, and digests.
- `ai_model.py`: Gemini SDK adapter.
- `database.py`: SQLite schema, migrations, tracked chats, indexed messages, and FTS.
- `setup_service.sh`: `systemd` unit generation and private-file permission hardening.
- `tests/`: behavior, safety, service setup, repo hygiene, and database migration tests.

## Dependency Notes

Dependencies are pinned in `requirements.txt`:

- `Telethon`: Telegram MTProto user-client library.
- `python-telegram-bot`: Bot API polling and command handling.
- `google-genai`: Gemini SDK.
- `python-dotenv`: `.env` loading.

Avoid adding dependencies for small helpers unless they remove meaningful complexity.

## Private Artifacts

Do not commit or print:

- `.env` or local `.env.*` files.
- `*.session*` Telethon files.
- `digest_bot.db` or SQLite sidecars.
- Generated `*.service` files.
- Logs containing chat content, sender names, credentials, indexed messages, or AI responses.
