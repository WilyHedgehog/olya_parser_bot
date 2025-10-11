from bot_setup import bot
from config.config import load_config
from logging import getLogger
from db.requests import (
    get_user_by_admin_chat_message_id,
)

logger = getLogger(__name__)

config = load_config()


async def send_message(chat_id: int, text: str):
    """Отправка сообщения с обработкой ошибок"""
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        # Логируем ошибку, но не поднимаем исключение
        logger.error(f"Ошибка при отправке сообщения в чат {chat_id}: {e}")