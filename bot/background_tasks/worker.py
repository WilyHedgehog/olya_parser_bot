import json
import logging
from parser.parser_bot import process_message

logger = logging.getLogger(__name__)

async def vacancy_worker(app, js):
    sub = await js.pull_subscribe("vacancy.queue", durable="vacancy_worker")
    while True:
        msgs = await sub.fetch(batch=1, timeout=5)
        for msg in msgs:
            try:
                data = json.loads(msg.data.decode())
                message_id = data["message_id"]
                chat_id = data["chat_id"]

                message = await app.get_messages(chat_id, ids=message_id)
                await process_message(message)

                await msg.ack()
                logger.info(f"✅ Вакансия {message_id} обработана")
            except Exception as e:
                logger.error(f"Ошибка обработки задачи: {e}")
                await msg.nak()