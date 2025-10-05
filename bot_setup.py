from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from config.config import load_config
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
API_TOKEN = load_config().bot.token

bot = Bot(
    token=API_TOKEN, 
    session=AiohttpSession(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

def get_db(storage) -> Dispatcher:
    dp = Dispatcher(storage=storage)
    return dp

_bot_id_cache = None  # глобальная переменная для кеша

async def get_bot_id():
    global _bot_id_cache
    if _bot_id_cache is None:
        user = await bot.get_me()
        _bot_id_cache = user.id
    return _bot_id_cache


jobstores = {
    "default": MemoryJobStore()
}
scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="Europe/Moscow")
