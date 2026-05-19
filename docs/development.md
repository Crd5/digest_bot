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
