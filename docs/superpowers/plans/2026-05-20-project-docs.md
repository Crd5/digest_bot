# Project Docs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dedicated `docs/` hub for developers and future agents, with `README.md` and `GEMINI.md` tightened into concise entry points.

**Architecture:** This is a Markdown-only documentation change. Keep `README.md` as the human quickstart, `GEMINI.md` as the agent quickstart, and place deeper topic docs under `docs/`.

**Tech Stack:** Markdown, Python unittest verification, existing repository files.

---

## File Structure

- Create: `docs/index.md` - docs table of contents and recommended reading order.
- Create: `docs/development.md` - local development setup, test workflow, dependency notes, and contribution hygiene.
- Create: `docs/architecture.md` - runtime architecture, data flow, cursor behavior, persistence, and safety boundaries.
- Create: `docs/operations.md` - first-run authentication, Linux service setup, private files, permissions, scheduling, troubleshooting, and backup notes.
- Create: `docs/agent-notes.md` - future-agent invariants and high-risk areas.
- Modify: `README.md` - concise human-facing overview, setup, usage, privacy note, and docs links.
- Modify: `GEMINI.md` - concise future-agent entry point with project map, invariants, and verification command.

---

### Task 1: Create Docs Index

**Files:**
- Create: `docs/index.md`

- [ ] **Step 1: Verify the docs index is absent before creation**

Run:

```bash
test ! -f docs/index.md
```

Expected: command exits `0`. If it exits `1`, inspect the existing file and merge instead of overwriting user work.

- [ ] **Step 2: Create `docs/index.md`**

Use `apply_patch` to add this complete file:

```markdown
# Telegram Digest Bot Docs

This directory is the deeper project guide for developers and future agents working on the Telegram Digest Bot.

## Start Here

- [Development](development.md): local setup, test commands, and development workflow.
- [Architecture](architecture.md): how the bot collects messages, summarizes them, stores cursors, and sends digests.
- [Operations](operations.md): first-run auth, systemd setup, generated private files, scheduling, and troubleshooting.
- [Agent Notes](agent-notes.md): invariants and guardrails for future coding agents.

## Recommended Reading Order

1. Read the root [README](../README.md) for the user-facing quickstart.
2. Read [Development](development.md) before changing code.
3. Read [Architecture](architecture.md) before changing digest, cursor, Telegram, Gemini, or database behavior.
4. Read [Operations](operations.md) before changing deployment, service, or file-permission behavior.
5. Read [Agent Notes](agent-notes.md) before making automated or agentic changes.

## Generated Local Files

The bot creates private runtime files locally. Do not commit or expose these files:

- `.env` and `.env.*` except `.env.example`
- `*.session*`
- `*.db*`
- `*.sqlite3*`
- `*.service`
- `*.log`

The repository `.gitignore` excludes these artifacts.
```

- [ ] **Step 3: Verify the docs index exists and links to all topic docs**

Run:

```bash
test -f docs/index.md && rg -n "development.md|architecture.md|operations.md|agent-notes.md" docs/index.md
```

Expected: the command exits `0` and prints matches for all four topic docs.

- [ ] **Step 4: Commit**

```bash
git add docs/index.md
git commit -m "docs: add documentation index"
```

---

### Task 2: Create Development Guide

**Files:**
- Create: `docs/development.md`

- [ ] **Step 1: Verify the development guide is absent before creation**

Run:

```bash
test ! -f docs/development.md
```

Expected: command exits `0`. If it exits `1`, inspect the existing file and merge instead of overwriting user work.

- [ ] **Step 2: Create `docs/development.md`**

Use `apply_patch` to add this complete file:

```markdown
# Development

This project is a compact Python Telegram user bot. The runtime code lives mostly in `main.py`; SQLite persistence lives in `database.py`; behavior tests live in `tests/test_digest_behavior.py`.

## Requirements

- Python 3.9 or newer.
- Telegram API ID and API hash from https://my.telegram.org/.
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
```

Keep `.env` private. It is ignored by git.

## Running The Bot

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

