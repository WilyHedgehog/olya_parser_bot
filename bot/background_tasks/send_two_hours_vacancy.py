from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from aiogram.types import FSInputFile
from aiogram.fsm.storage.base import StorageKey
from bot_setup import scheduler
from apscheduler.triggers.cron import CronTrigger

from zoneinfo import ZoneInfo
from bot_setup import bot, dp, get_bot_id
from bot.lexicon.lexicon import LEXICON_SUBSCRIBE
from bot.states.user import Main
import asyncio
import logging
from find_job_process.job_dispatcher import send_two_hours_vacancies

logger = logging.getLogger(__name__)

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def start_scheduler_two_hours_vacancy_send():
    if not any(job.id == "two_hours_vacancy" for job in scheduler.get_jobs()):
        trigger = CronTrigger(minute=0, hour="0-23/2", timezone=MOSCOW_TZ)
        scheduler.add_job(
            send_two_hours_vacancies,
            trigger=trigger,
            id="two_hours_vacancy",
            coalesce=True,
            max_instances=1,
            misfire_grace_time=60
        )
    logger.info("Two hours vacancy scheduler task added.")