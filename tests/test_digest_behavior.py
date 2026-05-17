import asyncio
import importlib
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_main(temp_dir):
    os.environ["API_ID"] = "12345"
    os.environ["API_HASH"] = "dummy_hash"
    os.environ["GEMINI_API_KEY"] = "dummy_key"
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    previous_cwd = os.getcwd()
    os.chdir(temp_dir)
    for module_name in ("main", "database"):
        sys.modules.pop(module_name, None)
    try:
        module = importlib.import_module("main")
    finally:
        os.chdir(previous_cwd)
    return module


class FakeMessage:
    def __init__(self, text, date, sender_name):
        self.text = text
        self.date = date
        self._sender = SimpleNamespace(username=sender_name, first_name=sender_name)

    async def get_sender(self):
        return self._sender


class FakeClient:
    def __init__(self, messages_by_chat=None, *, send_error=None, fail_after=None):
        self.messages_by_chat = messages_by_chat or {}
        self.sent_messages = []
        self.send_error = send_error
        self.fail_after = fail_after

    async def iter_messages(self, chat_id, limit=None):
        messages = self.messages_by_chat.get(chat_id, [])
        if limit is not None:
            messages = messages[:limit]
        for message in messages:
            yield message

    async def send_message(self, peer, text):
        if self.fail_after is not None and len(self.sent_messages) >= self.fail_after:
            raise RuntimeError("send failed")
        if self.send_error:
            raise self.send_error
        self.sent_messages.append((peer, text))


class FakeDatabase:
    def __init__(self):
        self.targets = [
            {"chat_id": -1001, "chat_title": "One", "last_digest_timestamp": 100},
            {"chat_id": -1002, "chat_title": "Two", "last_digest_timestamp": 200},
        ]
        self.updated = {}

    def get_target_chats(self):
        return [dict(chat) for chat in self.targets]

    def update_chat_last_digest_timestamp(self, chat_id, timestamp):
        self.updated[chat_id] = timestamp


class DigestBehaviorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.main = load_main(self.temp_dir.name)

    async def test_manual_digest_preview_does_not_advance_chat_cursors(self):
        fake_db = FakeDatabase()
        self.main.database = fake_db
        self.main.client = FakeClient({
            -1001: [FakeMessage("new item", datetime.fromtimestamp(150, tz=timezone.utc), "alice")],
            -1002: [FakeMessage("newer item", datetime.fromtimestamp(250, tz=timezone.utc), "bob")],
        })

        async def fake_summary(chat_title, text_content):
            return f"### {chat_title}\n{text_content}"

        self.main.generate_digest_summary = fake_summary

        digest = await self.main.fetch_messages_and_digest(advance_cursors=False)

        self.assertIn("Daily Digest", digest)
        self.assertEqual({}, fake_db.updated)

    async def test_scheduled_digest_advances_per_chat_cursors_after_send(self):
        fake_db = FakeDatabase()
        self.main.database = fake_db
        self.main.client = FakeClient({
            -1001: [FakeMessage("new item", datetime.fromtimestamp(150, tz=timezone.utc), "alice")],
            -1002: [FakeMessage("newer item", datetime.fromtimestamp(250, tz=timezone.utc), "bob")],
        })

        async def fake_summary(chat_title, text_content):
            return f"### {chat_title}\n{text_content}"

        self.main.generate_digest_summary = fake_summary

        await self.main.send_digest(advance_cursors=True)

        self.assertEqual({-1001, -1002}, set(fake_db.updated))
        self.assertTrue(all(timestamp > 0 for timestamp in fake_db.updated.values()))

    async def test_scheduled_digest_splits_long_telegram_messages_before_sending(self):
        fake_db = FakeDatabase()
        self.main.database = fake_db
        self.main.client = FakeClient()
        self.main.MAX_TELEGRAM_MESSAGE_LENGTH = 50

        async def fake_digest_result():
            return self.main.DigestResult("A" * 120, {-1001: 456})

        self.main.build_digest_result = fake_digest_result

        await self.main.send_digest(advance_cursors=True)

        sent_texts = [text for _, text in self.main.client.sent_messages]
        self.assertEqual(["A" * 50, "A" * 50, "A" * 20], sent_texts)
        self.assertEqual({-1001: 456}, fake_db.updated)

    async def test_scheduled_digest_does_not_advance_cursors_when_split_send_fails(self):
        fake_db = FakeDatabase()
        self.main.database = fake_db
        self.main.client = FakeClient(fail_after=1)
        self.main.MAX_TELEGRAM_MESSAGE_LENGTH = 50

        async def fake_digest_result():
            return self.main.DigestResult("A" * 120, {-1001: 456})

        self.main.build_digest_result = fake_digest_result

        with self.assertRaises(RuntimeError):
            await self.main.send_digest(advance_cursors=True)

        self.assertEqual({}, fake_db.updated)

    async def test_scheduled_digest_does_not_advance_cursors_when_send_fails(self):
        fake_db = FakeDatabase()
        self.main.database = fake_db
        self.main.client = FakeClient(
            {-1001: [FakeMessage("new item", datetime.fromtimestamp(150, tz=timezone.utc), "alice")]},
            send_error=RuntimeError("send failed"),
        )

        async def fake_summary(chat_title, text_content):
            return f"### {chat_title}\n{text_content}"

        self.main.generate_digest_summary = fake_summary

        with self.assertRaises(RuntimeError):
            await self.main.send_digest(advance_cursors=True)

        self.assertEqual({}, fake_db.updated)

    async def test_digest_splits_chat_input_before_summary_generation(self):
        fake_db = FakeDatabase()
        fake_db.targets = [
            {"chat_id": -1001, "chat_title": "One", "last_digest_timestamp": 100},
        ]
        self.main.database = fake_db
        self.main.MAX_GEMINI_INPUT_CHARS = 180
        self.main.client = FakeClient({
            -1001: [
                FakeMessage("x" * 90, datetime.fromtimestamp(350, tz=timezone.utc), "alice"),
                FakeMessage("y" * 90, datetime.fromtimestamp(300, tz=timezone.utc), "bob"),
                FakeMessage("z" * 90, datetime.fromtimestamp(250, tz=timezone.utc), "carol"),
            ],
        })
        summary_inputs = []

        async def fake_summary(chat_title, text_content):
            summary_inputs.append(text_content)
            return f"### {chat_title}\nchunk {len(summary_inputs)}"

        self.main.generate_digest_summary = fake_summary

        result = await self.main.build_digest_result()

        self.assertGreater(len(summary_inputs), 1)
        self.assertTrue(all(len(text) <= self.main.MAX_GEMINI_INPUT_CHARS for text in summary_inputs))
        self.assertIn(-1001, result.cursor_updates)

    async def test_digest_excludes_messages_newer_than_run_snapshot(self):
        fake_db = FakeDatabase()
        fake_db.targets = [
            {"chat_id": -1001, "chat_title": "One", "last_digest_timestamp": 100},
        ]
        self.main.database = fake_db

        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime.fromtimestamp(150.5, tz=tz)

        self.main.datetime = FrozenDateTime
        self.main.client = FakeClient({
            -1001: [
                FakeMessage("future item", datetime.fromtimestamp(151, tz=timezone.utc), "alice"),
                FakeMessage("old item", datetime.fromtimestamp(140, tz=timezone.utc), "bob"),
            ],
        })
        summary_inputs = []

        async def fake_summary(chat_title, text_content):
            summary_inputs.append(text_content)
            return f"### {chat_title}\n{text_content}"

        self.main.generate_digest_summary = fake_summary

        result = await self.main.build_digest_result()

        self.assertEqual(1, len(summary_inputs))
        self.assertIn("old item", summary_inputs[0])
        self.assertNotIn("future item", summary_inputs[0])
        self.assertEqual({-1001: 150}, result.cursor_updates)

    async def test_summary_generation_is_concurrency_limited(self):
        fake_db = FakeDatabase()
        fake_db.targets = [
            {"chat_id": -1001, "chat_title": "One", "last_digest_timestamp": 100},
        ]
        self.main.database = fake_db
        self.main.client = FakeClient({
            -1001: [
                FakeMessage(f"item {index} " + ("x" * 40), datetime.fromtimestamp(200 + index, tz=timezone.utc), "alice")
                for index in range(8)
            ],
        })
        self.main.MAX_GEMINI_INPUT_CHARS = 80
        self.main.MAX_CONCURRENT_SUMMARIES = 2
        active = 0
        max_active = 0

        async def fake_summary(chat_title, text_content):
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.01)
            active -= 1
            return f"### {chat_title}\n{text_content}"

        self.main.generate_digest_summary = fake_summary

        await self.main.build_digest_result()

        self.assertLessEqual(max_active, 2)

    async def test_digest_reports_fetch_failures_without_advancing_failed_chat(self):
        fake_db = FakeDatabase()
        self.main.database = fake_db

        class PartiallyFailingClient(FakeClient):
            async def iter_messages(self, chat_id, limit=None):
                if chat_id == -1002:
                    raise RuntimeError("history unavailable")
                async for message in super().iter_messages(chat_id, limit=limit):
                    yield message

        self.main.client = PartiallyFailingClient({
            -1001: [FakeMessage("new item", datetime.fromtimestamp(150, tz=timezone.utc), "alice")],
        })

        async def fake_summary(chat_title, text_content):
            return f"### {chat_title}\n{text_content}"

        self.main.generate_digest_summary = fake_summary

        result = await self.main.build_digest_result()

        self.assertIn("Daily Digest", result.text)
        self.assertIn("Could not fetch messages from Two", result.text)
        self.assertIn(-1001, result.cursor_updates)
        self.assertNotIn(-1002, result.cursor_updates)

    async def test_add_command_stores_marked_peer_id(self):
        added = []
        entity = SimpleNamespace(id=123, title="Channel")

        class AddClient:
            async def get_entity(self, identifier):
                self.identifier = identifier
                return entity

            async def get_peer_id(self, peer):
                self.peer = peer
                return -100123

        class AddDatabase:
            def add_target_chat(self, chat_id, title):
                added.append((chat_id, title))

        class Status:
            async def delete(self):
                pass

        class Event:
            pattern_match = SimpleNamespace(group=lambda index: "@channel")

            async def respond(self, message):
                self.message = message
                return Status()

            async def delete(self):
                pass

        self.main.client = AddClient()
        self.main.database = AddDatabase()

        with patch.object(self.main.asyncio, "sleep", new=AsyncMock()):
            await self.main.add_command_handler(Event())

        self.assertEqual([(-100123, "Channel")], added)

    async def test_add_command_accepts_numeric_string_id(self):
        added = []
        entity = SimpleNamespace(id=123, title="Channel")

        class AddClient:
            async def get_entity(self, identifier):
                if identifier == "-100123":
                    raise ValueError("numeric string not resolved")
                if identifier == -100123:
                    return entity
                raise AssertionError(f"unexpected identifier: {identifier!r}")

            async def get_peer_id(self, peer):
                return -100123

        class AddDatabase:
            def add_target_chat(self, chat_id, title):
                added.append((chat_id, title))

        class Status:
            async def delete(self):
                pass

        class Event:
            pattern_match = SimpleNamespace(group=lambda index: "-100123")

            async def respond(self, message):
                self.message = message
                return Status()

            async def delete(self):
                pass

        self.main.client = AddClient()
        self.main.database = AddDatabase()

        with patch.object(self.main.asyncio, "sleep", new=AsyncMock()):
            await self.main.add_command_handler(Event())

        self.assertEqual([(-100123, "Channel")], added)


