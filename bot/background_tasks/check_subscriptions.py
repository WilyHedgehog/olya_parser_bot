from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from bot_setup import scheduler
from db.requests import update_user_access, get_all_users
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


async def check_subscriptions():
    users = await get_all_users()
    now = datetime.now(MOSCOW_TZ)  # текущее время в МСК

    for user in users:
        if user.subscription_until:
            # Приводим subscription_until к МСК
            sub_until_msk = (
                user.subscription_until
                if user.subscription_until.tzinfo
                else user.subscription_until.replace(tzinfo=ZoneInfo("UTC"))
            ).astimezone(MOSCOW_TZ)

            if sub_until_msk < now:
                await update_user_access(user.telegram_id, False)
                logger.info(
                    f"User {user.telegram_id} access revoked (subscription expired)."
                )

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