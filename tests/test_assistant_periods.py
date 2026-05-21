import json
import unittest
from datetime import datetime, time as datetime_time

from assistant_service import AssistantService, LOCAL_TIMEZONE, MAX_DIGEST_MESSAGES


class ExplodingDatabase:
    def get_indexed_messages_since(self, since_timestamp, limit):
        raise AssertionError("invalid digest periods should not query the database")


class ExplodingModel:
    async def generate_text(self, prompt):
        raise AssertionError("invalid digest periods should not call the model")


class EmptyDatabase:
    def __init__(self):
        self.calls = []

    def get_indexed_messages_since(self, since_timestamp, limit):
        self.calls.append((since_timestamp, limit))
        return []


class LargeDigestDatabase:
    def get_indexed_messages_since(self, since_timestamp, limit):
        max_size_text = "x" * 4096
        return [
            {
                "chat_title": f"Chat {index}",
                "sender_name": f"Sender {index}",
                "message_timestamp": 1716163200 + index,
                "message_id": index,
                "text": max_size_text,
            }
            for index in range(limit)
        ]


class CapturingModel:
    def __init__(self):
        self.prompts = []

    async def generate_text(self, prompt):
        self.prompts.append(prompt)
        return "digest"


class AssistantDigestPeriodTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_since_date_returns_usage_without_side_effects(self):
        result = await AssistantService(ExplodingDatabase(), ExplodingModel()).digest("since nope")

        self.assertIn("Invalid date", result)
        self.assertIn("YYYY-MM-DD", result)

    async def test_blank_period_defaults_to_today(self):
        database = EmptyDatabase()

        result = await AssistantService(database, ExplodingModel()).digest("")

        self.assertIn("No indexed Telegram messages found for today.", result)
        self.assertEqual(1, len(database.calls))
        self.assertEqual(MAX_DIGEST_MESSAGES, database.calls[0][1])

    async def test_today_period_uses_today_label(self):
        database = EmptyDatabase()

        result = await AssistantService(database, ExplodingModel()).digest("today")

        self.assertIn("No indexed Telegram messages found for today.", result)
        self.assertEqual(1, len(database.calls))
        self.assertEqual(MAX_DIGEST_MESSAGES, database.calls[0][1])

    async def test_valid_since_period_uses_requested_date(self):
        database = EmptyDatabase()

        result = await AssistantService(database, ExplodingModel()).digest("since 2024-05-20")

        expected_start = datetime.combine(
            datetime(2024, 5, 20).date(),
            datetime_time.min,
            tzinfo=LOCAL_TIMEZONE,
        )
        self.assertIn("No indexed Telegram messages found for since 2024-05-20.", result)
        self.assertEqual([(int(expected_start.timestamp()), MAX_DIGEST_MESSAGES)], database.calls)

    async def test_unsupported_period_label_returns_usage_without_side_effects(self):
        for period in ("weekly", "todya"):
            with self.subTest(period=period):
                result = await AssistantService(ExplodingDatabase(), ExplodingModel()).digest(period)

                self.assertEqual("Invalid date. Usage: /digest [today|since YYYY-MM-DD]", result)

    async def test_digest_prompt_input_is_bounded_for_large_indexed_messages(self):
        model = CapturingModel()

        result = await AssistantService(LargeDigestDatabase(), model).digest("today")

        self.assertEqual("digest", result)
        self.assertEqual(1, len(model.prompts))
        prompt = model.prompts[0]
        self.assertLessEqual(len(prompt), 70_000)

        payload = json.loads(prompt.split("JSON payload:\n", 1)[1])
        self.assertEqual(MAX_DIGEST_MESSAGES, len(payload["messages"]))
        self.assertEqual("Chat 0", payload["messages"][0]["chat_title"])
        self.assertEqual("Sender 0", payload["messages"][0]["sender_name"])
        self.assertEqual(0, payload["messages"][0]["message_id"])
        self.assertIn("[truncated", payload["messages"][0]["text"])
