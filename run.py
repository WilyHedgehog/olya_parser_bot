import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from aiogram import Dispatcher
from app.bot_instance import bot, scheduler
from app.user import user
from app.admin import admin
from app.parser import parser_main

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

dp = Dispatcher()




async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    dp.include_routers(admin, user)
    await dp.start_polling(bot)
    scheduler.start()


if __name__ == "__main__":
    try:
        asyncio.run(parser_main())
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
