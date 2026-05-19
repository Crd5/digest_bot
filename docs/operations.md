# Operations

This guide covers running the Telegram Digest Bot outside the test suite.

## First Run

Create and configure `.env`, then run:

```bash
source venv/bin/activate
python main.py
```

Telethon will ask for the Telegram phone number and login code on first run. Successful authentication creates `digest_session.session` in the project directory.

Run the bot manually at least once before using the Linux service. The service is non-interactive and cannot complete Telegram login prompts.

## Private Files

Treat these files as private local state:

- `.env` and `.env.*` except `.env.example`
- `*.session*`
- `digest_bot.db`
- `digest_bot.db-journal`
- `digest_bot.db-wal`
- `digest_bot.db-shm`
- Generated `*.service` files
- Logs containing chat content or credentials

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

## Schedule

The scheduled digest runs at `19:00 UTC`, which is `22:00 UTC+3`.

Manual `/digest` commands are previews. They send a digest but do not advance cursors.

## Backups

To preserve tracked chats and cursor state, back up `digest_bot.db` while the bot is stopped. If SQLite sidecar files exist, keep them with the database file:

- `digest_bot.db`
- `digest_bot.db-wal`
- `digest_bot.db-shm`
- `digest_bot.db-journal`

Back up `digest_session.session` separately if you want to preserve the Telegram login session.

## Troubleshooting

### Missing Credentials

If startup logs say `Please set API_ID, API_HASH, and GEMINI_API_KEY`, check `.env` and confirm the process is running from the project directory.

### Invalid API ID

If startup logs say `API_ID must be an integer`, replace the value in `.env` with the numeric Telegram API ID.

### Service Will Not Start

Check:

```bash
journalctl -u tg-digest-bot -n 100 --no-pager
```

Common causes:

- `venv/bin/python` does not exist.
- `.env` is missing or incomplete.
- `digest_session.session` is missing because the bot was not run manually first.
- The service was generated from a different project directory than expected.

### No New Messages

The bot tracks each chat from the latest visible message at the time `/add` is run. It does not backfill older history for newly added chats.

### Partial Chat Failures

If one chat cannot be fetched or summarized, the digest may still include successful chats and a warning. The failed chat cursor should not advance.
