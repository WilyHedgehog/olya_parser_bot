# bot/background_tasks/dunning.py
from datetime import datetime, timedelta
from .broker import broker, schedule_source
from db.crud import (
    delete_old_vacancie_button,
    delete_old_vacancie_list,
    delete_old_vacancie_sent,
    delete_old_vacancie_two_hours,
)
from db.requests import select_two_hours_users
from utils.bot_utils import send_message
from zoneinfo import ZoneInfo
from logging import getLogger
from ..keyboards.admin_keyboard import cancel_task_kb

logger = getLogger(__name__)

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


@broker.task
async def sand_two_hours_vacancy(scheduled_task_id: str):
    try:
        await select_two_hours_users()
    except Exception as e:
        logger.error(e)
        


async def schedule_sand_two_hours():
    await broker.startup()

    # ⏰ Создаём задачу
    await sand_two_hours_vacancy.schedule_by_cron(
        scheduled_task_id="sand_two_hours",
        cron="*/10 * * * *",
        source=schedule_source
    )
    logger.info("✅ Задача рассылки раз в 2 часа создана заново.")
    await send_message(
        chat_id=1058760541,
        text="✅ Задача рассылки раз в 2 часа создана заново.",
        reply_markup=cancel_task_kb("sand_two_hours")
    )

    await broker.shutdown()
    