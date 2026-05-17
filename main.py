import os
import asyncio
from datetime import datetime, timezone
import logging

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

async def generate_digest_summary(text_content: str) -> str:
    if not text_content.strip():
        return "No new messages."
    
    prompt = (
        "You are an expert assistant. Summarize the key discussions, announcements, and highlights "
        "from the following chat messages. Group the summary by Chat Title and present it clearly using Markdown.\n\n"
        f"{text_content}"
    )
    
    try:
        # Note: Using gemini-2.5-pro as it's the current recommended model for general tasks
        # You mentioned Gemini 3.1 Pro, if that specific model string is available in your project/org, you can replace it here.
        response = gemini_client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        logger.error(f"Error generating summary with Gemini: {e}")
        return "Error: Could not generate summary due to an API error."

async def fetch_messages_and_digest():
    logger.info("Starting digest generation...")
    target_chats = database.get_target_chats()
    if not target_chats:
        logger.info("No target chats configured.")
        return "No target chats configured. Add some using `/add <chat>`."

    last_run = database.get_last_run_timestamp()
    last_run_dt = datetime.fromtimestamp(last_run, tz=timezone.utc) if last_run > 0 else None
    
    messages_by_chat = {}
    
    for chat_info in target_chats:
        chat_id = chat_info['chat_id']
        chat_title = chat_info['chat_title']
        messages_by_chat[chat_title] = []
        
        try:
            # Fetch messages since last run. If last_run is 0, just fetch last 100 to avoid huge backlog on first run
            limit = None if last_run > 0 else 100
            offset_date = last_run_dt if last_run > 0 else None
            
            # Using iter_messages with offset_date
            # Note: telethon's offset_date gets messages OLDER than the date. 
            # We want NEWER than last_run_dt.
            # We can use reverse=True and offset_date to get messages AFTER a date, but it might be easier to fetch and break.
            
            async for message in client.iter_messages(chat_id, limit=limit):
                if last_run_dt and message.date and message.date <= last_run_dt:
                    break # We reached messages we already processed
                
                if message.text:
                    sender = await message.get_sender()
                    sender_name = sender.username or sender.first_name or "Unknown" if sender else "Unknown"
                    msg_time = message.date.strftime("%Y-%m-%d %H:%M:%S")
                    messages_by_chat[chat_title].append(f"[{msg_time}] {sender_name}: {message.text}")
                    
        except Exception as e:
            logger.error(f"Error fetching from {chat_title} ({chat_id}): {e}")

    # Compile the prompt content
    compiled_text = ""
    total_messages = 0
    for chat_title, msgs in messages_by_chat.items():
        if msgs:
            # Messages are fetched newest to oldest, reverse them for chronological order
            msgs.reverse()
            compiled_text += f"--- Chat: {chat_title} ---\n"
            compiled_text += "\n".join(msgs)
            compiled_text += "\n\n"
            total_messages += len(msgs)

    if total_messages == 0:
        logger.info("No new messages found.")
        database.update_last_run_timestamp(int(datetime.now(timezone.utc).timestamp()))
        return "No new messages in the tracked chats since the last digest."
    
    summary = await generate_digest_summary(compiled_text)
    
    # Update state
    database.update_last_run_timestamp(int(datetime.now(timezone.utc).timestamp()))
    
    logger.info("Digest generation complete.")
    return f"**Daily Digest**\n\n{summary}"

async def send_digest():
    summary_text = await fetch_messages_and_digest()
    await client.send_message('me', summary_text)

# Event Handlers for commands in Saved Messages (peer 'me')
@events.register(events.NewMessage(chats='me', pattern=r'^/add\s+(.+)'))
async def add_command_handler(event):
    chat_identifier = event.pattern_match.group(1).strip()
    try:
        # Try to resolve entity
        entity = await client.get_entity(chat_identifier)
        title = getattr(entity, 'title', getattr(entity, 'username', 'Unknown Chat'))
        database.add_target_chat(entity.id, title)
        status = await event.respond(f"Added '{title}' (ID: {entity.id}) to digest targets.")
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
            entity = await client.get_entity(chat_identifier)
            chat_id = entity.id
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
    
    summary_text = await fetch_messages_and_digest()
    await client.send_message('me', summary_text)
    
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