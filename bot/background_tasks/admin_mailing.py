# bot/background_tasks/dunning.py
from datetime import datetime, timedelta
from .broker import broker, schedule_source
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError
import logging
import asyncio
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
    
    reply_markup = await get_mailing_keyboard(keyboard_choice) if keyboard_choice else None
    keyboard_choice = scheduled.keyboard
    file_id = scheduled.file_id
    mailing_text = scheduled.message

    users = await get_all_users_in_segment(scheduled.segment)  # список chat_id пользователей в сегменте

    for user in users:
        try:
            if file_id and keyboard_choice:
                await send_photo(
                    chat_id=user,
                    file_id=file_id,
                    caption=mailing_text,
                    reply_markup=reply_markup
                )
            elif file_id and not keyboard_choice:
                await send_photo(
                    chat_id=user,
                    file_id=file_id,
                    caption=mailing_text
                )
            elif keyboard_choice:
                await send_photo(
                    chat_id=user,
                    file_id=file_id,
                    caption=mailing_text,
                    reply_markup=reply_markup
                )
            else:
                await send_message(
                    chat_id=user,
                    text=mailing_text,
                )
            await asyncio.sleep(0.5)
        except TelegramRetryAfter as e:
            logger.warning(
                f"Flood control, retry in {e.retry_after}s"
            )
            await asyncio.sleep(e.retry_after)  # ждем указанное Telegram время
        
        
        except TelegramForbiddenError:
            # Пользователь заблокировал бота или не начал чат
            logger.warning(
                f"Cannot send vacancy to user: bot is blocked or user hasn't started the chat."
            )
            pass

        except Exception as e:
            logger.error(f"Unexpected error sending vacancy to user: {e}")
            pass 


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