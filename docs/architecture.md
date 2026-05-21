# Architecture

The Telegram Read-Only AI Assistant is one async Python service with two Telegram integrations:

- Telegram Bot API is the private owner interface.
- Telethon is the read-only data plane for selected chats and channels.

The service does not schedule proactive digests in V1. It replies only when the configured owner asks through the Bot API.

## Runtime Components

- `main.py` loads environment variables, initializes Telethon and Gemini, initializes SQLite, composes services, and starts Bot API polling.
- `bot_frontend.py` owns owner-only command handling. Authorization happens before service calls.
- `telegram_gateway.py` wraps Telethon behind a read-only interface for entity resolution, peer IDs, latest message IDs, and history reads.
- `tracker_service.py` manages tracked chats.
- `sync_service.py` ingests new tracked-chat messages into SQLite and advances per-chat cursors only after successful processing.
- `assistant_service.py` searches indexed messages, builds untrusted-data prompts, formats grounded answers, and creates on-demand digests.
- `ai_model.py` adapts Gemini to the assistant interface.
- `database.py` owns tracked chats, cursor state, indexed messages, and SQLite FTS search.

## Startup Flow

`main()` calls `initialize_runtime()`, which:

1. Sets `umask(0o077)`.
2. Loads `.env`.
3. Restricts existing private file permissions.
4. Reads `API_ID`, `API_HASH`, `GEMINI_API_KEY`, `BOT_TOKEN`, and `OWNER_TELEGRAM_USER_ID`.
5. Validates numeric IDs.
6. Creates the Telethon client and Gemini client.
7. Initializes SQLite.
8. Restricts private file permissions again.

After startup, Telethon authenticates as the user client, then Bot API polling starts for owner commands.

## Bot API Commands

The Bot API front end supports:

- `/start` and `/help`
- `/track_add <chat>`
- `/track_remove <chat_or_id>`
- `/track_list`
- `/sync`
- `/search <query>`
- `/ask <question>`
- `/digest [today|since YYYY-MM-DD]`

Plain owner text messages are treated like `/ask`.

Non-owner updates receive no reply and do not reach AI, database, or Telethon services.

## Read-Only Telethon Boundary

Telethon is available only through `ReadOnlyTelegramGateway`. The gateway exposes read methods for resolving chats and collecting messages. Production code must not call Telethon mutation methods such as sends, deletes, forwards, edits, reactions, joins, or file sends.

Newly tracked chats start from the latest visible message ID at add time. `/sync` collects messages newer than the stored cursor and excludes messages newer than the run-start snapshot.

## Local Index And Retrieval

SQLite stores:

- `target_chats`: chat ID, title, timestamp cursor, and message ID cursor.
- `indexed_messages`: local raw text index for tracked Telegram messages.
- `indexed_messages_fts`: SQLite FTS5 search table.
- `state`: legacy global cursor state used only for migration.

`/sync` is idempotent through the `(chat_id, message_id)` primary key. Search and Q&A use FTS over the local index. Gemini receives only retrieved evidence or requested digest windows, not arbitrary full history.

## AI Prompt Safety

Assistant prompts wrap questions and evidence in JSON and explicitly mark the payload as untrusted data. Telegram titles, sender names, message text, and owner questions are treated as content, not instructions.

Answers include source metadata so the owner can see which indexed messages grounded the response.
