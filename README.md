# Telegram Digest Bot

A Telegram user bot that uses Telethon and the Google Gemini API to analyze selected chats and channels and generate daily highlights.

## Features

- **Daily Highlights:** Summarizes the activity in your tracked chats using Google Gemini.
- **Scheduled Digests:** Automatically generates a digest every day at 22:00 UTC+3.
- **On-Demand Digests:** Can be triggered manually at any time via a command.
- **Dynamic Configuration:** Manage the list of tracked chats directly from Telegram.
- **Self-Cleaning:** Automatically deletes command messages and temporary status updates to keep your "Saved Messages" tidy.

## Privacy and Security

Tracked Telegram message text, sender names, and chat titles are sent to the Google Gemini API for summarization. Only add chats whose contents you are comfortable processing with an external AI service.

Keep `.env` and `*.session` files private. They contain credentials or Telegram login state, so restrict them to your user account:

```bash
chmod 600 .env *.session 2>/dev/null || true
```

## Prerequisites

- Python 3.9 or higher.
- A Telegram API ID and API Hash (obtain from [https://my.telegram.org/](https://my.telegram.org/)).
- A Google Gemini API Key.

## Setup

1. **Clone the repository and enter the directory.**

2. **Create a virtual environment and install dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   - Copy the example environment file:
     ```bash
     cp .env.example .env
     ```
   - Open `.env` and fill in your credentials:
     - `API_ID`: Your Telegram API ID.
     - `API_HASH`: Your Telegram API Hash.
     - `GEMINI_API_KEY`: Your Google Gemini API Key.

### Linux Service Setup (Optional)

If you are running the bot on a Linux server, you can set it up as a `systemd` service using the provided script:

1. **Generate the service file:**
   ```bash
   ./setup_service.sh
   ```
2. **Follow the on-screen instructions** to copy the generated `.service` file to `/etc/systemd/system/` and start it.

*Note: Ensure you have run the bot manually at least once to complete the Telegram authentication before starting the service.*

## Usage

1. **Start the bot:**
   ```bash
   source venv/bin/activate
   python main.py
   ```
   *Note: On the first run, Telethon will ask you to enter your phone number and the login code sent to your Telegram app to authenticate the session. This will create a `digest_session.session` file locally.*

2. **Interact with the bot:**
   Send the following commands directly to your **Saved Messages** in Telegram:

   - `/add <chat_username_or_id>`: Add a chat or channel to the digest targets (e.g., `/add @durov` or `/add -100123456789`). Tracking starts from the latest message visible at add time; older history is not backfilled.
   - `/remove <chat_username_or_id>`: Remove a chat or channel from the targets.
   - `/list`: List all currently tracked chats.
   - `/digest`: Preview a digest for messages received since the last scheduled digest. This does not affect the evening scheduled digest.

The bot will also automatically generate and send a digest to your Saved Messages every day at 22:00 UTC+3. Each tracked chat keeps its own cursor, so a temporary failure in one chat does not advance the others incorrectly.

## Testing

Run the automated tests with:

```bash
venv/bin/python -m unittest discover -s tests
```
