from types import SimpleNamespace
import unittest

from bot_frontend import AssistantBotHandlers


class FakeMessage:
    def __init__(self, text):
        self.text = text
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append((text, kwargs))
        return SimpleNamespace()


def make_update(user_id=123, text="/start", chat_id=None, chat_type="private"):
    message = FakeMessage(text)
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=chat_id if chat_id is not None else user_id, type=chat_type),
        effective_message=message,
    )


def make_context(args=None):
    return SimpleNamespace(args=args or [])


class CountingTracker:
    def __init__(self):
        self.calls = []

    async def add_chat(self, identifier):
        self.calls.append(("add_chat", identifier))
        raise RuntimeError("resolve failed: secret peer id")

    async def remove_chat(self, identifier):
        self.calls.append(("remove_chat", identifier))
        raise RuntimeError("remove failed: internal db path")

    def list_chats(self):
        self.calls.append(("list_chats",))
        raise RuntimeError("list failed: sql details")


class CountingSync:
    def __init__(self):
        self.calls = []

    async def sync_tracked_chats(self):
        self.calls.append(("sync_tracked_chats",))
        raise RuntimeError("sync failed: gateway token")


class ReturnedFailureSync:
    def __init__(self):
        self.calls = []

    async def sync_tracked_chats(self):
        self.calls.append(("sync_tracked_chats",))
        return SimpleNamespace(
            indexed_count=2,
            failures=[
                SimpleNamespace(
                    chat_title="Research Lab",
                    chat_id=-100123,
                    error="ChatAdminRequiredError: leaked gateway token at /srv/private.db",
                )
            ],
        )


class CountingAssistant:
    def __init__(self):
        self.calls = []

    async def search_messages(self, query):
        self.calls.append(("search_messages", query))
        raise RuntimeError("search failed: sqlite query")

    async def answer_question(self, question):
        self.calls.append(("answer_question", question))
        raise RuntimeError("answer failed: model payload")

    async def digest(self, period):
        self.calls.append(("digest", period))
        raise ValueError("time data 'since nope' does not match format")


class BotFrontendErrorTests(unittest.IsolatedAsyncioTestCase):
    def make_handlers(self):
        tracker = CountingTracker()
        sync = CountingSync()
        assistant = CountingAssistant()
        return AssistantBotHandlers(123, tracker, sync, assistant), tracker, sync, assistant

    async def test_owner_service_exceptions_get_generic_plain_text_reply(self):
        cases = [
            ("track_add", "/track_add @research", ["@research"], "resolve failed"),
            ("track_remove", "/track_remove -1001", ["-1001"], "internal db"),
            ("track_list", "/track_list", [], "sql details"),
            ("sync", "/sync", [], "gateway token"),
            ("search", "/search roadmap", ["roadmap"], "sqlite query"),
            ("ask", "/ask what changed", ["what", "changed"], "model payload"),
            ("digest", "/digest since nope", ["since", "nope"], "time data"),
            ("natural_message", "what changed?", [], "model payload"),
        ]

        for handler_name, text, args, leaked_detail in cases:
            with self.subTest(handler_name=handler_name):
                handlers, _, _, _ = self.make_handlers()
                update = make_update(text=text)

                with self.assertLogs("bot_frontend", level="ERROR"):
                    await getattr(handlers, handler_name)(update, make_context(args))

                self.assertEqual(1, len(update.effective_message.replies))
                reply_text, kwargs = update.effective_message.replies[0]
                self.assertIn("couldn't complete", reply_text)
                self.assertIn("try again", reply_text)
                self.assertNotIn(leaked_detail, reply_text)
                self.assertEqual({"parse_mode": None}, kwargs)

    async def test_owner_service_exception_logs_are_sanitized(self):
        handlers, _, _, _ = self.make_handlers()
        update = make_update(text="/sync")

        with self.assertLogs("bot_frontend", level="ERROR") as logs:
            await handlers.sync(update, make_context())

        log_output = "\n".join(logs.output)
        self.assertIn("Owner bot handler failed", log_output)
        self.assertIn("the /sync command", log_output)
        self.assertNotIn("gateway token", log_output)
        self.assertNotIn("sync failed", log_output)

    async def test_sync_returned_failures_get_sanitized_warning_reply(self):
        sync = ReturnedFailureSync()
        handlers = AssistantBotHandlers(123, CountingTracker(), sync, CountingAssistant())
        update = make_update(text="/sync")

        await handlers.sync(update, make_context())

        self.assertEqual([("sync_tracked_chats",)], sync.calls)
        self.assertEqual(1, len(update.effective_message.replies))
        reply_text, kwargs = update.effective_message.replies[0]
        self.assertIn("Indexed 2 new messages.", reply_text)
        self.assertIn("Sync warnings:", reply_text)
        self.assertIn("Research Lab (-100123)", reply_text)
        self.assertIn("could not be synced", reply_text)
        self.assertNotIn("ChatAdminRequiredError", reply_text)
        self.assertNotIn("leaked gateway token", reply_text)
        self.assertNotIn("/srv/private.db", reply_text)
        self.assertEqual({"parse_mode": None}, kwargs)

    async def test_unauthorized_updates_are_rejected_before_reply_and_side_effects(self):
        unauthorized_updates = [
            ("non_owner_private", {"user_id": 999}),
            ("owner_group", {"user_id": 123, "chat_id": -10055, "chat_type": "supergroup"}),
        ]
        cases = [
            ("track_add", "/track_add @research", ["@research"]),
            ("track_remove", "/track_remove -1001", ["-1001"]),
            ("track_list", "/track_list", []),
            ("sync", "/sync", []),
            ("search", "/search roadmap", ["roadmap"]),
            ("ask", "/ask what changed", ["what", "changed"]),
            ("digest", "/digest since nope", ["since", "nope"]),
            ("natural_message", "what changed?", []),
        ]

        for scenario, update_kwargs in unauthorized_updates:
            for handler_name, text, args in cases:
                with self.subTest(scenario=scenario, handler_name=handler_name):
                    handlers, tracker, sync, assistant = self.make_handlers()
                    update = make_update(text=text, **update_kwargs)

                    await getattr(handlers, handler_name)(update, make_context(args))

                    self.assertEqual([], update.effective_message.replies)
                    self.assertEqual([], tracker.calls)
                    self.assertEqual([], sync.calls)
                    self.assertEqual([], assistant.calls)
