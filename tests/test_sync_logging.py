from types import SimpleNamespace
import unittest

from sync_service import SyncService


class FailingGateway:
    async def collect_new_messages(self, chat_id, chat_title, last_timestamp, last_message_id, run_started_dt):
        raise RuntimeError("gateway token leaked in local diagnostic")


class SingleChatDb:
    def get_target_chats(self):
        return [
            {
                "chat_id": -100123,
                "chat_title": "Research Lab",
                "last_digest_timestamp": 100,
                "last_digest_message_id": 10,
            }
        ]

    def insert_indexed_messages(self, records):
        raise AssertionError("failed sync should not index messages")

    def update_chat_last_digest_timestamp(self, chat_id, timestamp, message_id):
        raise AssertionError("failed sync should not advance cursor")


class SyncServiceLoggingTests(unittest.IsolatedAsyncioTestCase):
    async def test_per_chat_sync_failures_are_logged_with_chat_context_and_traceback(self):
        service = SyncService(FailingGateway(), SingleChatDb())

        with self.assertLogs("sync_service", level="ERROR") as logs:
            result = await service.sync_tracked_chats()

        self.assertEqual(0, result.indexed_count)
        self.assertEqual(
            [
                SimpleNamespace(
                    chat_id=-100123,
                    chat_title="Research Lab",
                    error="gateway token leaked in local diagnostic",
                )
            ],
            [SimpleNamespace(chat_id=f.chat_id, chat_title=f.chat_title, error=f.error) for f in result.failures],
        )

        log_output = "\n".join(logs.output)
        self.assertIn("Failed to sync tracked chat", log_output)
        self.assertIn("chat_id=-100123", log_output)
        self.assertIn("chat_title='Research Lab'", log_output)
        self.assertIn("RuntimeError: gateway token leaked in local diagnostic", log_output)
        self.assertIn("Traceback", log_output)


if __name__ == "__main__":
    unittest.main()
