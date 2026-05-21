import asyncio
import logging
import os
import signal
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

import database
from ai_model import GeminiModelClient
from assistant_service import AssistantService
from bot_frontend import AssistantBotHandlers, build_application
from sync_service import SyncService
from telegram_gateway import ReadOnlyTelegramGateway
from tracker_service import TrackerService


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PRIVATE_FILE_MODE = 0o600
PRIVATE_FILE_SIDECAR_SUFFIXES = ("-journal", "-wal", "-shm")

TelegramClient = None
genai = None

client = None  # type: Optional[Any]
gemini_client = None  # type: Optional[Any]
runtime_settings = None


@dataclass(frozen=True)
class RuntimeSettings:
    api_id: int
    api_hash: str
    gemini_api_key: str
    bot_token: str
    owner_telegram_user_id: int


def private_file_sidecars(file_path: Path) -> list[Path]:
    return [Path(f"{file_path}{suffix}") for suffix in PRIVATE_FILE_SIDECAR_SUFFIXES]


def local_private_file_paths() -> list[Path]:
    paths = [
        path
        for path in Path(".").glob(".env*")
        if path.name != ".env.example"
    ]
    paths.extend(Path(".").glob("*.session*"))

    db_path = Path(database.DB_FILE)
    paths.append(db_path)
    paths.extend(private_file_sidecars(db_path))
    return paths


def restrict_private_file_permissions(file_paths) -> None:
    for file_path in file_paths:
        try:
            path = Path(file_path)
            if path.is_file():
                path.chmod(PRIVATE_FILE_MODE)
        except OSError as exc:
            logger.warning("Could not restrict permissions on %s: %s", file_path, exc)


def restrict_local_private_files() -> None:
    restrict_private_file_permissions(local_private_file_paths())


def load_runtime_settings() -> RuntimeSettings:
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    bot_token = os.getenv("BOT_TOKEN")
    owner_user_id = os.getenv("OWNER_TELEGRAM_USER_ID")

    if not all([api_id, api_hash, gemini_api_key, bot_token, owner_user_id]):
        raise RuntimeError(
            "Please set API_ID, API_HASH, GEMINI_API_KEY, BOT_TOKEN, and "
            "OWNER_TELEGRAM_USER_ID in the .env file."
        )

    try:
        api_id_int = int(api_id)
    except (TypeError, ValueError):
        raise RuntimeError("API_ID must be an integer in the .env file.") from None

    try:
        owner_user_id_int = int(owner_user_id)
    except (TypeError, ValueError):
        raise RuntimeError("OWNER_TELEGRAM_USER_ID must be an integer in the .env file.") from None

    return RuntimeSettings(
        api_id=api_id_int,
        api_hash=api_hash,
        gemini_api_key=gemini_api_key,
        bot_token=bot_token,
        owner_telegram_user_id=owner_user_id_int,
    )


def get_telegram_client_class():
    global TelegramClient
    if TelegramClient is None:
        from telethon import TelegramClient as telethon_client

        TelegramClient = telethon_client
    return TelegramClient


def get_genai_module():
    global genai
    if genai is None:
        from google import genai as google_genai

        genai = google_genai
    return genai


def initialize_runtime() -> RuntimeSettings:
    global client, gemini_client, runtime_settings

    os.umask(0o077)
    load_dotenv()
    restrict_local_private_files()
    settings = load_runtime_settings()

    client = get_telegram_client_class()("digest_session", settings.api_id, settings.api_hash)
    gemini_client = get_genai_module().Client(api_key=settings.gemini_api_key)
    runtime_settings = settings
    database.init_db()
    restrict_local_private_files()
    return settings


def get_telegram_client() -> Any:
    if client is None:
        raise RuntimeError("Telegram client is not initialized.")
    return client


def get_gemini_client() -> Any:
    if gemini_client is None:
        raise RuntimeError("Gemini client is not initialized.")
    return gemini_client


async def run_bot_application(application, stop_event: Optional[asyncio.Event] = None):
    if not getattr(application, "updater", None):
        raise RuntimeError("run_bot_application requires an application with an Updater.")

    owns_stop_event = stop_event is None
    if stop_event is None:
        stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    registered_signals = []
    if owns_stop_event:
        for stop_signal in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(stop_signal, stop_event.set)
                registered_signals.append(stop_signal)
            except (NotImplementedError, RuntimeError, ValueError):
                logger.debug("Signal handlers are not supported for %s.", stop_signal.name)

    initialized = False
    started = False
    try:
        await application.initialize()
        initialized = True
        if post_init := getattr(application, "post_init", None):
            await post_init(application)

        def error_callback(exc):
            application.create_task(application.process_error(error=exc, update=None))

        await application.updater.start_polling(error_callback=error_callback)
        await application.start()
        started = True
        await stop_event.wait()
    finally:
        for registered_signal in registered_signals:
            loop.remove_signal_handler(registered_signal)
        cleanup_error = None

        async def run_cleanup_step(name, cleanup):
            nonlocal cleanup_error
            try:
                await cleanup()
                return True
            except Exception as exc:
                if cleanup_error is None:
                    cleanup_error = exc
                else:
                    logger.exception("Additional error during %s cleanup.", name)
                return False

        updater = getattr(application, "updater", None)
        if updater and getattr(updater, "running", False):
            await run_cleanup_step("updater stop", application.updater.stop)
        if getattr(application, "running", started):
            stopped = await run_cleanup_step("application stop", application.stop)
            if stopped and (post_stop := getattr(application, "post_stop", None)):
                await run_cleanup_step("application post_stop", lambda: post_stop(application))
        if initialized:
            await run_cleanup_step("application shutdown", application.shutdown)
            if post_shutdown := getattr(application, "post_shutdown", None):
                await run_cleanup_step(
                    "application post_shutdown",
                    lambda: post_shutdown(application),
                )
        if cleanup_error is not None:
            raise cleanup_error


async def main():
    logger.info("Starting Telegram Read-Only AI Assistant...")
    settings = initialize_runtime()
    telegram_client = get_telegram_client()
    try:
        await telegram_client.start()
        restrict_local_private_files()

        gateway = ReadOnlyTelegramGateway(telegram_client)
        model_client = GeminiModelClient(get_gemini_client())
        assistant = AssistantService(database, model_client)
        tracker = TrackerService(gateway, database)
        sync_service = SyncService(gateway, database)
        handlers = AssistantBotHandlers(
            owner_user_id=settings.owner_telegram_user_id,
            tracker=tracker,
            sync_service=sync_service,
            assistant=assistant,
        )
        application = build_application(settings.bot_token, handlers)

        logger.info("Bot API front end is running for owner user %s.", settings.owner_telegram_user_id)
        logger.info("Telethon is running in read-only gateway mode.")
        await run_bot_application(application)
    finally:
        await telegram_client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as exc:
        logger.error(exc)
        raise SystemExit(1)
