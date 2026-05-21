from types import SimpleNamespace
import unittest

from tracker_service import TrackerService


class FakeTelegramGateway:
    def __init__(self, entity):
        self.entity = entity

    async def resolve_chat(self, chat_identifier):
        return self.entity

    async def marked_peer_id(self, entity):
        return 12345

    async def latest_message_id(self, chat_id):
        return 678


class FakeDb:
    def __init__(self):
        self.added_chats = []

    def add_target_chat(self, chat_id, chat_title, last_digest_timestamp, last_digest_message_id):
        self.added_chats.append(
            {
                "chat_id": chat_id,
                "chat_title": chat_title,
                "last_digest_timestamp": last_digest_timestamp,
                "last_digest_message_id": last_digest_message_id,
            }
        )


class TrackerServiceTests(unittest.IsolatedAsyncioTestCase):
    async def add_entity(self, entity):
        db = FakeDb()
        service = TrackerService(FakeTelegramGateway(entity), db)

        result = await service.add_chat("@alice")

        return result, db.added_chats[0]

    async def test_add_chat_uses_first_name_when_username_is_none_and_title_is_missing(self):
        result, added_chat = await self.add_entity(SimpleNamespace(username=None, first_name="Alice"))

        self.assertEqual("Alice", added_chat["chat_title"])
        self.assertEqual("Alice", result["chat_title"])

    async def test_add_chat_preserves_titles_and_usernames(self):
        cases = [
            (SimpleNamespace(title="Research Group", username="research"), "Research Group"),
            (SimpleNamespace(username="alice_handle", first_name="Alice"), "alice_handle"),
        ]

        for entity, expected_title in cases:
            with self.subTest(expected_title=expected_title):
                result, added_chat = await self.add_entity(entity)

                self.assertEqual(expected_title, added_chat["chat_title"])
                self.assertEqual(expected_title, result["chat_title"])


if __name__ == "__main__":
    unittest.main()
