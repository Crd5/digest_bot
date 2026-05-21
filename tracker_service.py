from datetime import datetime, timezone


class TrackerService:
    def __init__(self, telegram_gateway, db_module):
        self.telegram_gateway = telegram_gateway
        self.db = db_module

    async def add_chat(self, chat_identifier: str):
        entity = await self.telegram_gateway.resolve_chat(chat_identifier)
        title = (
            getattr(entity, "title", None)
            or getattr(entity, "username", None)
            or getattr(entity, "first_name", None)
            or "Unknown Chat"
        )
        chat_id = await self.telegram_gateway.marked_peer_id(entity)
        start_message_id = await self.telegram_gateway.latest_message_id(chat_id)
        start_timestamp = int(datetime.now(timezone.utc).timestamp())
        self.db.add_target_chat(chat_id, title, start_timestamp, start_message_id)
        return {"chat_id": chat_id, "chat_title": title}

    async def remove_chat(self, chat_identifier: str):
        try:
            entity = await self.telegram_gateway.resolve_chat(chat_identifier)
            chat_id = await self.telegram_gateway.marked_peer_id(entity)
        except ValueError:
            chat_id = int(chat_identifier)
        self.db.remove_target_chat(chat_id)
        return chat_id

    def list_chats(self):
        return self.db.get_target_chats()
