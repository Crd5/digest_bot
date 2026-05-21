import sys
import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import main as runtime_main
from main import run_bot_application


class PollingFailure(Exception):
    pass


class UpdaterStopFailure(Exception):
    pass


class BuildApplicationFailure(Exception):
    pass


class TelegramStartupFailure(Exception):
    pass


class FakeTelegramClient:
    def __init__(self):
        self.started = False
        self.disconnected = False
        self.calls = []

    async def start(self):
        self.started = True
        self.calls.append("telegram.start")

    async def disconnect(self):
        self.disconnected = True
        self.calls.append("telegram.disconnect")


class FailingStartupTelegramClient(FakeTelegramClient):
    async def start(self):
        self.started = True
        self.calls.append("telegram.start")
        raise TelegramStartupFailure("telegram startup failed")


class FakeUpdater:
    def __init__(self, calls):
        self.calls = calls
        self.running = False

    async def start_polling(self, *args, **kwargs):
        self.calls.append("updater.start_polling")
        raise PollingFailure("polling failed")

    async def stop(self):
        self.calls.append("updater.stop")


class FakeApplication:
    def __init__(self):
        self.calls = []
        self.updater = FakeUpdater(self.calls)
        self.initialized = False
        self.running = False

    async def initialize(self):
        self.calls.append("application.initialize")
        self.initialized = True

    async def start(self):
        self.calls.append("application.start")
        self.running = True

    async def stop(self):
        self.calls.append("application.stop")
        self.running = False

    async def shutdown(self):
        self.calls.append("application.shutdown")
        self.initialized = False


class StoppableUpdater:
    def __init__(self, calls, polling_started, stop_error=None):
        self.calls = calls
        self.polling_started = polling_started
        self.stop_error = stop_error
        self.error_callback = None
        self.running = False

    async def start_polling(self, *args, error_callback=None, **kwargs):
        self.calls.append("updater.start_polling")
        self.error_callback = error_callback
        self.running = True
        self.polling_started.set()

    async def stop(self):
        self.calls.append("updater.stop")
        if self.stop_error:
            raise self.stop_error
        self.running = False


class StoppableApplication:
    def __init__(self, updater_stop_error=None):
        self.calls = []
        self.polling_started = asyncio.Event()
        self.started = asyncio.Event()
        self.initialized = False
        self.running = False
        self.processed_errors = []
        self.created_tasks = []
        self.updater = StoppableUpdater(
            self.calls,
            self.polling_started,
            stop_error=updater_stop_error,
        )
        self.post_init = self._post_init
        self.post_stop = self._post_stop
        self.post_shutdown = self._post_shutdown

    async def initialize(self):
        self.calls.append("application.initialize")
        self.initialized = True

    async def _post_init(self, application):
        self.assert_is_self(application)
        self.calls.append("application.post_init")

    async def start(self):
        self.calls.append("application.start")
        self.running = True
        self.started.set()

    async def stop(self):
        self.calls.append("application.stop")
        self.running = False

    async def _post_stop(self, application):
        self.assert_is_self(application)
        self.calls.append("application.post_stop")

    async def shutdown(self):
        self.calls.append("application.shutdown")
        self.initialized = False

    async def _post_shutdown(self, application):
        self.assert_is_self(application)
        self.calls.append("application.post_shutdown")

    def assert_is_self(self, application):
        if application is not self:
            raise AssertionError("post hook did not receive the application instance")

    def create_task(self, coroutine):
        self.calls.append("application.create_task")
        task = asyncio.create_task(coroutine)
        self.created_tasks.append(task)
        return task

    async def process_error(self, *, error, update=None):
        self.calls.append("application.process_error")
        self.processed_errors.append((error, update))


class ApplicationWithoutUpdater:
    def __init__(self):
        self.calls = []
        self.updater = None

    async def initialize(self):
        self.calls.append("application.initialize")


class RuntimeLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_main_disconnects_telegram_client_when_start_fails(self):
        fake_client = FailingStartupTelegramClient()
        settings = runtime_main.RuntimeSettings(
            api_id=123,
            api_hash="hash",
            gemini_api_key="gemini-key",
            bot_token="bot-token",
            owner_telegram_user_id=456,
        )

        with patch.object(
            runtime_main, "initialize_runtime", return_value=settings
        ), patch.object(
            runtime_main, "get_telegram_client", return_value=fake_client
        ):
            with self.assertRaises(TelegramStartupFailure):
                await runtime_main.main()

        self.assertTrue(fake_client.started)
        self.assertTrue(fake_client.disconnected)
        self.assertEqual(["telegram.start", "telegram.disconnect"], fake_client.calls)

    async def test_main_disconnects_telegram_client_when_application_build_fails_after_start(self):
        fake_client = FakeTelegramClient()
        settings = runtime_main.RuntimeSettings(
            api_id=123,
            api_hash="hash",
            gemini_api_key="gemini-key",
            bot_token="bot-token",
            owner_telegram_user_id=456,
        )

        with patch.object(
            runtime_main, "initialize_runtime", return_value=settings
        ), patch.object(
            runtime_main, "get_telegram_client", return_value=fake_client
        ), patch.object(
            runtime_main, "get_gemini_client", return_value=object()
        ), patch.object(
            runtime_main, "restrict_local_private_files"
        ), patch.object(
            runtime_main, "ReadOnlyTelegramGateway", return_value=object()
        ), patch.object(
            runtime_main, "GeminiModelClient", return_value=object()
        ), patch.object(
            runtime_main, "AssistantService", return_value=object()
        ), patch.object(
            runtime_main, "TrackerService", return_value=object()
        ), patch.object(
            runtime_main, "SyncService", return_value=object()
        ), patch.object(
            runtime_main, "AssistantBotHandlers", return_value=object()
        ), patch.object(
            runtime_main,
            "build_application",
            side_effect=BuildApplicationFailure("application build failed"),
        ):
            with self.assertRaises(BuildApplicationFailure):
                await runtime_main.main()

        self.assertTrue(fake_client.started)
        self.assertTrue(fake_client.disconnected)
        self.assertEqual(["telegram.start", "telegram.disconnect"], fake_client.calls)

    async def test_polling_start_failure_shuts_down_initialized_application(self):
        application = FakeApplication()

        with self.assertRaises(PollingFailure):
            await run_bot_application(application)

        self.assertEqual(
            [
                "application.initialize",
                "updater.start_polling",
                "application.shutdown",
            ],
            application.calls,
        )

    async def test_run_bot_application_requires_updater(self):
        application = ApplicationWithoutUpdater()

        with self.assertRaisesRegex(RuntimeError, "Updater"):
            await run_bot_application(application, stop_event=asyncio.Event())

        self.assertEqual([], application.calls)

    async def test_run_bot_application_matches_ptb_polling_lifecycle_order(self):
        application = StoppableApplication()
        stop_event = asyncio.Event()

        run_task = asyncio.create_task(run_bot_application(application, stop_event=stop_event))
        await asyncio.wait_for(application.started.wait(), timeout=1)
        stop_event.set()
        await asyncio.wait_for(run_task, timeout=1)

        self.assertEqual(
            [
                "application.initialize",
                "application.post_init",
                "updater.start_polling",
                "application.start",
                "updater.stop",
                "application.stop",
                "application.post_stop",
                "application.shutdown",
                "application.post_shutdown",
            ],
            application.calls,
        )

    async def test_updater_stop_failure_still_stops_and_shuts_down_application(self):
        application = StoppableApplication(updater_stop_error=UpdaterStopFailure("stop failed"))
        stop_event = asyncio.Event()

        run_task = asyncio.create_task(run_bot_application(application, stop_event=stop_event))
        await asyncio.wait_for(application.polling_started.wait(), timeout=1)
        stop_event.set()

        with self.assertRaises(UpdaterStopFailure):
            await asyncio.wait_for(run_task, timeout=1)

        self.assertEqual(
            [
                "application.initialize",
                "application.post_init",
                "updater.start_polling",
                "application.start",
                "updater.stop",
                "application.stop",
                "application.post_stop",
                "application.shutdown",
                "application.post_shutdown",
            ],
            application.calls,
        )

    async def test_polling_error_callback_forwards_to_application_error_handlers(self):
        application = StoppableApplication()
        stop_event = asyncio.Event()
        polling_error = RuntimeError("polling callback failed")

        run_task = asyncio.create_task(run_bot_application(application, stop_event=stop_event))
        await asyncio.wait_for(application.started.wait(), timeout=1)

        self.assertIsNotNone(application.updater.error_callback)
        self.assertIsNone(application.updater.error_callback(polling_error))
        await asyncio.wait_for(application.created_tasks[-1], timeout=1)

        stop_event.set()
        await asyncio.wait_for(run_task, timeout=1)

        self.assertEqual([(polling_error, None)], application.processed_errors)


if __name__ == "__main__":
    unittest.main()
