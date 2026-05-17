import os
import asyncio
from datetime import datetime, timezone
import logging
from typing import Dict, NamedTuple, Optional

from telethon import TelegramClient, events
from google import genai
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not all([API_ID, API_HASH, GEMINI_API_KEY]):
    logger.error("Please set API_ID, API_HASH, and GEMINI_API_KEY in the .env file.")
    exit(1)

# Initialize Clients
client = TelegramClient('digest_session', int(API_ID), API_HASH)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
database.init_db()
digest_lock = None  # type: Optional[asyncio.Lock]


class DigestResult(NamedTuple):
    text: str
    cursor_updates: Dict[int, int]


def get_digest_lock() -> asyncio.Lock:
    global digest_lock
    if digest_lock is None:
        digest_lock = asyncio.Lock()
    return digest_lock


async def resolve_chat_entity(chat_identifier: str):
    try:
        return await client.get_entity(chat_identifier)
    except ValueError:
        return await client.get_entity(int(chat_identifier))


async def generate_digest_summary(chat_title: str, text_content: str) -> str:
    if not text_content.strip():
        return ""

    prompt = (
        f"You are an expert assistant. Summarize the key discussions, announcements, and highlights "
        f"specifically for the Telegram chat: '{chat_title}'.\n\n"
        "Please provide a clear, concise summary using Markdown. Focus on the most important information.\n\n"
        f"Messages:\n{text_content}"
    )

    # Note: Using gemini-2.5-pro as it's the current recommended model for general tasks
    response = await gemini_client.aio.models.generate_content(
        model='gemini-2.5-pro',
        contents=prompt,
    )
    response_text = (response.text or "").strip()
    return f"### {chat_title}\n{response_text}"


async def summarize_chat(chat_id: int, chat_title: str, text_content: str):
    try:
        summary = await generate_digest_summary(chat_title, text_content)
        return chat_id, summary, True
    except Exception as e:
        logger.error(f"Error generating summary for {chat_title}: {e}")
        return chat_id, f"### {chat_title}\nError: Could not generate summary due to an API error.", False


def commit_cursor_updates(cursor_updates: Dict[int, int]) -> None:
    for chat_id, timestamp in cursor_updates.items():
        database.update_chat_last_digest_timestamp(chat_id, timestamp)


async def build_digest_result() -> DigestResult:
    logger.info("Starting digest generation...")
    target_chats = database.get_target_chats()
    if not target_chats:
        logger.info("No target chats configured.")
        return DigestResult("No target chats configured. Add some using `/add <chat>`.", {})

    run_started_timestamp = int(datetime.now(timezone.utc).timestamp())
    summary_tasks = []
    cursor_updates = {}

    for chat_info in target_chats:
        chat_id = chat_info['chat_id']
        chat_title = chat_info['chat_title']
        last_run = chat_info.get('last_digest_timestamp', 0) or 0
        last_run_dt = datetime.fromtimestamp(last_run, tz=timezone.utc) if last_run > 0 else None
        chat_messages = []

        try:
            limit = None if last_run > 0 else 100
            async for message in client.iter_messages(chat_id, limit=limit):
                if last_run_dt and message.date and message.date <= last_run_dt:
                    break

                if message.text:
                    sender = await message.get_sender()
                    sender_name = (
                        getattr(sender, 'username', None)
                        or getattr(sender, 'first_name', None)
                        or getattr(sender, 'title', None)
                        or "Unknown"
                    )
                    msg_time = message.date.strftime("%Y-%m-%d %H:%M:%S")
                    chat_messages.append(f"[{msg_time}] {sender_name}: {message.text}")
            cursor_updates[chat_id] = run_started_timestamp
        except Exception as e:
            logger.error(f"Error fetching from {chat_title} ({chat_id}): {e}")
            continue

        if chat_messages:
            chat_messages.reverse() # chronological
            compiled_chat_text = "\n".join(chat_messages)
            summary_tasks.append(summarize_chat(chat_id, chat_title, compiled_chat_text))

    if not summary_tasks:
        logger.info("No new messages found.")
        return DigestResult("No new messages in the tracked chats since the last digest.", cursor_updates)

    # Generate summaries in parallel
    summary_results = await asyncio.gather(*summary_tasks)

    failed_summary_chat_ids = {chat_id for chat_id, _, success in summary_results if not success}
    for chat_id in failed_summary_chat_ids:
        cursor_updates.pop(chat_id, None)

    # Filter out empty results and join
    individual_summaries = [summary for _, summary, _ in summary_results]
    full_summary = "\n\n".join([s for s in individual_summaries if s])

    logger.info("Digest generation complete.")
    return DigestResult(f"**Daily Digest**\n\n{full_summary}", cursor_updates)


