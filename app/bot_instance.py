from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore



load_dotenv()


bot = Bot(
    token=os.environ.get("BOT_TOKEN"),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

jobstores = {
    "default": MemoryJobStore()
}
scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="Europe/Moscow")
