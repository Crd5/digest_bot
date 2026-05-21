import importlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def require_module(name):
    spec = importlib.util.find_spec(name)
    if spec is None:
        raise AssertionError(f"Expected module {name!r} to exist")
    return importlib.import_module(name)


class IndexedChatTitleRefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        sys.modules.pop("database", None)
        self.database = require_module("database")
        self.database.DB_FILE = str(Path(self.temp_dir.name) / "digest_bot.db")
        self.database.init_db()

    def test_repeated_track_add_refreshes_indexed_titles_and_title_search(self):
        self.database.add_target_chat(-1001, "Old Space")
        self.database.insert_indexed_messages([
            {
                "chat_id": -1001,
                "chat_title": "Old Space",
                "message_id": 42,
                "message_timestamp": 1716200000,
                "sender_name": "alice",
                "text": "Historical evidence about vector clocks.",
            }
        ], indexed_at_timestamp=1716200100)

        self.database.add_target_chat(-1001, "Current Lab")

        messages = self.database.get_indexed_messages_since(0, limit=10)
        current_title_matches = self.database.search_indexed_messages("Current Lab", limit=10)
        old_title_matches = self.database.search_indexed_messages("Old Space", limit=10)

        self.assertEqual(["Current Lab"], [message["chat_title"] for message in messages])
        self.assertEqual([42], [message["message_id"] for message in current_title_matches])
        self.assertEqual(
            ["Current Lab"],
            [message["chat_title"] for message in current_title_matches],
        )
        self.assertEqual([], old_title_matches)
