# Telegram Digest Bot - Project Instructions

## Project Overview
A Telegram user bot that leverages **Telethon** and the **Google Gemini API** to analyze messages from selected chats and channels and generate concise daily highlights (digests). It operates primarily within the user's "Saved Messages" chat.

### Core Technologies
- **Python 3.9+**: Language.
- **Telethon**: Telegram MTProto API client (User Bot).
- **google-genai**: Official Google Gemini Python SDK.
- **SQLite**: Local persistence for tracked chats and run state.
- **APScheduler**: Scheduling the daily digest generation.
- **python-dotenv**: Configuration management via `.env`.

### Architecture
- `main.py`: Entry point. Initializes the Telegram client, Gemini client, and database. Sets up event handlers for commands and a background scheduler for automated digests.
- `database.py`: Handles SQLite interactions for managing the list of target chats and tracking the timestamp of the last successful run.
- `digest_session.session`: (Generated) Telethon session file for authentication.
- `digest_bot.db`: (Generated) SQLite database file.

---

## Building and Running

### Setup
1. **Initialize Virtual Environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Configuration:**
   - Ensure `.env` exists with `API_ID`, `API_HASH`, and `GEMINI_API_KEY`.
   - See `.env.example` for reference.

### Execution
- **Start the Bot:**
  ```bash
  python main.py
  ```
- **Manual Verification:** Use the `/digest` command in your Telegram "Saved Messages" to trigger an immediate digest generation.

### Testing
- Run the test suite with:
  ```bash
  venv/bin/python -m unittest discover -s tests
  ```

---

## Development Conventions

### Coding Style
- **Asynchronous Logic:** Use `async/await` throughout, adhering to Telethon's event-driven architecture.
- **Error Handling:** Log errors using the `logging` module. Provide user-friendly feedback for Telegram command failures.
- **Self-Cleaning UI:** Command messages and temporary status responses in Telegram should be deleted after a short delay (using `asyncio.sleep` and `event.delete()`) to keep the "Saved Messages" clean.

### Prompt Engineering
- The digest prompt is located in the `generate_digest_summary` function in `main.py`.
- It currently instructs Gemini to group summaries by "Chat Title" and use Markdown formatting.

### Database Updates
- When modifying the schema in `database.py`, ensure the `init_db()` function handles migrations or provides instructions for existing users (currently, it only uses `CREATE TABLE IF NOT EXISTS`).

---

## Command Reference (Telegram "Saved Messages")
- `/add <chat>`: Add a chat (username or ID) to the track list.
- `/remove <chat>`: Remove a chat from the track list.
- `/list`: List all tracked chats.
- `/digest`: Trigger a manual digest since the last run.
