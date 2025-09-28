# job_dispatcher.py
import logging
import zoneinfo
from datetime import datetime, timedelta
from uuid import UUID
import asyncio
from bot_setup import scheduler

from bot_setup import bot

from db.models import Vacancy

from db.requests import (
    get_users_by_profession,
    record_vacancy_sent,
    cleanup_old_data,
    get_vacancy_by_id,
    add_to_vacancy_queue,
    dublicate_check,
    get_unsent_vacancies_by_user,
    mark_vacancies_as_sent,
)

logger = logging.getLogger(__name__)

TZ_MOSCOW = zoneinfo.ZoneInfo("Europe/Moscow")

_last_scheduled_time: datetime | None = None


def get_next_even_hour() -> datetime:
    now = datetime.now(TZ_MOSCOW)
    # округляем к следующему часу
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    # если час нечётный -> прибавляем ещё 1
    if next_hour.hour % 2 != 0:
        next_hour += timedelta(hours=1)
    return next_hour



async def schedule_two_hours_vacancy(user_id: int, vacancy):
    global _last_scheduled_time

    # Если нет предыдущей задачи или она уже прошла — ставим на следующий чётный час
    if _last_scheduled_time is None or _last_scheduled_time < datetime.now(TZ_MOSCOW):
        run_time = get_next_even_hour()
    else:
        # Каждая следующая задача сдвигается на +1 сек после последней
        run_time = _last_scheduled_time + timedelta(seconds=1)

    _last_scheduled_time = run_time

    scheduler.add_job(
        send_delayed_vacancy,
        trigger="date",
        run_date=run_time,
        args=[user_id, vacancy],
        id=f"two_hours_{user_id}_{vacancy.id}_{int(run_time.timestamp())}",
        replace_existing=False,  # не перезаписываем предыдущие
    )



# --- 2. Отправка вакансии пользователю ---
async def send_vacancy(user_id: int, vacancy: Vacancy):

    if await dublicate_check(user_id, vacancy):
        try:
            message = await bot.send_message(user_id, vacancy.text, disable_web_page_preview=True)
            logger.info(f"message_id: {message.message_id}")
            await record_vacancy_sent(user_id=user_id, vacancy_id=vacancy.id, message_id=message.message_id)
        except Exception as e:
            logger.error(f"Error sending vacancy to user {user_id}: {e}")
        logger.info(f"Vacancy sent to user {user_id}")
    else:
        logger.info(f"Vacancy already sent to user {user_id}, skipping.")

    await asyncio.sleep(1)  # чтобы не спамить слишком быстро


# --- 4. Отправка вакансии всем пользователям с учётом delivery_mode ---
async def send_vacancy_to_users(vacancy_id: UUID):
    vacancy = await get_vacancy_by_id(vacancy_id)
    if not vacancy:
        logger.error(f"Vacancy {vacancy_id} not found.")
        return
    users = await get_users_by_profession(vacancy.profession_id)

    for user in users:
        if user.delivery_mode == "instant":
            await send_vacancy(user.telegram_id, vacancy)

        elif user.delivery_mode == "two_hours":
            await schedule_two_hours_vacancy(user.telegram_id, vacancy)

        elif user.delivery_mode == "button_click":
            await add_to_vacancy_queue(text=vacancy.text, user_id=user.telegram_id, profession_id=vacancy.profession_id)

# --- 5. Отложенная отправка для two_hours ---
async def send_delayed_vacancy(user_id: int, vacancy: Vacancy):
    await send_vacancy(user_id, vacancy)


# --- 6. Отправка по кнопке (button_click) ---
async def send_vacancy_from_queue(user_id: int):
    result = await get_unsent_vacancies_by_user(user_id)
    if not result:
        await bot.send_message(user_id, "Нет накопленных вакансий.")
        logger.info(f"No queued vacancies for user {user_id}.")
        return

    sent_ids = []
    for item in result:
        await send_vacancy(user_id, item)  # Отправка самой вакансии
        sent_ids.append(item.id)           # Сохраняем id для апдейта

    # Помечаем как отправленные
    await mark_vacancies_as_sent(user_id, sent_ids)
    logger.info(f"All queued vacancies sent to user {user_id}.")

# --- 8. Планировщик для регулярной очистки ---
def start_cleanup_scheduler(interval_hours: int = 24):
    scheduler.add_job(
        cleanup_old_data,
        trigger="interval",
        hours=interval_hours,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=60,
    )
    logger.info("Cleanup scheduler started.")
