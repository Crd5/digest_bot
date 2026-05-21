import logging


MAX_BOT_REPLY_LENGTH = 4096
LOGGER = logging.getLogger(__name__)


def split_reply(text: str, max_length: int = MAX_BOT_REPLY_LENGTH):
    if not text:
        return [""]
    parts = []
    remaining = text
    while len(remaining) > max_length:
        split_at = remaining.rfind("\n", 0, max_length + 1)
        if split_at < max_length // 2:
            split_at = remaining.rfind(" ", 0, max_length + 1)
        if split_at < max_length // 2:
            split_at = max_length
        part = remaining[:split_at].rstrip() or remaining[:max_length]
        parts.append(part)
        remaining = remaining[len(part):].lstrip()
    if remaining:
        parts.append(remaining)
    return parts


def args_text(context) -> str:
    return " ".join(getattr(context, "args", []) or []).strip()


class AssistantBotHandlers:
    def __init__(self, owner_user_id: int, tracker, sync_service, assistant):
        self.owner_user_id = int(owner_user_id)
        self.tracker = tracker
        self.sync_service = sync_service
        self.assistant = assistant

    def is_owner(self, update) -> bool:
        user = getattr(update, "effective_user", None)
        chat = getattr(update, "effective_chat", None)
        return bool(
            user
            and getattr(user, "id", None) == self.owner_user_id
            and chat
            and getattr(chat, "type", None) == "private"
            and getattr(chat, "id", None) == self.owner_user_id
        )

    async def _reply(self, update, text: str):
        message = update.effective_message
        for part in split_reply(text):
            await message.reply_text(part, parse_mode=None)

    async def _guard(self, update) -> bool:
        return self.is_owner(update)

    async def _reply_command_error(self, update, request_label: str):
        await self._reply(
            update,
            f"Sorry, I couldn't complete {request_label}. Please check the input or try again later.",
        )

    async def _run_owner_handler(self, update, request_label: str, handler):
        if not await self._guard(update):
            return
        try:
            await handler()
        except Exception as exc:
            LOGGER.error(
                "Owner bot handler failed while handling %s (exception_type=%s)",
                request_label,
                type(exc).__name__,
            )
            await self._reply_command_error(update, request_label)

    async def start(self, update, context):
        async def handler():
            await self._reply(update, self.help_text())

        await self._run_owner_handler(update, "the /start command", handler)

    async def help(self, update, context):
        await self.start(update, context)

    async def track_add(self, update, context):
        async def handler():
            identifier = args_text(context)
            if not identifier:
                await self._reply(update, "Usage: /track_add <chat_username_or_id>")
                return
            chat = await self.tracker.add_chat(identifier)
            await self._reply(update, f"Tracking {chat['chat_title']} ({chat['chat_id']}).")

        await self._run_owner_handler(update, "the /track_add command", handler)

    async def track_remove(self, update, context):
        async def handler():
            identifier = args_text(context)
            if not identifier:
                await self._reply(update, "Usage: /track_remove <chat_username_or_id>")
                return
            chat_id = await self.tracker.remove_chat(identifier)
            await self._reply(update, f"Stopped tracking {chat_id}.")

        await self._run_owner_handler(update, "the /track_remove command", handler)

    async def track_list(self, update, context):
        async def handler():
            chats = self.tracker.list_chats()
            if not chats:
                await self._reply(update, "No chats are currently tracked.")
                return
            lines = ["Tracked chats:"]
            lines.extend(f"- {chat['chat_title']} ({chat['chat_id']})" for chat in chats)
            await self._reply(update, "\n".join(lines))

        await self._run_owner_handler(update, "the /track_list command", handler)

    async def sync(self, update, context):
        async def handler():
            result = await self.sync_service.sync_tracked_chats()
            message = f"Indexed {result.indexed_count} new messages."
            if result.failures:
                failures = "\n".join(
                    f"- {failure.chat_title} ({failure.chat_id}): could not be synced"
                    for failure in result.failures
                )
                message = f"{message}\n\nSync warnings:\n{failures}"
            await self._reply(update, message)

        await self._run_owner_handler(update, "the /sync command", handler)

    async def search(self, update, context):
        async def handler():
            await self._reply(update, await self.assistant.search_messages(args_text(context)))

        await self._run_owner_handler(update, "the /search command", handler)

    async def ask(self, update, context):
        async def handler():
            await self._reply(update, await self.assistant.answer_question(args_text(context)))

        await self._run_owner_handler(update, "the /ask command", handler)

    async def digest(self, update, context):
        async def handler():
            period = args_text(context) or "today"
            await self._reply(update, await self.assistant.digest(period))

        await self._run_owner_handler(update, "the /digest command", handler)

    async def natural_message(self, update, context):
        async def handler():
            text = getattr(update.effective_message, "text", "") or ""
            await self._reply(update, await self.assistant.answer_question(text))

        await self._run_owner_handler(update, "that request", handler)

    @staticmethod
    def help_text() -> str:
        return (
            "Read-only Telegram AI assistant.\n\n"
            "Commands:\n"
            "/track_add <chat> - track a chat or channel\n"
            "/track_remove <chat_or_id> - stop tracking\n"
            "/track_list - list tracked chats\n"
            "/sync - read new messages into the local index\n"
            "/search <query> - search indexed messages\n"
            "/ask <question> - answer from indexed evidence\n"
            "/digest [today|since YYYY-MM-DD] - on-demand digest"
        )


def build_application(bot_token: str, handlers: AssistantBotHandlers):
    from telegram.ext import Application, CommandHandler, MessageHandler, filters

    application = Application.builder().token(bot_token).build()
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help))
    application.add_handler(CommandHandler("track_add", handlers.track_add))
    application.add_handler(CommandHandler("track_remove", handlers.track_remove))
    application.add_handler(CommandHandler("track_list", handlers.track_list))
    application.add_handler(CommandHandler("sync", handlers.sync))
    application.add_handler(CommandHandler("search", handlers.search))
    application.add_handler(CommandHandler("ask", handlers.ask))
    application.add_handler(CommandHandler("digest", handlers.digest))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.natural_message))
    return application
