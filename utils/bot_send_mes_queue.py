import json
import logging
import asyncio
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError
from bot_utils import send_message, send_photo
from db.requests import record_vacancy_sent
from uuid import UUID
from aiogram.types import InlineKeyboardMarkup

logger = logging.getLogger(__name__)


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
            success = False
            try:
                data = json.loads(msg.data.decode())
                logger.info(f"📥 Получена задача: {data}")

                chat_id = data.get("chat_id")
                message = data.get("message")
                flag = data.get("flag")
                retry_count = data.get("retry_count", 0)

                try:
                    photo_id = data.get("photo_id")
                except KeyError:
                    photo_id = None

                try:
                    reply_markup_data = data.get("reply_markup")
                    reply_markup = InlineKeyboardMarkup.model_validate(reply_markup_data)
                except KeyError:
                    reply_markup = None

                # Отправляем сообщение
                try:
                    if photo_id:
                        message_id = await send_photo(
                            chat_id=chat_id,
                            photo=photo_id,
                            caption=message,
                            reply_markup=reply_markup,
                        )
                    else:
                        message_id = await send_message(
                            chat_id=chat_id, text=message, reply_markup=reply_markup
                        )

                    if flag == "vacancy":
                        vacancy_id = UUID(data.get("vacancy_id"))
                        await record_vacancy_sent(
                            user_id=chat_id,
                            vacancy_id=vacancy_id,
                            message_id=message_id,
                        )
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
                else:
                    await msg.nak()

                # Подтверждаем обработку сообщения
                await asyncio.sleep(0.4)
            except Exception as e:
                logger.error(f"Ошибка при обработке сообщения: {e}")
                await msg.nak()
