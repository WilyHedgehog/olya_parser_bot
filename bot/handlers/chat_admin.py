from aiogram import Router
from aiogram.types import ChatMemberUpdated
from aiogram.enums import ChatMemberStatus
from bot_setup import bot
from db.requests import check_user_has_active_subscription
from config.config import load_config

config = load_config()
router = Router(name="chat_admin_bot_router")


@router.chat_member()
async def new_member_handler(event: ChatMemberUpdated):
    if not event.new_chat_member:
        return

    user_id = event.new_chat_member.user.id
    chat_id = event.chat.id
    status = event.new_chat_member.status

    if status in [ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED]:
        if not await check_user_has_active_subscription(user_id):
            try:
                await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                await bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
                print(f"Удалён пользователь {user_id}, нет подписки")
            except Exception as e:
                print(f"Ошибка при удалении пользователя {user_id}: {e}")


async def remove_expired_subscribers(user_id: int):
    try:
        await bot.ban_chat_member(chat_id=config.bot.wacancy_chat_id, user_id=user_id)
        await bot.unban_chat_member(chat_id=config.bot.wacancy_chat_id, user_id=user_id)
        print(f"Удалён пользователь {user_id} с истекшей подпиской")
    except Exception as e:
        print(f"Ошибка при удалении пользователя {user_id}: {e}")