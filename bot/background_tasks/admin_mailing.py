# bot/background_tasks/dunning.py
from datetime import datetime, timedelta
from .broker import broker, schedule_source
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError
import logging
import json
from utils.nats_connect import get_nats_connection
from db.crud import (\
    create_admin_mailing,
    mark_admin_mailing_executed,
    set_admin_mailing_taskiq_id,
    get_admin_mailing,
    get_all_users_in_segment,
)
from utils.bot_utils import send_message, send_photo
from bot.keyboards.add_mail_keyboard import get_mailing_keyboard
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
logger = logging.getLogger(__name__)


@broker.task
async def admin_mailing(scheduled_task_id: int, ):
    logger.info(f"admin_mailing called with scheduled_task_id={scheduled_task_id}")
    """
    Воркeром выполняется эта функция. Она получает id записи в БД,
    проверяет флаг cancelled и только потом шлёт сообщение.
    """
    scheduled = await get_admin_mailing(scheduled_task_id)
    if not scheduled:
        return  # нет записи — ничего делать
    if scheduled.cancelled:
        return  # пользователь отменил — выходим
    if scheduled.executed:
        return  # уже выполнено
    
    keyboard_choice = scheduled.keyboard
    reply_markup = await get_mailing_keyboard(keyboard_choice) if keyboard_choice else None
    file_id = scheduled.file_id
    mailing_text = scheduled.message

    users = await get_all_users_in_segment(scheduled.segment)  # список chat_id пользователей в сегменте

    
    try:
        nc, js = await get_nats_connection()
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к NATS: {e}")
        return

    flag = "mailing"
    # Формируем задачу для очереди

    # Отправляем задачу в NATS
    for user in users:
        task = {"chat_id": user, "message": mailing_text, "flag": flag, "file_id": file_id, "reply_markup": reply_markup}
        try:
            await js.publish("bot.send.messages.queue", json.dumps(task).encode())
            logger.info(f"📨 Задача добавлена в очередь: {task}")
        except Exception as e:
            logger.error(f"❌ Ошибка публикации задачи в NATS: {e}")



    # пометить как выполненное
    await mark_admin_mailing_executed(scheduled_task_id)


async def set_admin_mailing(mailing_datetime, message, file_id, keyboard, segment, task_name):
    await broker.startup()
    if isinstance(mailing_datetime, str):
        run_time = datetime.fromisoformat(mailing_datetime)
    else:
        run_time = mailing_datetime
    
    # переводим строку в dict
    if isinstance(segment, str):
        segment_dict = {}
        for item in segment.split(","):
            key, value = item.split(":")
            segment_dict[key.strip()] = value.strip().lower() == "true"
        segment = segment_dict

    scheduled = await create_admin_mailing(
        message=message,
        run_at=run_time,
        file_id=file_id,
        keyboard=keyboard,
        segment=segment ,
        task_name=task_name
    )

        # 2) ставим задачу в Taskiq, передаём scheduled.id как аргумент
    task = await admin_mailing.schedule_by_time(
        scheduled_task_id=scheduled.id, time=run_time, source=schedule_source
    )
    await set_admin_mailing_taskiq_id(scheduled.id, task.schedule_id)
        
    await broker.shutdown()