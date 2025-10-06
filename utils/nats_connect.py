import nats
from nats.aio.client import Client
from nats.js import JetStreamContext
from nats.js.api import StreamConfig, RetentionPolicy
from logging import getLogger
from config.config import load_config
import asyncio
config = load_config()

logger = getLogger(__name__)

 
_nc: Client | None = None
_js: JetStreamContext | None = None
_lock = asyncio.Lock()


async def get_nats_connection() -> tuple[Client, JetStreamContext]:
    """
    Возвращает существующее подключение к NATS или создаёт новое.
    Безопасно для многопоточного (async) доступа.
    """
    global _nc, _js

    async with _lock:
        # Если уже подключен и соединение живое — возвращаем его
        if _nc and _nc.is_connected:
            return _nc, _js

        # Иначе создаём новое подключение
        _nc = await nats.connect(config.nats.servers)
        _js = _nc.jetstream()
        return _nc, _js


async def close_nats_connection():
    """Аккуратно закрывает соединение с NATS при завершении бота."""
    global _nc
    if _nc and _nc.is_connected:
        await _nc.close()


async def setup_vacancy_stream(js):
    # Проверим, существует ли уже поток
    streams = await js.streams_info()
    if any(stream.config.name == "VACANCY_TASKS" for stream in streams):
        logger.info("✅ Stream VACANCY_TASKS уже существует")
        return

    await js.add_stream(
        StreamConfig(
            name="VACANCY_TASKS",
            subjects=["vacancy.queue"],
            retention=RetentionPolicy.WORK_QUEUE,
        )
    )
    logger.info("🚀 Stream VACANCY_TASKS создан")