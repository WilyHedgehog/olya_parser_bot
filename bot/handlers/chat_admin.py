from aiogram import F
from aiogram.types import ChatMemberUpdated
from bot_setup import bot
import asyncio
from aiogram import Router

from db.requests import check_user_has_active_subscription
from config.config import load_config
config = load_config()

router = Router(name="chat_admin_bot_router")

@router.chat_member()
async def new_member_handler(event: ChatMemberUpdated):
    user_id = event.from_user.id
    chat_id = event.chat.id
    # Если новый участник или восстановлен
    if event.new_chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED]:
        if not await check_user_has_active_subscription(user_id):
            try:
                await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                await bot.unban_chat_member(chat_id=chat_id, user_id=user_id)  # чтобы мог вернуться после подписки
                print(f"Удалён пользователь {user_id}, нет подписки")
            except Exception as e:
                print(f"Ошибка при удалении пользователя {user_id}: {e}")
                
                
async def remove_expired_subscribers(user_id: int):
    try:
        await bot.ban_chat_member(chat_id=config.bot.wacancy_chat_id, user_id=user_id)
        await bot.unban_chat_member(chat_id=config.bot.wacancy_chat_id, user_id=user_id)  # чтобы мог вернуться после подписки
        print(f"Удалён пользователь {user_id} с истекшей подпиской")
    except Exception as e:
        print(f"Ошибка при удалении пользователя {user_id}: {e}")