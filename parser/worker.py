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
    # Подписки на очереди
    sub_tg = await js.pull_subscribe("vacancy.queue", durable="vacancy_worker")
    sub_hh = await js.pull_subscribe("hh.vacancy.queue", durable="hh_vacancy_worker")

    logger.info("🚀 Воркер запущен и слушает очереди 'vacancy.queue' и 'hh.vacancy.queue'")

    while True:
        # --- Telegram-сообщения ---
        try:
            msgs_tg = await sub_tg.fetch(1, timeout=5)
        except Exception:
            msgs_tg = []

        for msg in msgs_tg:
            try:
                data = json.loads(msg.data.decode())
                payload_data = data.get("payload")
                
                if payload_data:
                    payload = MessagePayload.model_validate_json(msg.data.decode())
                    logger.info(f"📥 Получена задача на обработку сообщения {payload.id} из чата {payload.chat_id}")
                    await process_message(payload=payload)
                    await msg.ack()
                    logger.info(f"✅ Telegram-сообщение обработано: message_id={payload.id}")
                else:
                    logger.warning("⚠️ Пустой payload в Telegram-сообщении, пропускаем")
                    await msg.ack()

            except Exception as e:
                logger.error(f"❌ Ошибка обработки Telegram-сообщения: {e}")
                await msg.nack()

        # --- HH-вакансии ---
        try:
            msgs_hh = await sub_hh.fetch(1, timeout=5)
        except Exception:
            msgs_hh = []

        for msg in msgs_hh:
            try:
                data = json.loads(msg.data.decode())
                hh_message = data.get("message")

                if hh_message:
                    logger.info("📥 Получена HH-вакансия")
                    await process_message(hh_message=hh_message)
                    await msg.ack()
                    logger.info("✅ HH-вакансия успешно обработана")
                else:
                    logger.warning("⚠️ Пустое сообщение HH, пропускаем")
                    await msg.ack()

            except Exception as e:
                logger.error(f"❌ Ошибка обработки HH-вакансии: {e}")
                await msg.nack()

        await asyncio.sleep(0.5)  # небольшая пауза между циклами