The tests use fakes for Telegram, Gemini, and SQLite behavior where possible. They also verify repo hygiene such as ignored private artifacts and the documented test command.

## Development Workflow

Before changing behavior:

1. Read [Architecture](architecture.md) for cursor and digest semantics.
2. Read [Agent Notes](agent-notes.md) for invariants that future agents must preserve.
3. Add or update tests in `tests/test_digest_behavior.py` for behavior changes.
4. Run `venv/bin/python -m unittest discover -s tests`.

For documentation-only changes, still run the test suite because repo hygiene tests inspect `README.md` and `GEMINI.md`.

## Code Map

- `main.py`: initializes runtime clients, registers Telegram command handlers, schedules daily digests, collects messages, calls Gemini, sends digest output, and advances cursors.
- `database.py`: owns SQLite schema creation, migration from older global cursor state, target chat CRUD, and per-chat cursor updates.
- `setup_service.sh`: generates a `systemd` unit and restricts local private file permissions before service setup.
- `tests/test_digest_behavior.py`: tests digest flow, cursor semantics, prompt safety, Telegram output safety, command cleanup, service generation, repo hygiene, and database migrations.

## Dependency Notes

Dependencies are pinned in `requirements.txt`:

- `Telethon`: Telegram MTProto user-client library.
- `google-genai`: Gemini SDK.
- `APScheduler`: async daily scheduling.
- `python-dotenv`: `.env` loading.

Avoid adding dependencies for small helpers unless they remove meaningful complexity.

## Private Artifacts

Do not commit or print:

- `.env` or local `.env.*` files.
- `*.session*` Telethon files.
- `digest_bot.db` or SQLite sidecars.
- Generated `*.service` files.
- Logs containing chat content, sender names, credentials, or summaries.
```

- [ ] **Step 3: Verify setup and test commands are documented**

Run:

```bash
rg -n "python3 -m venv venv|pip install -r requirements.txt|venv/bin/python -m unittest discover -s tests" docs/development.md
```

Expected: command exits `0` and prints all three command references.

- [ ] **Step 4: Commit**

```bash
git add docs/development.md
git commit -m "docs: add development guide"
```

---

### Task 3: Create Architecture Guide

**Files:**
- Create: `docs/architecture.md`

- [ ] **Step 1: Verify the architecture guide is absent before creation**

Run:

```bash
test ! -f docs/architecture.md
```

Expected: command exits `0`. If it exits `1`, inspect the existing file and merge instead of overwriting user work.

- [ ] **Step 2: Create `docs/architecture.md`**

Use `apply_patch` to add this complete file:

```markdown
# Architecture

The Telegram Digest Bot is a Telegram user bot that reads selected chats and channels, summarizes new messages with Gemini, and sends a digest to the user's Saved Messages.

## Runtime Components

- `main.py` owns the runtime. It loads environment variables, initializes Telethon and Gemini clients, registers command handlers, schedules the daily digest, collects messages, summarizes content, and sends output.
- `database.py` owns local SQLite persistence. It stores target chats and per-chat cursor state.
- `setup_service.sh` generates a Linux `systemd` service file for long-running deployments.
- `tests/test_digest_behavior.py` captures the expected digest, cursor, safety, service, and database behavior.

## Startup Flow

`main()` calls `initialize_runtime()`, which:

1. Sets `umask(0o077)` so newly created local files default to private permissions.
2. Loads `.env`.
3. Restricts existing private file permissions.
4. Reads `API_ID`, `API_HASH`, and `GEMINI_API_KEY`.
5. Validates that `API_ID` is an integer.
6. Creates the Telethon `TelegramClient`.
7. Creates the Gemini client.
8. Initializes the SQLite database.
9. Restricts private file permissions again.

After startup, `main()` starts the Telegram client, registers command handlers, schedules the daily digest, and waits until disconnected.

## Telegram Commands

Commands are handled in Saved Messages (`chats='me'`):

- `/add <chat>` resolves a username or numeric ID, records the marked Telegram peer ID, and starts tracking from the latest message visible at add time.
- `/remove <chat>` resolves a chat or numeric ID and removes it from tracking.
- `/list` lists tracked chats.
- `/digest` sends a manual preview digest without advancing cursors.