class ImportBehaviorTests(unittest.TestCase):
    def test_load_main_restores_cwd_when_import_fails(self):
        previous_cwd = os.getcwd()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        try:
            with patch("importlib.import_module", side_effect=ModuleNotFoundError("boom")):
                with self.assertRaises(ModuleNotFoundError):
                    load_main(temp_dir.name)

            self.assertEqual(previous_cwd, os.getcwd())
        finally:
            os.chdir(previous_cwd)

    def test_main_import_does_not_require_credentials(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))

        previous_cwd = os.getcwd()
        os.chdir(temp_dir.name)
        for module_name in ("main", "database"):
            sys.modules.pop(module_name, None)
        try:
            with patch.dict(os.environ, {}, clear=True):
                module = importlib.import_module("main")
        finally:
            os.chdir(previous_cwd)

        self.assertIsNone(module.client)
        self.assertIsNone(module.gemini_client)


class ServiceSetupTests(unittest.TestCase):
    def test_generated_systemd_unit_escapes_paths(self):
        temp_dir = tempfile.TemporaryDirectory(prefix="digest bot %")
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name)
        python_path = project_dir / "venv" / "bin" / "python"
        python_path.parent.mkdir(parents=True)
        python_path.touch()

        subprocess.run(
            [str(PROJECT_ROOT / "setup_service.sh")],
            cwd=project_dir,
            check=True,
            capture_output=True,
            text=True,
        )

        service_content = (project_dir / "tg-digest-bot.service").read_text()

        self.assertIn('WorkingDirectory="', service_content)
        self.assertIn('ExecStart="', service_content)
        self.assertIn("%%", service_content)


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        sys.modules.pop("database", None)
        self.database = importlib.import_module("database")
        self.database.DB_FILE = str(Path(self.temp_dir.name) / "digest_bot.db")
        self.database.init_db()

    def test_chat_cursor_is_stored_per_chat_and_survives_title_updates(self):
        self.database.add_target_chat(-100123, "Original")
        self.database.update_chat_last_digest_timestamp(-100123, 456)
        self.database.add_target_chat(-100123, "Renamed")

        chats = self.database.get_target_chats()

        self.assertEqual(
            [{"chat_id": -100123, "chat_title": "Renamed", "last_digest_timestamp": 456}],
            chats,
        )


if __name__ == "__main__":
    unittest.main()
