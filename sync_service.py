import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


@dataclass(frozen=True)
class SyncFailure:
    chat_id: int
    chat_title: str
    error: str


@dataclass(frozen=True)
class SyncResult:
    indexed_count: int
    failures: list[SyncFailure]


class SyncService:
    def __init__(self, telegram_gateway, db_module):
        self.telegram_gateway = telegram_gateway
        self.db = db_module
        self._sync_lock = asyncio.Lock()

    async def sync_tracked_chats(self) -> SyncResult:
        async with self._sync_lock:
            run_started_dt = datetime.now(timezone.utc)
            indexed_count = 0
            failures = []

            for chat in self.db.get_target_chats():
                chat_id = chat["chat_id"]
                chat_title = chat["chat_title"]
                try:
                    batch = await self.telegram_gateway.collect_new_messages(
                        chat_id=chat_id,
                        chat_title=chat_title,
                        last_timestamp=chat.get("last_digest_timestamp", 0) or 0,
                        last_message_id=chat.get("last_digest_message_id", 0) or 0,
                        run_started_dt=run_started_dt,
                    )
                    indexed_count += self.db.insert_indexed_messages([record.to_dict() for record in batch.records])
                    if batch.cursor_update:
                        self.db.update_chat_last_digest_timestamp(
                            chat_id,
                            batch.cursor_update.timestamp,
                            batch.cursor_update.message_id,
                        )
                except Exception as exc:
                    logger.exception(
                        "Failed to sync tracked chat chat_id=%s chat_title=%r",
                        chat_id,
                        chat_title,
                    )
                    failures.append(SyncFailure(chat_id=chat_id, chat_title=chat_title, error=str(exc)))

            return SyncResult(indexed_count=indexed_count, failures=failures)
