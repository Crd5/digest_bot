# Agent Notes

This file is for future coding agents. Read it before changing this repository.

## First Files To Read

1. `README.md`
2. `docs/index.md`
3. `docs/development.md`
4. `docs/architecture.md`
5. `docs/operations.md`
6. `GEMINI.md`

## Repository Map

- `main.py`: async runtime composition.
- `bot_frontend.py`: owner-only Bot API front end.
- `telegram_gateway.py`: read-only Telethon gateway.
- `tracker_service.py`: tracked chat management.
- `sync_service.py`: ingestion into the local index.
- `assistant_service.py`: retrieval, prompt construction, Q&A, search, and digests.
- `ai_model.py`: Gemini adapter.
- `database.py`: SQLite schema, migrations, tracked chats, cursors, indexed messages, and FTS.
- `setup_service.sh`: service file generation and local private-file permission hardening.
- `tests/`: behavior, safety, service, hygiene, and database tests.
- `.env.example`: safe environment template.

## Hard Invariants

Preserve these unless the user explicitly asks for a behavior change and tests are updated with care:

- Bot API replies are allowed only to `OWNER_TELEGRAM_USER_ID`.
- Non-owner updates must be rejected before AI calls, database mutations, or Telethon reads.
- Telethon must stay read-only. Do not add sends, deletes, forwards, edits, reactions, joins, or file sends.
- Only explicitly tracked chats are indexed.
- `/sync` advances each chat cursor only after that chat has been successfully read and indexed.
- Failed fetches must not advance affected chat cursors.
- Per-chat cursors must remain independent.
- Message ID cursors must protect same-second Telegram messages from being skipped.
- Newly added chats start tracking from the latest visible message at add time.
- Bot API replies should use `parse_mode=None`.
- Prompt construction must treat Telegram titles, sender names, message text, and questions as untrusted data.
- No scheduled proactive digest sends in V1.
- Private files must stay ignored and restricted: `.env*`, `*.session*`, `*.db*`, SQLite sidecars, logs, and generated service files.

## Verification Command

Run the full suite after behavior or docs-entrypoint changes:

```bash
venv/bin/python -m unittest discover -s tests
```

The repo hygiene tests expect this exact command to remain documented in `README.md` and `GEMINI.md`.

## Common Safe Change Pattern

1. Read the relevant docs.
2. Add or update tests for behavior changes.
3. Make the smallest code change that satisfies the tests.
4. Run `venv/bin/python -m unittest discover -s tests`.
5. Keep generated runtime files out of commits.

## High-Risk Areas

- Authorization in `bot_frontend.py`.
- Telethon read-only boundaries in `telegram_gateway.py` and `main.py`.
- Cursor changes in `telegram_gateway.py`, `sync_service.py`, and `database.py`.
- Prompt changes in `assistant_service.py`.
- Telegram output changes that could enable Markdown parsing.
- Database schema changes in `database.init_db()`.
- Service setup changes that affect quoting, working directory, or private file permissions.

## Generated Files To Ignore

Do not inspect, print, commit, or summarize private local runtime artifacts unless the user explicitly asks and the content is safe to handle:

- `.env`
- `.env.local`
- `digest_session.session`
- Other `*.session*` files
- `digest_bot.db`
- SQLite sidecars
- `tg-digest-bot.service`
- Log files