Command status messages are cleaned up after short delays to keep Saved Messages tidy.

## Digest Flow

Scheduled and manual digests share the same core path:

1. `build_digest_result()` loads target chats from SQLite.
2. It captures a run-start timestamp.
3. It collects messages for each chat with `collect_chat_messages()`.
4. It formats text entries as `[timestamp] sender: text`.
5. It splits large chat inputs with `split_text_entries()`.
6. It summarizes chunks through Gemini with a concurrency limit.
7. It renders a single digest text with warnings for fetch failures.
8. `send_digest()` splits long Telegram output into safe message parts and sends each part with `parse_mode=None`.
9. Scheduled sends commit cursor updates only after all message parts send successfully.

## Cursor Semantics

Cursor state is stored per chat:

- `last_digest_timestamp`
- `last_digest_message_id`

The message ID cursor prevents missing messages that share the same timestamp second. Timestamp-only legacy cursors still include same-second messages so they can be upgraded safely.

Important rules:

- Manual `/digest` previews do not advance cursors.
- Scheduled digest sends advance cursors only after every Telegram message part is sent successfully.
- Fetch failures do not advance the failed chat.
- Summary failures do not advance the affected chat.
- Cursors are independent per chat; one failing chat must not block cursor updates for successful chats.
- Messages newer than the run-start snapshot are excluded so in-flight messages are not partially digested.

## Gemini Summarization

`build_summary_prompt()` wraps chat title and message text in a JSON payload and explicitly tells Gemini to treat those values as untrusted data. This protects against prompt injection from Telegram message content.

`generate_digest_summary()` calls Gemini and rejects empty summaries. `summarize_chat()` converts API failures into per-chat error text and marks the summary as failed so the chat cursor is not advanced.

## Telegram Output Safety

Digest and command output should be sent with `parse_mode=None` when it can include user-controlled or AI-generated text. This prevents Telegram Markdown parsing from turning arbitrary text into spoofed links, mentions, or formatting.

Long outgoing messages are split with `split_telegram_message()` to stay below Telegram's message length limit.

## Persistence

`database.init_db()` creates and migrates:

- `target_chats`: target chat ID, title, timestamp cursor, and message ID cursor.
- `state`: legacy global cursor state used only for migration from older databases.

When adding a chat, `add_target_chat()` updates the title for existing chats without resetting existing cursor state. New chats start from the latest visible message at add time.

## Scheduling

`APScheduler` runs `send_digest()` at `19:00 UTC`, which corresponds to `22:00 UTC+3`.
```

- [ ] **Step 3: Verify high-risk architecture terms are documented**

Run:

```bash
rg -n 'Manual `/digest`|parse_mode=None|prompt injection|last_digest_message_id|19:00 UTC' docs/architecture.md
```

Expected: command exits `0` and prints matches for all listed concepts.

- [ ] **Step 4: Commit**

```bash
git add docs/architecture.md
git commit -m "docs: add architecture guide"
```

---

### Task 4: Create Operations Guide

**Files:**
- Create: `docs/operations.md`

- [ ] **Step 1: Verify the operations guide is absent before creation**

Run:

```bash
test ! -f docs/operations.md
```

Expected: command exits `0`. If it exits `1`, inspect the existing file and merge instead of overwriting user work.

- [ ] **Step 2: Create `docs/operations.md`**

Use `apply_patch` to add this complete file:

```markdown
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
```

- [ ] **Step 3: Verify operational commands are documented**

Run:

```bash
rg -n "./setup_service.sh|systemctl start tg-digest-bot|journalctl -u tg-digest-bot|chmod 600" docs/operations.md
```

Expected: command exits `0` and prints all command references.

- [ ] **Step 4: Commit**

```bash
git add docs/operations.md
git commit -m "docs: add operations guide"
```

---

### Task 5: Create Future-Agent Notes

**Files:**
- Create: `docs/agent-notes.md`

- [ ] **Step 1: Verify the agent notes file is absent before creation**

Run:

```bash
test ! -f docs/agent-notes.md
```

Expected: command exits `0`. If it exits `1`, inspect the existing file and merge instead of overwriting user work.

- [ ] **Step 2: Create `docs/agent-notes.md`**

Use `apply_patch` to add this complete file:

```markdown
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
```

- [ ] **Step 3: Verify agent invariants are documented**

Run:

```bash
rg -n 'Manual `/digest`|parse_mode=None|Prompt construction|venv/bin/python -m unittest discover -s tests|Private files' docs/agent-notes.md
```

Expected: command exits `0` and prints all invariant references.

- [ ] **Step 4: Commit**

```bash
git add docs/agent-notes.md
git commit -m "docs: add future-agent notes"
```

---

### Task 6: Tighten README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Confirm README currently contains the test command required by repo hygiene tests**

Run:

```bash
rg -n "venv/bin/python -m unittest discover -s tests" README.md
```

Expected: command exits `0`.

- [ ] **Step 2: Replace `README.md` with the tightened human entry point**

Use `apply_patch` to replace the complete file with:

```markdown
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
```

- [ ] **Step 3: Verify README keeps required links and test command**

Run:

```bash
rg -n "docs/index.md|docs/development.md|docs/architecture.md|docs/operations.md|docs/agent-notes.md|venv/bin/python -m unittest discover -s tests" README.md
```

Expected: command exits `0` and prints all links plus the test command.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: tighten README entry point"
```

