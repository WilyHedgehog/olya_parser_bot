from typing import Callable, Awaitable, Dict, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User, Update, Message, CallbackQuery
from cachetools import TTLCache
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from aiogram.dispatcher.event.handler import HandlerObject
from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram import Bot
import logging

from db.requests import (
    upsert_user,
    check_banned_user,
    get_user_by_telegram_id,
    upsert_user_professions,
    get_all_professions,
    give_three_days_free,
)

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
logging = logging.getLogger(__name__)


class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker):
        super().__init__()
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with self.session_pool() as session:
            data["session"] = session
            return await handler(event, data)


class TrackAllUsersMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.cache = TTLCache(
            maxsize=1000,
            ttl=60 * 60 * 6,  # 6 часов
        )

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        # Определяем пользователя из события
        event_user = None
        if event.message:
            event_user = event.message.from_user
        elif event.callback_query:
            event_user = event.callback_query.from_user
        elif event.inline_query:
            event_user = event.inline_query.from_user
        else:
            return await handler(event, data)
        # Можно добавить другие типы событий, если нужно

        if not event_user:
            return await handler(event, data)

        user_id = event_user.id

        # Обновляем данные пользователя, если его нет в кэше
        if user_id not in self.cache:
            session: AsyncSession = data["session"]
            await upsert_user(
                session=session,
                telegram_id=event_user.id,
                first_name=event_user.first_name,
                last_name=event_user.last_name,
            )
            self.cache[user_id] = None

        return await handler(event, data)


class ShadowBanMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:

        tg_user: User = data.get("event_from_user")
        if not tg_user:
            return await handler(event, data)

        session: AsyncSession = data["session"]
        is_banned = await check_banned_user(session, tg_user.id)

        if is_banned:
            return

        return await handler(event, data)


class FreeThreeDaysMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ):
        # запускаем хэндлер
        result = await handler(event, data)

        # работаем только если это сообщение со /start (учитываем deep link)
        if not event.message or not event.message.text:
            return result

        text = event.message.text
        if not text.startswith("/start"):
            return result

        # извлекаем payload (аргумент после /start)
        payload = text.split(maxsplit=1)[1] if len(text.split(maxsplit=1)) > 1 else None

        event_user = event.message.from_user
        if not event_user:
            return result

        user_id = event_user.id
        user = await get_user_by_telegram_id(user_id)

        # если юзер не найден или уже имеет триал — ничего не делаем
        if not user or user.three_days_free_active in ["active", "used", "used_with", "admin"]:
            return result

        # выдаём три дня
        await give_three_days_free(user_id)

        return result


class UserProfessionsMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        session: AsyncSession = data["session"]

        # Безопасно получаем пользователя
        event_user = data.get("event_from_user")
        if not event_user:
            return await handler(event, data)

        user_id = event_user.id

        all_professions = [prof.id for prof in await get_all_professions()]
        await upsert_user_professions(session, user_id, all_professions)

        return await handler(event, data)


# from aiogram import BaseMiddleware
# from aiogram.types import Update, BotCommand, BotCommandScopeChatMember, User
# from cachetools import TTLCache
# import logging
# from db.requests import get_user_status  # твоя функция из БД

# logger = logging.getLogger(__name__)

# class DynamicCommandsMiddleware(BaseMiddleware):
#     """
#     Middleware для динамических команд Telegram.
#     Обновляет команды пользователя автоматически при событии.
#     """

#     def __init__(self, bot, cache_ttl: int = 3600):
#         super().__init__()
#         self.bot: Bot = bot
#         self.cache = TTLCache(maxsize=5000, ttl=cache_ttl)

#     async def __call__(self, handler, event: Update, data: dict):
#         """
#         Обрабатывает входящее событие.
#         """
#         # Определяем пользователя
#         user: User = None
#         if event.message:
#             user = event.message.from_user
#         elif event.callback_query:
#             user = event.callback_query.from_user
#         elif event.inline_query:
#             user = event.inline_query.from_user

#         if user:
#             await self.update_commands_for_user(user.id)

#         # Продолжаем выполнение хэндлера
#         return await handler(event, data)

#     async def update_commands_for_user(self, user_id: int):
#         """
#         Формируем и устанавливаем команды для конкретного пользователя.
#         """
#         # Получаем статус пользователя из БД
#         status = await get_user_status(user_id)

#         # Формируем список команд
#         commands = [
#             BotCommand(command="start", description="Начать"),
#             BotCommand(command="help", description="Помощь"),
#         ]

#         if status.is_premium:
#             commands.append(BotCommand(command="premium", description="Премиум-функции"))

#         if status.is_admin:
#             commands.extend([
#                 BotCommand(command="admin", description="Админ-панель"),
#                 BotCommand(command="stats", description="Статистика пользователей"),
#             ])

#         # Проверка кэша — обновляем только если команды изменились
#         commands_repr = [(c.command, c.description) for c in commands]
#         cached = self.cache.get(user_id)
#         if cached == commands_repr:
#             return

#         try:
#             await self.bot.set_my_commands(
#                 commands=commands,
#                 scope=BotCommandScopeChatMember(chat_id=user_id, user_id=user_id)
#             )
#             self.cache[user_id] = commands_repr
#             logger.info(f"Команды обновлены для пользователя {user_id}")
#         except Exception as e:
#             logger.error(f"Ошибка при установке команд для пользователя {user_id}: {e}")