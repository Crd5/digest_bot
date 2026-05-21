from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional


INITIAL_FETCH_LIMIT = 100


@dataclass(frozen=True)
class CursorUpdate:
    timestamp: int
    message_id: int = 0


@dataclass(frozen=True)
class MessageRecord:
    chat_id: int
    chat_title: str
    message_id: int
    message_timestamp: int
    sender_name: str
    text: str

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class MessageBatch:
    records: list[MessageRecord]
    cursor_update: Optional[CursorUpdate]


def as_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def compute_cursor_update(
    last_timestamp: int,
    last_message_id: int,
    max_seen_timestamp: int,
    max_seen_message_id: int,
    fallback_timestamp: int,
) -> Optional[CursorUpdate]:
    if max_seen_message_id > last_message_id:
        return CursorUpdate(max_seen_timestamp or fallback_timestamp, max_seen_message_id)
    if not last_message_id and max_seen_timestamp > last_timestamp:
        return CursorUpdate(max_seen_timestamp, 0)
    return None


async def sender_display_name(message) -> str:
    try:
        sender = await message.get_sender()
    except Exception:
        return "Unknown"
    return (
        getattr(sender, "username", None)
        or getattr(sender, "first_name", None)
        or getattr(sender, "title", None)
        or "Unknown"
    )


class ReadOnlyTelegramGateway:
    def __init__(self, telegram_client):
        self._client = telegram_client

    async def resolve_chat(self, chat_identifier: str):
        try:
            return await self._client.get_entity(chat_identifier)
        except ValueError:
            return await self._client.get_entity(int(chat_identifier))

    async def marked_peer_id(self, entity) -> int:
        return await self._client.get_peer_id(entity)

    async def latest_message_id(self, chat_id: int) -> int:
        messages = await self._client.get_messages(chat_id, limit=1)
        if not messages:
            return 0
        return getattr(messages[0], "id", 0) or 0

    async def collect_new_messages(
        self,
        chat_id: int,
        chat_title: str,
        last_timestamp: int,
        last_message_id: int,
        run_started_dt: datetime,
    ) -> MessageBatch:
        last_dt = datetime.fromtimestamp(last_timestamp, tz=timezone.utc) if last_timestamp > 0 else None
        run_started_utc = as_utc_datetime(run_started_dt)
        run_started_timestamp = int(run_started_utc.timestamp())
        max_seen_message_id = last_message_id
        max_seen_timestamp = last_timestamp
        records = []
        limit = None if last_timestamp > 0 or last_message_id > 0 else INITIAL_FETCH_LIMIT

        async for message in self._client.iter_messages(chat_id, limit=limit):
            message_id = getattr(message, "id", 0) or 0
            message_dt = as_utc_datetime(message.date) if getattr(message, "date", None) else None

            if last_message_id and message_id and message_id <= last_message_id:
                break
            if message_dt and message_dt > run_started_utc:
                continue
            if not last_message_id and last_dt and message_dt and message_dt < last_dt:
                break

            if message_id:
                max_seen_message_id = max(max_seen_message_id, message_id)
            if message_dt:
                max_seen_timestamp = max(max_seen_timestamp, int(message_dt.timestamp()))

            text = (getattr(message, "text", None) or "").strip()
            if text:
                records.append(
                    MessageRecord(
                        chat_id=chat_id,
                        chat_title=chat_title,
                        message_id=message_id,
                        message_timestamp=int(message_dt.timestamp()) if message_dt else run_started_timestamp,
                        sender_name=await sender_display_name(message),
                        text=text,
                    )
                )

        cursor_update = compute_cursor_update(
            last_timestamp,
            last_message_id,
            max_seen_timestamp,
            max_seen_message_id,
            run_started_timestamp,
        )
        return MessageBatch(list(reversed(records)), cursor_update)
