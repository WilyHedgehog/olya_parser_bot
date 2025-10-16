import json
import logging
import asyncio
from parser.parser_bot import process_message
from parser.telethon_client import app
from telethon.errors import MessageIdInvalidError
from schemas.message_payload import MessagePayload

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
                # --- ✅ Декодируем и валидируем payload ---
                payload = MessagePayload.model_validate_json(msg.data.decode())
                logger.info(f"📥 Получена задача на обработку сообщения {payload.id} из чата {payload.chat_id}")

                # --- ✅ Обрабатываем сообщение напрямую ---
                await process_message(payload)

                # --- ✅ Подтверждаем задачу ---
                await msg.ack()
                logger.info(f"✅ Задача успешно выполнена: message_id={payload.id}")

            except Exception as e:
                logger.error(f"❌ Ошибка обработки задачи: {e}")
                await msg.nak()
        #await asyncio.sleep(0.5)  # Небольшая пауза между задачами