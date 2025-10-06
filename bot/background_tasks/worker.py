import json
import logging
from parser.parser_bot import process_message
from parser.telethon_client import app
from telethon.tl.types import InputPeerChannel, PeerChannel

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

                # Получаем entity
                try:
                    entity = await app.get_entity(chat_id)
                except Exception as e:
                    logger.error(f"❌ Не удалось получить entity для chat_id={chat_id}: {e}")
                    await msg.nak()
                    continue

                # Получаем сообщение
                try:
                    message = await app.get_messages(entity, ids=message_id)
                except Exception as e:
                    logger.error(f"❌ Не удалось получить сообщение {message_id} из {chat_id}: {e}")
                    await msg.nak()
                    continue

                if not message:
                    logger.warning(f"⚠️ Сообщение {message_id} из чата {chat_id} не найдено")
                    await msg.nak()
                    continue

                await process_message(message)
                await msg.ack()
                logger.info(f"✅ Задача выполнена: {data}")

            except Exception as e:
                logger.error(f"❌ Ошибка обработки задачи: {e}")
                await msg.nak()