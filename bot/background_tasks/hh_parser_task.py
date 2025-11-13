# bot/background_tasks/hh_parser_task.py
from .broker import broker, schedule_source
from utils.bot_utils import send_message
from zoneinfo import ZoneInfo
from logging import getLogger
from parser.hh_parser import hh_parser

logger = getLogger(__name__)

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


@broker.task
async def hh_parser_task(scheduled_task_id: str):
    try:
        logger.info("🔹 hh_parser_task стартовала")
        await hh_parser()
        logger.info("✅ hh_parser_task завершена")
    except Exception as e:
        logger.error(e)
        


async def schedule_hh_parser_task():
    await broker.startup()

    # ⏰ Создаём задачу
    await hh_parser_task.schedule_by_cron(
        scheduled_task_id="hh_parser_task",
        cron="0 */8 * * *",
        source=schedule_source
    )
    logger.info("✅ Задача парсинга hh создана заново.")
    await send_message(
        chat_id=1058760541,
        text="✅ Задача парсинга hh создана заново."
    )

    await broker.shutdown()