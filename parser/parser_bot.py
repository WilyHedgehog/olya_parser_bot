from telethon import TelegramClient, events
import asyncio
from find_job_process.find_job import find_job_func
import random
from typing import Optional
import re
import hashlib
from config.config import load_config, Config
import logging
from schemas.message_payload import MessagePayload
from db.requests import (
    get_vacancy_by_hash,
    save_vacancy_hash,
    record_vacancy_sent,
    dublicate_check,
    get_vacancy_by_id,
    update_vacancy_hash_admin_chat_url,
)
from schemas.message_payload import MessagePayload
from utils.nats_connect import get_nats_connection
from find_job_process.job_dispatcher import send_vacancy_to_users
from telethon.tl.types import (
    MessageEntityBold,
    MessageEntityItalic,
    MessageEntityCode,
    MessageEntityPre,
    MessageEntityTextUrl,
    MessageEntityUnderline,
    MessageEntityStrike,
)
from bot_setup import bot
from bot.keyboards.admin_keyboard import get_delete_vacancy_kb
from bot.lexicon.lexicon import LEXICON_PARSER
from parser.telethon_client import app
from .extract_sender import extract_sender_info

EXCLUDED_CHAT_IDS = [-1003096281707, 7877140188, -4816957611]


from telethon import events
from telethon.tl.types import User


config = load_config()
logger = logging.getLogger(__name__)



processed_messages = set()



def get_message_link(message):
    try:
        if message.link:  # для публичных чатов
            return message.link
    except Exception:
        pass

    if str(message.chat_id).startswith("-100"):  # приватный канал/группа
        return f"https://t.me/c/{str(message.chat_id)[4:]}/{message.id}"
    return "ссылка недоступна"



def markdown_to_html(text: str) -> str:
    """Преобразует простой markdown-текст в HTML."""
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"_(.*?)_", r"<i>\1</i>", text)
    return text


def message_to_html(text: str, entities: Optional[list] = None) -> str:
    """Добавляет HTML-разметку на основе entities (жирный, курсив, ссылки и т.д.)."""
    if not entities:
        return text

    html = text
    entities = sorted(entities, key=lambda e: e["offset"] + e["length"], reverse=True)
    for ent in entities:
        start, end = ent["offset"], ent["offset"] + ent["length"]
        entity_text = html[start:end]

        match ent.get("_"):
            case "MessageEntityBold":
                html = html[:start] + f"<b>{entity_text}</b>" + html[end:]
            case "MessageEntityItalic":
                html = html[:start] + f"<i>{entity_text}</i>" + html[end:]
            case "MessageEntityUnderline":
                html = html[:start] + f"<u>{entity_text}</u>" + html[end:]
            case "MessageEntityStrike":
                html = html[:start] + f"<s>{entity_text}</s>" + html[end:]
            case "MessageEntityCode":
                html = html[:start] + f"<code>{entity_text}</code>" + html[end:]
            case "MessageEntityPre":
                html = html[:start] + f"<pre>{entity_text}</pre>" + html[end:]
            case "MessageEntityTextUrl":
                url = ent.get("url", "#")
                html = html[:start] + f'<a href="{url}">{entity_text}</a>' + html[end:]

    return html



