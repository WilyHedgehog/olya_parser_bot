# bot/background_tasks/dunning.py
from datetime import datetime, timedelta
from .broker import broker, schedule_source
from db.crud import (
    delete_old_vacancie_button,
    delete_old_vacancie_list,
    delete_old_vacancie_sent,
    delete_old_vacancie_two_hours,
)
from utils.bot_utils import send_message
from zoneinfo import ZoneInfo
from logging import getLogger
from ..keyboards.admin_keyboard import cancel_task_kb

logger = getLogger(__name__)

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


@broker.task
async def vacancy_clear_func():
    try:
        await delete_old_vacancie_sent()
        await delete_old_vacancie_button()
        await delete_old_vacancie_two_hours()
        await delete_old_vacancie_list()
        logger.info("Задача удаления старых вакансий выполнена.")
    except Exception as e:
        logger.error(e)
        


async def schedule_vacancy_clear():
    await broker.startup()

    # 🔍 Проверяем, существует ли задача с ID "auto_delete"
    existing_tasks = await schedule_source.get_schedules()
    task_exists = any(t.schedule_id == "auto_delete" for t in existing_tasks)

    if task_exists:
        logger.info("⏸ Задача удаления старых вакансий уже существует, повторное создание пропущено.")
    else:
        # ⏰ Создаём задачу
        await vacancy_clear_func.schedule_by_cron(
            scheduled_task_id="auto_delete",
            cron="30 0 * * *",
            source=schedule_source
        )
        logger.info("✅ Задача удаления старых вакансий создана заново.")
        await send_message(
            chat_id=1058760541,
            text="Задача автоудаления старых вакансий создана.",
            reply_markup=cancel_task_kb("auto_delete")
        )

    await broker.shutdown()
    
    
async def cancel_shedule_vacancy_clear():
    await broker.startup()
    delete = await schedule_source.delete_schedule("auto_delete")
    if delete:
        logger.info("Задача удаления старых вакансий удалена.")
    else:
        logger.info("Задача удаления старых вакансий не удалена.")
    await broker.shutdown()
