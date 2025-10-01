from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from aiogram.types import FSInputFile
from aiogram.fsm.storage.base import StorageKey
from bot_setup import scheduler
from db.requests import update_user_access, get_all_users, update_autopay_status
from datetime import datetime
from zoneinfo import ZoneInfo
from bot_setup import bot, dp, get_bot_id
from lexicon.lexicon import LEXICON_SUBSCRIBE
from bot.states.user import Main
import asyncio
import logging

logger = logging.getLogger(__name__)

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


async def check_subscriptions():
    users = await get_all_users()
    now = datetime.now(MOSCOW_TZ)  # текущее время в МСК
    bot_id = await get_bot_id()
    for user in users:
        try:
            if user.subscription_until:
                # Приводим subscription_until к МСК
                sub_until_msk = (
                    user.subscription_until
                    if user.subscription_until.tzinfo
                    else user.subscription_until.replace(tzinfo=ZoneInfo("UTC"))
                ).astimezone(MOSCOW_TZ)

                if sub_until_msk < now:
                    await update_user_access(user.telegram_id, False)
                    await update_autopay_status(user.telegram_id, False)
                    logger.info(
                        f"User {user.telegram_id} access revoked (subscription expired)."
                    )
                    photo = FSInputFile("bot/assets/Подписка закончилась-1.png")
                    key = StorageKey(bot_id=bot_id, user_id=user.telegram_id, chat_id=user.telegram_id)
                    await dp.storage.set_state(key=key, state=Main.main)
                    message = await bot.send_photo(chat_id=user.telegram_id, photo=photo, caption=LEXICON_SUBSCRIBE["subscription_ended"])
                    await dp.storage.update_data(key=key, data={"reply_id": message.message_id})
                    await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error processing user {user.telegram_id}: {e}")


def start_scheduler(interval_seconds: int = 10):

    scheduler.add_job(
        check_subscriptions,
        trigger=IntervalTrigger(seconds=interval_seconds),
        coalesce=True,
        max_instances=1,
        misfire_grace_time=30,
    )
    scheduler.start()
    logger.info("Subscription check scheduler started.")
