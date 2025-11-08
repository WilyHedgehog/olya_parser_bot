import json
import logging
import asyncio
from parser.parser_bot import process_message
from parser.telethon_client import app
from telethon.errors import MessageIdInvalidError
from schemas.message_payload import MessagePayload

MAX_RETRIES = 3  # Максимальное количество попыток для одной задачи
logger = logging.getLogger(__name__)

async def hh_vacancy_worker(js):
    sub_hh = await js.pull_subscribe("hh.vacancy.queue", durable="hh_vacancy_worker")

    logger.info("🚀 Воркер запущен и слушает очереди 'vacancy.queue' и 'hh.vacancy.queue'")

    while True:
        try:
            msgs_hh = await sub_hh.fetch(1, timeout=5)
        except Exception:
            msgs_hh = []

        for msg in msgs_hh:
            try:
                data = json.loads(msg.data.decode())
                hh_message = data.get("message")
                proffession = data.get("profession")

                if hh_message:
                    logger.info("📥 Получена HH-вакансия")
                    await process_message(hh_message=hh_message, flag=proffession)
                    await msg.ack()
                    logger.info("✅ HH-вакансия успешно обработана")
                else:
                    logger.warning("⚠️ Пустое сообщение HH, пропускаем")
                    await msg.ack()

            except Exception as e:
                logger.error(f"❌ Ошибка обработки HH-вакансии: {e}")
                await msg.nak()

        #await asyncio.sleep(0.5)  # небольшая пауза между циклами