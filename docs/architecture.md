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
