# Telegram Read-Only AI Assistant - Agent Instructions

This file is the short handoff for future agents. For deeper context, read `docs/index.md` and especially `docs/agent-notes.md`.

## Project Overview

The project is an owner-only Telegram AI assistant. Telegram Bot API is the private front end for replies to the configured owner. Telethon is the read-only back end for resolving and ingesting selected chats into a local SQLite index.

## Start Here

1. `README.md`: human quickstart and command reference.
2. `docs/index.md`: documentation map.
3. `docs/development.md`: setup and verification workflow.
4. `docs/architecture.md`: runtime, Bot API, Telethon gateway, index, and assistant behavior.
5. `docs/operations.md`: first-run auth, service setup, private files, and troubleshooting.
6. `docs/agent-notes.md`: invariants and high-risk areas.

## Code Map

- `main.py`: async runtime composition for Telethon, Bot API handlers, services, and Gemini.
- `bot_frontend.py`: owner-only Bot API command handlers and plain-text replies.
- `telegram_gateway.py`: read-only Telethon gateway and message collection cursor logic.
- `sync_service.py`: tracked-chat ingestion into SQLite.
- `assistant_service.py`: FTS retrieval, answer prompts, search formatting, and on-demand digests.
- `ai_model.py`: Gemini provider adapter.
- `tracker_service.py`: tracked chat add/remove/list behavior.
- `database.py`: SQLite schema, migrations, tracked chats, message index, and FTS search.
- `setup_service.sh`: `systemd` service generation and permission hardening.
- `tests/`: behavior, safety, service, hygiene, and database tests.

## Core Technologies

- Python 3.9+
- Telethon
- python-telegram-bot
- google-genai
- SQLite FTS5
- python-dotenv

## Hard Invariants

- Bot API replies are allowed only to `OWNER_TELEGRAM_USER_ID`.
- Non-owner updates must be rejected before AI calls, database mutations, or Telethon reads.
- Telethon must remain read-only: no sends, deletes, forwards, edits, reactions, joins, or file sends.
- The assistant indexes only explicitly tracked chats.
- `/sync` advances each chat cursor only after successful read/index processing for that chat.
- Failed fetches must not advance affected chat cursors.
- Message ID cursors must protect same-second Telegram messages from being skipped.
- Newly added chats start tracking from the latest visible message at add time.
- AI prompts must treat Telegram chat titles, sender names, message text, and questions as untrusted data.
- Bot API replies should use plain text with `parse_mode=None`.
- No scheduled proactive digest sends in V1.
- `.env`, `*.session*`, `*.db*`, SQLite sidecars, logs, and generated service files are private local artifacts.

## Build And Run

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

`python main.py` requires valid `.env` credentials. The first run creates a Telethon session file after interactive Telegram login.

## Test

Run the full suite with:

```bash
venv/bin/python -m unittest discover -s tests
```

Run this after behavior changes and after edits to `README.md` or `GEMINI.md`, because repo hygiene tests inspect those files.
