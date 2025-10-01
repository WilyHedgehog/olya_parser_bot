from aiogram import Router
from aiogram.enums import ChatMemberStatus
from bot_setup import bot
from db.requests import check_user_has_active_subscription
from config.config import load_config

config = load_config()
router = Router(name="chat_admin_bot_router")

# requirements:
# pip install aiogram pyahocorasick

import logging
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter
from config.config import load_config

config = load_config()


CHANNEL_ID = config.bot.wacancy_chat_id

logger = logging.getLogger(__name__)



@router.chat_member(ChatMemberUpdatedFilter(chat_id=CHANNEL_ID))
async def handle_member_update(update: ChatMemberUpdated):
    user = update.from_user
    new_status = update.new_chat_member.status
    logger.info("Обновление участника: %s, новый статус: %s", user.id, new_status)

    # Только если пользователь стал участником
    if new_status == "member":
        has_acsess = await check_user_has_active_subscription(user.id)
        if has_acsess:
            logger.info("Пользователь %s имеет активную подписку, пропускаем проверку.", user.id)
            return
        else:
            logger.info("Баним пользователя %s без активной подписки.", user.id)
            try:
                await bot.ban_chat_member(chat_id=update.chat.id, user_id=user.id)
                await bot.unban_chat_member(chat_id=update.chat.id, user_id=user.id, only_if_banned=True)
            except Exception as e:
                logger.exception("Ошибка при бане пользователя: %s", e)

# ============================
# Обработка уже присоединившихся (на всякий случай) — chat_member updates
# ============================
@router.chat_member(ChatMemberUpdatedFilter(chat_id=CHANNEL_ID))
async def on_chat_member_update(update: ChatMemberUpdated):
    user = update.from_user
    new_status = update.new_chat_member.status
    old_status = update.old_chat_member.status
    logger.info("Обновление участника: %s, старый статус: %s, новый статус: %s", user.id, old_status, new_status)

    # Проверяем только если пользователь стал участником
    if old_status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED} and new_status == ChatMemberStatus.MEMBER:
        has_acsess = await check_user_has_active_subscription(user.id)
        if has_acsess:
            logger.info("Пользователь %s имеет активную подписку, пропускаем проверку.", user.id)
            return
        else:
            logger.info("Баним пользователя %s без активной подписки.", user.id)
            try:
                await bot.ban_chat_member(chat_id=update.chat.id, user_id=user.id)
                await bot.unban_chat_member(chat_id=update.chat.id, user_id=user.id, only_if_banned=True)
            except Exception as e:
                logger.exception("Ошибка при бане пользователя: %s", e)
                
                
async def remove_expired_subscribers(user_id: int):
    try:
        await bot.ban_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        await bot.unban_chat_member(chat_id=CHANNEL_ID, user_id=user_id, only_if_banned=True)
        logger.info(f"Пользователь {user_id} удалён из канала из-за истечения подписки.")
    except Exception as e:
        logger.exception(f"Ошибка при удалении пользователя {user_id} из канала: {e}")