async def process_message(payload: MessagePayload):
    # 1. Проверка дублей сообщений
    if payload.id in processed_messages:
        logger.info(f"Сообщение {payload.id} уже обработано, пропускаем.")
        return
    processed_messages.add(payload.id)

    # 2. Собираем текст
    message_text = (payload.text or "").strip()
    if not message_text:
        logger.info(f"Сообщение {payload.id} пустое, пропускаем.")
        return

    logger.info(f"Проверяем сообщение {payload.id}: {payload.date}")

    original_link = payload.link or get_message_link(payload)

    message_hash = hashlib.sha256(message_text.encode("utf-8")).hexdigest()


    # 3. Проверка по хэшу в БД
    existing = await get_vacancy_by_hash(message_hash)  # нужно реализовать
    if existing:
        logger.info(
            f"Вакансия с хэшем {message_hash} уже существует (ID {existing.id}), пропускаем."
        )
        return

    # 4. Конвертация текста
    markdown_text = markdown_to_html(message_text)
    html_text = message_to_html(markdown_text, getattr(payload, "entities", None))

    if payload.flag == "Технический специалист онлайн-школ":
        found_proffs = [(payload.flag, 3.0)]
    else:
        found_proffs = await find_job_func(vacancy_text=message_text)
        if not found_proffs:
            logger.info(f"⚠️ Вакансия не подходит ни под одну из профессий: {payload.id}")
            return

    unique_proffs = {prof_name: score for prof_name, score in found_proffs}

    try:
        entity = await app.get_input_entity(payload.chat_id)
        messages = await app.get_messages(entity, ids=[payload.id])
        message = messages[0] if messages else None
    except Exception as e:
        logger.error(f"Ошибка получения сообщения для форварда: {e}")
        message = None
    
    
    link = None
    if message:    
    # 6. Форвард в канал (один раз)
        try:
            forwarded_msg = await app.forward_messages(
                entity=config.bot.wacancy_chat_id,
                messages=message.id,
                from_peer=message.chat_id,
            )
            chat_id = forwarded_msg.chat_id
            msg_id = forwarded_msg.id
            link = f"https://t.me/c/{str(chat_id)[4:]}/{msg_id}"
            logger.info(f"Вакансия переслана в канал: {link}")
        except Exception as e:
            logger.error(f"Ошибка пересылки вакансии: {e}")

    for_admin_prof = {}
    # 7. Сохраняем для каждой профессии
    for prof_name, score in unique_proffs.items():
        vacancy_id = await save_vacancy_hash(
            text=html_text,
            proffname=prof_name,
            score=score,
            url=original_link,
            text_hash=message_hash,
            vacancy_source=payload.sender_name if not payload.sender_username else f"@{payload.sender_username}",
            forwarding_source=payload.fwd_from or "Нет",
        )
        if vacancy_id:
            for_admin_prof[prof_name] = vacancy_id
            logger.info(f"Вакансия по '{prof_name}' сохранена с ID {vacancy_id}")
            await send_vacancy_to_users(vacancy_id)
        else:
            logger.info(f"Вакансия по '{prof_name}' уже существует в БД, пропускаем.")
        #await asyncio.sleep(0.5)
        # 8. Отправляем в админку
    reply = await bot.send_message(
        config.bot.chat_id,
        text=LEXICON_PARSER["vacancy_data"].format(
            profession_name=', '.join(for_admin_prof.keys()),
            vacancy_id=vacancy_id,
            score=score,
            orig_vacancy_link=original_link,
            source=payload.sender_name if not payload.sender_username else f"@{payload.sender_username}",
            vacancy_link=link if link else "Закрытый чат",
            fwd_info=payload.fwd_from or "Нет",
            vacancy_text=html_text,
            sender_link = (
                payload.sender_link
                if payload.sender_link and "ссылка недоступна" not in payload.sender_link.lower()
                else "Ссылка недоступна"
            )
        ),
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=await get_delete_vacancy_kb(vacancy_id),
    )
    await record_vacancy_sent(user_id=config.bot.chat_id, vacancy_id=vacancy_id, message_id=reply.message_id)

    try:
        for prof_name, vacancy_id in for_admin_prof.items():
            await update_vacancy_hash_admin_chat_url(vacancy_id, reply.message_id)
    except Exception as e:
        logger.error(f"Ошибка обновления URL вакансии: {e}")

    await asyncio.sleep(
        random.uniform(config.parser.delay_min, config.parser.delay_max)
    )



@app.on(events.NewMessage())
async def on_new_message(event):
    # Игнорируем исходящие сообщения (наши собственные)
    if event.out or event.chat_id in EXCLUDED_CHAT_IDS:
        return

    try:
        sender = await event.get_sender()
    except Exception as e:
        logger.warning(f"⚠️ Не удалось получить отправителя: {e}")
        sender = None

    # Пропускаем сообщения от ботов
    if isinstance(sender, User) and sender.bot:
        return

    # Пропускаем системные сообщения
    if event.message.action:
        logger.debug("🟡 Системное сообщение — пропускаем")
        return

    # Определяем флаг (если админчат)
    flag = "Технический специалист онлайн-школ" if event.chat_id == -1002962447175 else None
    if flag:
        logger.info(f"🔵 Сообщение из админчата, устанавливаем флаг: {flag}")

    # Подключаемся к NATS
    try:
        nc, js = await get_nats_connection()
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к NATS: {e}")
        return

    # --- ✅ Сериализация Telethon-сообщения ---
    try:
        payload = await MessagePayload.from_telethon(app, event.message, flag)
        json_data = payload.model_dump_json()
    except Exception as e:
        logger.error(f"❌ Ошибка сериализации сообщения: {e}")
        return

    # --- ✅ Публикация в NATS ---
    try:
        await js.publish("vacancy.queue", json_data.encode())
        logger.info(f"📨 Задача добавлена в очередь (сообщение {payload.id})")
    except Exception as e:
        logger.error(f"❌ Ошибка публикации задачи в NATS: {e}")
        
    await asyncio.sleep(0.5)  # Небольшая пауза между задачами




# ==================== Главная функция ====================
async def main():
    await app.start(phone=config.parser.phone_number)
    logger.info("Userbot запущен")

    logger.info("Парсер перешел в режим ожидания новых сообщений...")
    await app.run_until_disconnected()


async def list_all_chats():
    await app.start(phone=config.parser.phone_number)
    logger.info("Список чатов и каналов:")

    with open("all_chats.txt", "w", encoding="utf-8") as f:
        async for dialog in app.iter_dialogs():
            name = dialog.name
            chat_id = dialog.id
            chat_type = type(dialog.entity).__name__
            line = f"Name: {name}, ID: {chat_id}, Type: {chat_type}"
            print(line)
            f.write(line + "\n")

    logger.info("Список сохранён в all_chats.txt")


if __name__ == "__main__":
    try:
        # asyncio.run(list_all_chats())
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Userbot остановлен")