async def fetch_messages_and_digest(advance_cursors: bool = False):
    result = await build_digest_result()
    if advance_cursors:
        commit_cursor_updates(result.cursor_updates)
    return result.text


async def send_digest(advance_cursors: bool = True):
    async with get_digest_lock():
        result = await build_digest_result()
        await client.send_message('me', result.text)
        if advance_cursors:
            commit_cursor_updates(result.cursor_updates)

# Event Handlers for commands in Saved Messages (peer 'me')
@events.register(events.NewMessage(chats='me', pattern=r'^/add\s+(.+)'))
async def add_command_handler(event):
    chat_identifier = event.pattern_match.group(1).strip()
    try:
        # Try to resolve entity
        entity = await resolve_chat_entity(chat_identifier)
        title = getattr(entity, 'title', getattr(entity, 'username', 'Unknown Chat'))
        chat_id = await client.get_peer_id(entity)
        database.add_target_chat(chat_id, title)
        status = await event.respond(f"Added '{title}' (ID: {chat_id}) to digest targets.")
    except Exception as e:
        status = await event.respond(f"Could not add chat: {e}")
    
    # Auto-cleanup
    await asyncio.sleep(5)
    await event.delete()
    await status.delete()

@events.register(events.NewMessage(chats='me', pattern=r'^/remove\s+(.+)'))
async def remove_command_handler(event):
    chat_identifier = event.pattern_match.group(1).strip()
    try:
        # Try to resolve entity to get ID
        try:
            entity = await resolve_chat_entity(chat_identifier)
            chat_id = await client.get_peer_id(entity)
        except ValueError:
            # If it's just an ID
            chat_id = int(chat_identifier)
            
        database.remove_target_chat(chat_id)
        status = await event.respond(f"Removed chat ID {chat_id} from targets.")
    except Exception as e:
        status = await event.respond(f"Could not remove chat: {e}")
        
    # Auto-cleanup
    await asyncio.sleep(5)
    await event.delete()
    await status.delete()

@events.register(events.NewMessage(chats='me', pattern=r'^/list'))
async def list_command_handler(event):
    chats = database.get_target_chats()
    if not chats:
        msg = "No chats are currently being tracked."
    else:
        msg = "Tracked chats:\n" + "\n".join([f"- {c['chat_title']} (ID: {c['chat_id']})" for c in chats])
    
    status = await event.respond(msg)
    
    # Auto-cleanup
    await asyncio.sleep(10)
    await event.delete()
    await status.delete()

@events.register(events.NewMessage(chats='me', pattern=r'^/digest'))
async def digest_command_handler(event):
    status = await event.respond("Generating digest, please wait...")

    await send_digest(advance_cursors=False)
    
    # Auto-cleanup command and status
    await event.delete()
    await status.delete()

async def main():
    logger.info("Starting Telegram Digest Bot...")
    await client.start()
    
    # Register handlers
    client.add_event_handler(add_command_handler)
    client.add_event_handler(remove_command_handler)
    client.add_event_handler(list_command_handler)
    client.add_event_handler(digest_command_handler)
    
    # Setup Scheduler for 22:00 UTC+3 (which is 19:00 UTC)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_digest, 'cron', hour=19, minute=0, timezone=timezone.utc)
    scheduler.start()
    
    logger.info("Bot is running and listening for commands in Saved Messages.")
    logger.info("Scheduled digest set for 22:00 UTC+3.")
    
    # Run indefinitely
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
