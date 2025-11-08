import json
import logging
import asyncio
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError
from utils.bot_utils import send_message, send_photo
from db.requests import record_vacancy_sent, get_vacancy_by_id, dublicate_check, mark_vacancies_as_sent_two_hours, mark_vacancy_as_sent_queue
from bot.keyboards.user_keyboard import get_need_author_kb
from uuid import UUID

logger = logging.getLogger(__name__)

semaphore = asyncio.Semaphore(1)

import re
from html import escape

def safe_html(text: str) -> str:
    """Экранирует любые непарные или неизвестные HTML-теги."""
    allowed_tags = ['b', 'i', 'u', 'a', 'code', 'pre', 'blockquote', 'tg-spoiler']
    # заменяем любые угловые скобки, кроме разрешённых тегов
    def repl(match):
        tag = match.group(1)
        if tag and any(tag.startswith(t) for t in allowed_tags):
            return f"<{tag}>"
        return escape(f"<{tag}>")
    return re.sub(r'<(/?[^>]+)>', repl, text)


async def bot_send_messages_worker(js):
    sub = await js.pull_subscribe(
        "bot.send.messages.queue", durable="bot_send_messages_worker"
    )
    logger.info("🚀 Воркер запущен и слушает очередь 'bot.send.messages.queue'")

    while True:
        try:
            msgs = await sub.fetch(1, timeout=5)
        except Exception:
            continue  # ничего нет, ждём дальше

        for msg in msgs:
            async with semaphore:
                success = False
                try:
                    data = json.loads(msg.data.decode())

                    chat_id = data.get("chat_id")
                    logger.info(f"📥 Получена задача для отправки сообщения: {chat_id}")
                    message = data.get("message")
                    flag = data.get("flag")
                    retry_count = data.get("retry_count", 0)

                    try:
                        photo_id = data.get("photo_id")
                    except KeyError:
                        photo_id = None

                    if flag in ["queue", "two_hours", "vacancy"]:
                        logger.info(f"📨 Отправка вакансии пользователю: {chat_id}")
                        vacancy_id = UUID(data.get("vacancy_id"))
                        reply_markup = await get_need_author_kb(str(vacancy_id))
                        
                        vacancy = await get_vacancy_by_id(vacancy_id)
                        
                        if not await dublicate_check(chat_id, vacancy):
                            success = True
                            await msg.ack()
                            logger.info(f"⏭  Skip duplicate vacancy for user: {chat_id}")
                            if flag == "two_hours":
                                await mark_vacancies_as_sent_two_hours(chat_id, vacancy_id)
                            elif flag == "queue":
                                await mark_vacancy_as_sent_queue(chat_id, vacancy_id)
                            continue  # Уже отправляли такую вакансию этому пользователю
                    else:
                        try:
                            reply_markup = data.get("reply_markup")
                        except KeyError:
                            reply_markup = None
                    

                    # Отправляем сообщение
                    try:
                        clean_message = safe_html(message) if message else ""
                        
                        if photo_id:
                            message = await send_photo(
                                chat_id=chat_id,
                                photo=photo_id,
                                caption=clean_message,
                                reply_markup=reply_markup,
                            )
                        else:
                            message_sent = await send_message(
                                chat_id=chat_id, text=clean_message, reply_markup=reply_markup
                            )

                        if flag in ["queue", "two_hours", "vacancy"] and message_sent:
                            await record_vacancy_sent(
                                user_id=chat_id,
                                vacancy_id=vacancy_id,
                                message_id=message_sent.message_id,
                            )
                            if flag == "queue":
                                await mark_vacancy_as_sent_queue(chat_id, vacancy_id)
                            elif flag == "two_hours":
                                await mark_vacancies_as_sent_two_hours(chat_id, vacancy_id)
                                
                        success = True

                    except TelegramRetryAfter as e:
                        logger.warning(f"Flood control, retry in {e.retry_after}s")
                        await asyncio.sleep(e.retry_after)
                        if retry_count < 3:
                            data["retry_count"] = retry_count + 1
                            await js.publish(
                                "bot.send.messages.queue", json.dumps(data).encode()
                            )
                        else:
                            logger.error(
                                f"Max retries reached for message to chat_id={chat_id}"
                            )
                            success = True  # Stop retrying

                    except TelegramForbiddenError:
                        # Пользователь заблокировал бота или не начал чат
                        logger.warning(
                            f"Cannot send vacancy to user: bot is blocked or user hasn't started the chat."
                        )
                        success = True  # Подтверждаем обработку сообщения, чтобы не пытаться снова

                    except Exception as e:
                        logger.error(f"Unexpected error sending vacancy to user: {e}")

                    if success:
                        await msg.ack()
                        logger.info(f"📝 Задача выполнена")
                    else:
                        await msg.nak()

                    # Подтверждаем обработку сообщения
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Ошибка при обработке сообщения: {e}")
                    await msg.ack()