---

### Task 7: Tighten GEMINI Agent Entry Point

**Files:**
- Modify: `GEMINI.md`

- [ ] **Step 1: Confirm GEMINI currently contains the test command required by repo hygiene tests**

Run:

```bash
rg -n "venv/bin/python -m unittest discover -s tests" GEMINI.md
```

Expected: command exits `0`.

- [ ] **Step 2: Replace `GEMINI.md` with the tightened future-agent entry point**

Use `apply_patch` to replace the complete file with:

```markdown
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
```

- [ ] **Step 3: Verify GEMINI keeps required docs links, invariants, and test command**

Run:

```bash
rg -n 'docs/agent-notes.md|Manual `/digest`|parse_mode=None|venv/bin/python -m unittest discover -s tests' GEMINI.md
```

Expected: command exits `0` and prints all references.

- [ ] **Step 4: Commit**

```bash
git add GEMINI.md
git commit -m "docs: tighten agent entry point"
```

---

### Task 8: Full Documentation Verification

**Files:**
- Verify: `README.md`
- Verify: `GEMINI.md`
- Verify: `docs/index.md`
- Verify: `docs/development.md`
- Verify: `docs/architecture.md`
- Verify: `docs/operations.md`
- Verify: `docs/agent-notes.md`

- [ ] **Step 1: Verify all planned docs exist**

Run:

```bash
for file in README.md GEMINI.md docs/index.md docs/development.md docs/architecture.md docs/operations.md docs/agent-notes.md; do test -f "$file" || exit 1; done
```

Expected: command exits `0`.

- [ ] **Step 2: Verify docs cross-links are present**

Run:

```bash
rg -n "docs/index.md|development.md|architecture.md|operations.md|agent-notes.md" README.md GEMINI.md docs/index.md
```

Expected: command exits `0` and prints links from the entry points and docs index.

- [ ] **Step 3: Verify required safety and cursor content is documented**

Run:

```bash
rg -n 'Manual `/digest`|parse_mode=None|prompt injection|last_digest_message_id|Private files|scheduled digest' docs README.md GEMINI.md
```

Expected: command exits `0` and prints matches across the docs.

- [ ] **Step 4: Run the existing test suite**

Run:

```bash
venv/bin/python -m unittest discover -s tests
```

Expected: all tests pass.

- [ ] **Step 5: Inspect git status**

Run:

```bash
git status --short
```

Expected: clean working tree if each task was committed. If docs changes remain unstaged, inspect and commit them with:

```bash
git add README.md GEMINI.md docs/index.md docs/development.md docs/architecture.md docs/operations.md docs/agent-notes.md
git commit -m "docs: add developer and agent documentation"
```
