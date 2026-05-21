# Operations

This guide covers running the Telegram Read-Only AI Assistant outside the test suite.

## First Run

Create and configure `.env`, then run:

```bash
source venv/bin/activate
python main.py
```

Telethon will ask for the Telegram phone number and login code on first run. Successful authentication creates `digest_session.session` in the project directory.

Run the assistant manually at least once before using the Linux service. The service is non-interactive and cannot complete Telegram login prompts.

## Bot API Owner Setup

Create a bot with BotFather and set `BOT_TOKEN` in `.env`. Set `OWNER_TELEGRAM_USER_ID` to your numeric Telegram user ID.

The Bot API front end rejects all non-owner updates before AI, database, or Telethon work. It does not reply to non-owner users.

## Private Files

Treat these files as private local state:

- `.env` and `.env.*` except `.env.example`
- `*.session*`
- `digest_bot.db`
- `digest_bot.db-journal`
- `digest_bot.db-wal`
- `digest_bot.db-shm`
- Generated `*.service` files
- Logs containing chat content, indexed messages, credentials, or AI responses

The application sets `umask(0o077)` and restricts known private files to mode `600`. You can also run:

```bash
chmod 600 .env *.session digest_bot.db* 2>/dev/null || true
```

## Linux Service Setup

Generate a `systemd` service file:

```bash
./setup_service.sh
```

The script:

- Uses the script directory as the project directory.
- Warns if `.env` or `digest_session.session` is missing.
- Restricts private file permissions before early exits.
- Verifies that `venv/bin/python` exists.
- Writes `tg-digest-bot.service` in the project directory.

Install and start the generated service:

```bash
sudo cp tg-digest-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tg-digest-bot
sudo systemctl start tg-digest-bot
```

Follow logs:

```bash
journalctl -u tg-digest-bot -f
```

## Operating Flow

1. Start the assistant.
2. In your private bot chat, run `/track_add <chat>`.
3. Run `/sync` to ingest new messages into the local index.
4. Use `/search`, `/ask`, natural-language messages, or `/digest`.

There are no scheduled proactive digest sends in V1.

## Backups

To preserve tracked chats, cursors, and indexed messages, back up `digest_bot.db` while the assistant is stopped. If SQLite sidecar files exist, keep them with the database file:

- `digest_bot.db`
- `digest_bot.db-wal`
- `digest_bot.db-shm`
- `digest_bot.db-journal`

Back up `digest_session.session` separately if you want to preserve the Telegram login session.

## Troubleshooting

### Missing Credentials

If startup logs mention missing credentials, check `.env` and confirm it contains `API_ID`, `API_HASH`, `GEMINI_API_KEY`, `BOT_TOKEN`, and `OWNER_TELEGRAM_USER_ID`.

### Invalid Numeric IDs

If startup logs say `API_ID` or `OWNER_TELEGRAM_USER_ID` must be an integer, replace the value with the numeric ID.

### Service Will Not Start

Check:

```bash
journalctl -u tg-digest-bot -n 100 --no-pager
```

Common causes:

- `venv/bin/python` does not exist.
- `.env` is missing or incomplete.
- `digest_session.session` is missing because the assistant was not run manually first.
- `python-telegram-bot` was not installed after updating `requirements.txt`.
- The service was generated from a different project directory than expected.

### No Search Results

The assistant searches only locally indexed messages. Run `/track_add <chat>` and `/sync` before `/search`, `/ask`, or `/digest`.

### Partial Sync Failures

If one chat cannot be fetched, `/sync` may still index successful chats and report a warning. The failed chat cursor should not advance.
