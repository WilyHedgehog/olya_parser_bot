# job_dispatcher.py
import logging
import zoneinfo
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from uuid import UUID
import asyncio
from bot_setup import scheduler
from bot_setup import bot
from bot.lexicon.lexicon import LEXICON_PARSER
from bot.keyboards.user_keyboard import get_need_author_kb
from utils.nats_connect import get_nats_connection
import json

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
    get_vacancy_by_text,
)

logger = logging.getLogger(__name__)

TZ_MOSCOW = zoneinfo.ZoneInfo("Europe/Moscow")


from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError


# --- 2. Отправка вакансии пользователю ---
async def send_vacancy(user_id: int, vacancy: Vacancy, url=None, msg_type=None) -> bool:
    #print("🔔 Подготовка к отправке вакансии пользователю:", user_id)
    if not await dublicate_check(user_id, vacancy):
        return False  # Уже отправляли такую вакансию этому пользователю
    #print("🤖 Отправка вакансии пользователю:", user_id)

    if url == True:
        main_vacancy = await get_vacancy_by_text(vacancy.text)
        # vacancy_url = main_vacancy.url
        vacancy_id = main_vacancy.id
        author = main_vacancy.vacancy_source
    else:
        # vacancy_url = vacancy.url
        vacancy_id = vacancy.id
        author = vacancy.vacancy_source

    text = LEXICON_PARSER["msg_for_user"].format(
        author=author if author else "Не указан",
        vacancy_text=vacancy.text,
    )

    if msg_type == None:
        flag = "vacancy"
    elif msg_type == "queue":
        flag = "queue"
    elif msg_type == "two_hours":
        flag = "two_hours"

    try:
        nc, js = await get_nats_connection()
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к NATS: {e}")
        return

    # Формируем задачу для очереди
    task = {
        "chat_id": user_id,
        "message": text,
        "flag": flag,
        "vacancy_id": str(vacancy_id),
    }

    # Отправляем задачу в NATS
    try:
        await js.publish("bot.send.messages.queue", json.dumps(task).encode())
        logger.info(f"📨 Задача добавлена в очередь: {flag} для {user_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка публикации задачи в NATS: {e}")


# --- 4. Отправка вакансии всем пользователям с учётом delivery_mode ---
async def send_vacancy_to_users(vacancy_id: UUID):
    vacancy = await get_vacancy_by_id(vacancy_id)
    if not vacancy:
        logger.error(f"Vacancy {vacancy_id} not found.")
        return

    users = await get_users_by_profession(vacancy.profession_id)

    now_msk = datetime.now(TZ_MOSCOW)

    for user in users:
        #print("👤 Проверка пользователя:", user.telegram_id)
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
            #print("🚀 Instant delivery for user:", user.telegram_id)
            await send_vacancy(user.telegram_id, vacancy)
        elif user.delivery_mode == "two_hours":
            logger.info(
                f"User {user.telegram_id} is using two hours mode🍎"
            )
            await add_to_two_hours(
                text=vacancy.text,
                profession_id=vacancy.profession_id,
                user_id=user.telegram_id,
            )
        elif user.delivery_mode == "button_click":
            #print("⏳ Button click delivery for user:", user.telegram_id)
            await add_to_vacancy_queue(
                text=vacancy.text,
                user_id=user.telegram_id,
                profession_id=vacancy.profession_id,
            )
        elif user.delivery_mode == "support":
            logger.info(
                f"User {user.telegram_id} is using support mode, skipping vacancy."
            )
            pass  # Техподдержка не получает вакансии
        else:
            logger.warning(
                f"Unknown delivery mode '{user.delivery_mode}' for user {user.telegram_id}, skipping."
            )



# --- 6. Отправка по кнопке (button_click) ---
async def send_vacancy_from_queue(user_id: int):
    result = await get_unsent_vacancies_by_user(user_id)
    if not result:
        await bot.send_message(user_id, "Нет накопленных вакансий.")
        logger.info(f"No queued vacancies for user {user_id}.")
        return
    #print("🔔 Подготовка к отправке вакансии пользователю:", user_id)
    for item in result:
        #print(f"🎃 Отправка вакансии {item.id} пользователю:", user_id)
        await send_vacancy(
            user_id, item, url=True, msg_type="queue"
        )


async def send_two_hours_vacancies():
    try:
        users_ids = select_two_hours_users()
        for user_id in users_ids:
            result = await get_two_hours_vacancies_by_user(user_id)
            if not result:
                logger.info("No two_hours vacancies to send.")
                return

            for item in result:
                await send_vacancy(user_id, item, msg_type="two_hours", url=True)

    except Exception as e:
        logger.error(f"Error sending two_hours vacancies: {e}")
