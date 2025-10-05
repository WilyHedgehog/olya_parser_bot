import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from aiogram.types import FSInputFile
from aiogram.fsm.storage.base import StorageKey
from bot_setup import bot, get_bot_id
from bot.lexicon.lexicon import LEXICON_SUBSCRIBE
from bot.states.user import Main

from db.requests import get_all_users, update_user_access, update_autopay_status
from find_job_process.job_dispatcher import send_two_hours_vacancies

logger = logging.getLogger(__name__)
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)

# ------------------ Task 1: Check subscriptions ------------------ #
async def check_subscriptions():
    users = await get_all_users()
    now = datetime.now(MOSCOW_TZ)

    bot_id = await get_bot_id()

    for user in users:
        try:
            logger.info(f"Checking subscription for user {user.first_name} ({user.telegram_id})")

            if not user.subscription_until:
                continue

            # Если в базе нет tzinfo, считаем, что время в МСК
            sub_until_msk = (
                user.subscription_until
                if user.subscription_until.tzinfo
                else user.subscription_until.replace(tzinfo=MOSCOW_TZ)
            )

            if sub_until_msk < now:
                logger.info(f"User {user.telegram_id} subscription expired, revoking access.")
                await update_user_access(user.telegram_id, False)
                await update_autopay_status(user.telegram_id, False)

                photo = FSInputFile("bot/assets/Подписка закончилась-1.png")
                key = StorageKey(bot_id=bot_id, user_id=user.telegram_id, chat_id=user.telegram_id)
                #await dp.storage.set_state(key=key, state=Main.main)
                message = await bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=photo,
                    caption=LEXICON_SUBSCRIBE["subscription_ended"]
                )
                #await dp.storage.update_data(key=key, data={"reply_id": message.message_id})
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.exception(f"Error processing user {user.telegram_id}: {e}")


def start_subscription_scheduler(interval_seconds: int = 1800):
    job_id = "check_subscriptions"

    if not any(job.id == job_id for job in scheduler.get_jobs()):
        scheduler.add_job(
            check_subscriptions,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id=job_id,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=30,
        )
        logger.info("Subscription check scheduler started.")


# ------------------ Task 2: Send two hours vacancies ------------------ #
def start_two_hours_vacancy_scheduler():
    job_id = "two_hours_vacancy"

    if not any(job.id == job_id for job in scheduler.get_jobs()):
        scheduler.add_job(
            send_two_hours_vacancies,  # async функция
            trigger=IntervalTrigger(hours=2, start_date=datetime.now(MOSCOW_TZ)),
            id=job_id,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=60,
        )
        logger.info("Two hours vacancy scheduler task added.")


# ------------------ Start scheduler ------------------ #
def start_all_schedulers():
    start_subscription_scheduler()
    start_two_hours_vacancy_scheduler()
    scheduler.start()
    logger.info("All schedulers started.")