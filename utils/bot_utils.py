from bot_setup import bot
from config.config import load_config
from logging import getLogger
from db.requests import (
    get_user_by_admin_chat_message_id,
)

logger = getLogger(__name__)

config = load_config()


async def send_message(chat_id: int, text: str, reply_markup=None):
    """Отправка сообщения с обработкой ошибок"""
    if reply_markup:
        try:
            message_id = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
            return message_id
        except Exception as e:
            # Логируем ошибку, но не поднимаем исключение
            logger.error(f"Ошибка при отправке сообщения в чат {chat_id}: {e}")
    else:
        try:
            message_id = await bot.send_message(chat_id=chat_id, text=text)
            return message_id
        except Exception as e:
            # Логируем ошибку, но не поднимаем исключение
            logger.error(f"Ошибка при отправке сообщения в чат {chat_id}: {e}")
        
        
async def send_file(chat_id: int, file_id: str, caption: str = None):
    """Отправка файла с обработкой ошибок"""
    try:
        message_id = await bot.send_document(chat_id=chat_id, document=file_id, caption=caption)
        return message_id
    except Exception as e:
        # Логируем ошибку, но не поднимаем исключение
        logger.error(f"Ошибка при отправке файла в чат {chat_id}: {e}")


async def send_photo(chat_id: int, photo: str, caption: str = None, reply_markup = None):
    """Отправка фото с обработкой ошибок"""
    if reply_markup:
        try:
            message_id = await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption, reply_markup=reply_markup)
            return message_id
        except Exception as e:
            # Логируем ошибку, но не поднимаем исключение
            logger.error(f"Ошибка при отправке фото в чат {chat_id}: {e}")
    else:
        try:
            message_id = await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption)
            return message_id
        except Exception as e:
            # Логируем ошибку, но не поднимаем исключение
            logger.error(f"Ошибка при отправке фото в чат {chat_id}: {e}")