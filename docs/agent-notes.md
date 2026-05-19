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

- `main.py`: async runtime, command handlers, digest generation, Gemini calls, Telegram output, cursor commits.
- `database.py`: SQLite schema, migrations, tracked chats, per-chat cursor persistence.
- `setup_service.sh`: service file generation and local private-file permission hardening.
- `tests/test_digest_behavior.py`: behavior, safety, service, hygiene, and database tests.
- `.env.example`: safe environment template.

## Hard Invariants

Preserve these unless the user explicitly asks for a behavior change and tests are updated with care:

- Manual `/digest` must not advance cursors.
- Scheduled digest sends advance cursors only after every Telegram message part sends successfully.
- A failed fetch must not advance that chat's cursor.
- A failed or empty Gemini summary must not advance that chat's cursor.
- Per-chat cursors must remain independent.
- Message ID cursors must protect same-second Telegram messages from being skipped.
- Newly added chats start tracking from the latest visible message at add time.
- User-controlled and AI-generated Telegram output should use `parse_mode=None`.
- Prompt construction must continue treating Telegram chat titles and message text as untrusted data.
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

- Cursor changes in `collect_chat_messages()`, `compute_cursor_update()`, `build_digest_result()`, `send_digest()`, and `commit_cursor_updates()`.
- Prompt changes in `build_summary_prompt()` and `generate_digest_summary()`.
- Telegram output changes that could re-enable Markdown parsing.
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
