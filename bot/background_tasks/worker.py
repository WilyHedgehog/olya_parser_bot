import json
import logging
from parser.parser_bot import process_message
from parser.telethon_client import app

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
                message_id = data["message_id"]
                chat_id = data["chat_id"]

                message = await app.get_messages(chat_id, ids=message_id)
                await process_message(message)

                await msg.ack()
                logger.info(f"✅ Задача выполнена: {data}")
            except Exception as e:
                logger.error(f"❌ Ошибка обработки задачи: {e}")
                await msg.nak()