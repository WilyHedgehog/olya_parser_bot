import logging

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject, Update
import time
from cachetools import TTLCache

from config.config import load_config
from db.requests import get_user_by_telegram_id, get_all_users_professions, get_admins_list

logger = logging.getLogger(__name__)
config = load_config()


admin_cache = TTLCache(maxsize=100, ttl=60)



async def get_admins_cached() -> set[int]:
    """Возвращает кэшированный список админов."""
    if "admin_ids" not in admin_cache:
        admins = await get_admins_list()
        admin_ids = {int(a.telegram_id) for a in admins}
        admin_cache["admin_ids"] = admin_ids
        logger.info("♻️ Кэш списка админов обновлён")
    return admin_cache["admin_ids"]


class IsAdminFilter(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        from_user = getattr(event, "from_user", None)
        if from_user is None:
            logger.debug("Update has no from_user.")
            return False
        user_id = from_user.id
        admin_ids = await get_admins_cached()
        is_admin = user_id in admin_ids
        logger.debug("User ID %s is admin: %s", user_id, is_admin)
        return is_admin


class UserNoEmail(BaseFilter):
    async def __call__(self, update: Update) -> bool:
        from_user = getattr(update, "from_user", None)
        if from_user is None:
            logger.debug("Update has no from_user.")
            return False
        user_id = from_user.id
        user = await get_user_by_telegram_id(user_id)
        if not user:
            logger.debug("User not found.")
            return False
        user_email = user.mail
        is_have_email = user_email is not None
        logger.debug("User email %s is have email: %s", user_email, is_have_email)
        return not is_have_email


class UserHaveEmail(BaseFilter):
    async def __call__(self, update: Update) -> bool:
        from_user = getattr(update, "from_user", None)
        if from_user is None:
            logger.debug("Update has no from_user.")
            return False
        user_id = from_user.id
        user = await get_user_by_telegram_id(user_id)
        if not user:
            logger.debug("User not found.")
            return False
        user_email = user.mail
        is_have_email = user_email is not None
        logger.debug("User email %s is have email: %s", user_email, is_have_email)
        return is_have_email


class UserHaveProfessions(BaseFilter):
    async def __call__(self, update: Update) -> bool:
        from_user = getattr(update, "from_user", None)
        if from_user is None:
            logger.debug("Update has no from_user.")
            return False
        
        user_id = from_user.id
        user_professions = await get_all_users_professions(user_id)
        
        # Проверяем, есть ли выбранные профессии
        has_professions = any(item.is_selected for item in user_professions)

        if not has_professions:
            logger.debug("User has no selected professions.")
        else:
            logger.debug("User has selected professions.")
        
        # Отладка
        logger.debug("User professions %s has professions: %s", user_professions, has_professions)
        
        return has_professions
    

class IsNewUser(BaseFilter):
    async def __call__(self, update: Update) -> bool:
        from_user = getattr(update, "from_user", None)
        if from_user is None:
            logger.debug("Update has no from_user.")
            return False
        user_id = from_user.id
        user = await get_user_by_telegram_id(user_id)
        if not user:
            logger.debug("User not found.")
            return False
        if user.three_days_free_active is None:
            return True