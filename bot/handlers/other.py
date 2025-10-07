import logging

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from config.config import load_config
from bot_setup import bot
from db.requests import (
    get_user_by_admin_chat_message_id,
)

config = load_config()
logger = logging.getLogger(__name__)

# Инициализируем роутер уровня модуля
router = Router(name="other router")


@router.message(F.chat.id == config.bot.support_chat_id, F.reply_to_message)
async def support_message_reply_from_admin(message: Message, session: AsyncSession):
    reply_id = message.reply_to_message.message_id
    admin_id = message.from_user.id
    admin_response = message.text
    user_id = await get_user_by_admin_chat_message_id(reply_id)
    
    if user_id:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"💬 Ответ от техподдержки:\n\n{admin_response}",
            )
            await message.reply("✅ Ответ отправлен пользователю.")
        except Exception as e:
            logger.error(f"Ошибка при отправке ответа пользователю {user_id}: {e}")
    else:
        await message.reply("❌ Не удалось найти пользователя для этого сообщения.")