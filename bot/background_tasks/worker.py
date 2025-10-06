import json
import logging
from parser.parser_bot import process_message
from parser.telethon_client import app
from telethon.errors import MessageIdInvalidError

MAX_RETRIES = 3  # Максимальное количество попыток для одной задачи
logger = logging.getLogger(__name__)

async def vacancy_worker(js):
    sub = await js.pull_subscribe("vacancy.queue", durable="vacancy_worker")
    logger.info("🚀 Воркер запущен и слушает очередь 'vacancy.queue'")

    while True:
        try:
            msgs = await sub.fetch(1, timeout=5)
        except Exception:
            continue  # ничего нет, ждём дальше

        for msg in msgs:
            try:
                data = json.loads(msg.data.decode())
                logger.info(f"📥 Получена задача: {data}")

                message_id = data.get("message_id")
                chat_id = data.get("chat_id")
                retries = data.get("retries", 0)

                # Получаем entity через get_input_entity
                try:
                    entity = await app.get_input_entity(chat_id)
                except Exception as e:
                    logger.error(f"❌ Не удалось получить entity для chat_id={chat_id}: {e}")
                    if retries < MAX_RETRIES:
                        data["retries"] = retries + 1
                        await js.publish("vacancy.queue", json.dumps(data).encode())
                    await msg.ack()
                    continue

                # Получаем сообщение
                try:
                    messages = await app.get_messages(entity, ids=[message_id])
                    message = messages[0] if messages else None
                except MessageIdInvalidError:
                    message = None
                except Exception as e:
                    logger.error(f"❌ Ошибка при получении сообщения {message_id} из {chat_id}: {e}")
                    message = None

                if not message:
                    logger.warning(f"❗️ Сообщение {message_id} из чата {chat_id} не найдено")
                    if retries < MAX_RETRIES:
                        data["retries"] = retries + 1
                        await js.publish("vacancy.queue", json.dumps(data).encode())
                    await msg.ack()  # ack чтобы задача не зависла бесконечно
                    continue

                # Обработка сообщения
                await process_message(message)
                await msg.ack()
                logger.info(f"✅ Задача выполнена: {data}")

            except Exception as e:
                logger.error(f"❌ Ошибка обработки задачи: {e}")
                await msg.nak()