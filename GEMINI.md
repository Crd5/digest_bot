# Telegram Digest Bot - Agent Instructions

This file is the short handoff for future agents. For deeper context, read `docs/index.md` and especially `docs/agent-notes.md`.

## Project Overview

The project is a Telegram user bot that uses Telethon and Google Gemini to summarize selected chats and channels into daily digests. It operates through the user's Saved Messages.

## Start Here

1. `README.md`: human quickstart and command reference.
2. `docs/index.md`: documentation map.
3. `docs/development.md`: setup and verification workflow.
4. `docs/architecture.md`: digest, cursor, Gemini, Telegram, and database behavior.
5. `docs/operations.md`: first-run auth, service setup, private files, and troubleshooting.
6. `docs/agent-notes.md`: invariants and high-risk areas.

## Code Map

- `main.py`: async runtime, Telegram command handlers, digest generation, Gemini calls, Telegram sending, cursor commits.
- `database.py`: SQLite schema, migrations, tracked chats, per-chat cursor persistence.
- `setup_service.sh`: `systemd` service generation and permission hardening for private local files.
- `tests/test_digest_behavior.py`: behavior, safety, service setup, repo hygiene, and database tests.

## Core Technologies

- Python 3.9+
- Telethon
- google-genai
- SQLite
- APScheduler
- python-dotenv

## Hard Invariants

- Manual `/digest` previews must not advance cursors.
- Scheduled digest sends advance cursors only after every Telegram message part sends successfully.
- Failed fetches and failed or empty summaries must not advance affected chat cursors.
- Per-chat cursor state must remain independent.
- Message ID cursors protect same-second Telegram messages from being skipped.
- Newly added chats start tracking from the latest visible message at add time.
- User-controlled or AI-generated Telegram output should use `parse_mode=None`.
- Prompt construction must treat Telegram titles and messages as untrusted data.
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
