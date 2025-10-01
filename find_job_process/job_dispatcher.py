# job_dispatcher.py
import logging
import zoneinfo
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
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
    add_to_two_hours,
    dublicate_check,
    get_unsent_vacancies_by_user,
    get_two_hours_vacancies_by_user,
    mark_vacancy_as_sent,
    mark_vacancies_as_sent_two_hours,
    select_two_hours_users,
)

logger = logging.getLogger(__name__)

TZ_MOSCOW = zoneinfo.ZoneInfo("Europe/Moscow")


# --- 2. Отправка вакансии пользователю ---
async def send_vacancy(user_id: int, vacancy: Vacancy) -> bool:
    if await dublicate_check(user_id, vacancy):
        try:
            message = await bot.send_message(
                user_id, vacancy.text, disable_web_page_preview=True
            )
            print(f"Vacancy sent to user {user_id}, message ID:🥶🥶🥶🥶🥶🥶🥶🥶🥶🥶🥶🥶🥶🥶🥶🥶🥶 {message.message_id}")
            await record_vacancy_sent(
                user_id=user_id, vacancy_id=vacancy.id, message_id=message.message_id
            )
            await asyncio.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error sending vacancy to user {user_id}: {e}")
            return False
    else:
        return False


# --- 4. Отправка вакансии всем пользователям с учётом delivery_mode ---
async def send_vacancy_to_users(vacancy_id: UUID):
    vacancy = await get_vacancy_by_id(vacancy_id)
    if not vacancy:
        logger.error(f"Vacancy {vacancy_id} not found.")
        return

    users = await get_users_by_profession(vacancy.profession_id)

    now_msk = datetime.now(TZ_MOSCOW)

    for user in users:
        # Приводим subscription_until к aware datetime
        if user.subscription_until is None:
            logger.info(f"User {user.telegram_id} subscription expired, skipping.")
            continue

        sub_until = user.subscription_until
        if sub_until.tzinfo is None:
            sub_until = sub_until.replace(
                tzinfo=ZoneInfo("UTC")
            )  # если без tzinfo, считаем UTC
        sub_until = sub_until.astimezone(TZ_MOSCOW)

        if sub_until < now_msk:
            logger.info(f"User {user.telegram_id} subscription expired, skipping.")
            continue

        if user.delivery_mode == "instant":
            await send_vacancy(user.telegram_id, vacancy)
        elif user.delivery_mode == "two_hours":
            await add_to_two_hours(
                text=vacancy.text,
                profession_id=vacancy.profession_id,
                user_id=user.telegram_id,
            )
        elif user.delivery_mode == "button_click":
            await add_to_vacancy_queue(
                text=vacancy.text,
                user_id=user.telegram_id,
                profession_id=vacancy.profession_id,
            )


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

    for item in result:
        sent = await send_vacancy(user_id, item)  # True, если реально отправили
        if sent:
            await mark_vacancy_as_sent(user_id, item.id)


async def send_two_hours_vacancies():
    users = select_two_hours_users()
    sent_ids = []
    for user in users:
        result = await get_two_hours_vacancies_by_user(user.telegram_id)
        if not result:
            logger.info("No two_hours vacancies to send.")
            return

        for item in result:
            await send_vacancy(user.telegram_id, item)  # Отправка самой вакансии
            sent_ids.append(item.id)  # Сохраняем id для апдейта

        await mark_vacancies_as_sent_two_hours(user.telegram_id, sent_ids)
        logger.info(f"All two_hours vacancies sent to user {user.telegram_id}.")


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
