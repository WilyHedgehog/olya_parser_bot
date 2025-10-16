from telethon.tl.types import Message
import logging
from .telethon_client import app

logger = logging.getLogger(__name__)

async def extract_sender_info(message: Message):
    """
    Возвращает максимально точные данные об отправителе:
    (entity_name, entity_username, fwd_info)
    """
    entity_name = "Unknown"
    entity_username = None
    fwd_info = []

    try:
        # 1️⃣ Пробуем достать из message.get_sender()
        user = await message.get_sender()

        if user:
            entity_username = getattr(user, "username", None)
            if not entity_username:
                # Если username не был загружен, пробуем заново получить entity
                try:
                    user_full = await app.get_entity(user.id)
                    entity_username = getattr(user_full, "username", None)
                except Exception as e:
                    logger.debug(f"Не удалось обновить entity для {user.id}: {e}")

            # Имя ставим в любом случае, но username — приоритетный
            entity_name = (
                f"@{entity_username}"
                if entity_username
                else (getattr(user, "first_name", None) or "Unknown")
            )

        # 2️⃣ Если get_sender() ничего не вернул — пробуем по from_id
        elif getattr(message, "from_id", None):
            try:
                entity = await app.get_entity(message.from_id)
                entity_username = getattr(entity, "username", None)
                if not entity_username:
                    # Иногда entity может быть чатом без username — fallback
                    entity_username = None
                entity_name = (
                    f"@{entity_username}"
                    if entity_username
                    else getattr(entity, "first_name", None)
                    or getattr(entity, "title", "Unknown")
                )
            except Exception as e:
                logger.debug(f"Ошибка получения entity по from_id: {e}")

        # 3️⃣ Если и from_id нет — fallback на peer_id (чат/канал)
        elif getattr(message, "peer_id", None):
            try:
                peer = await app.get_entity(message.peer_id)
                entity_username = getattr(peer, "username", None)
                entity_name = (
                    f"@{entity_username}"
                    if entity_username
                    else getattr(peer, "title", "Unknown")
                )
            except Exception as e:
                logger.debug(f"Ошибка получения entity по peer_id: {e}")

    except Exception as e:
        logger.warning(f"Ошибка получения отправителя: {e}")

    # -------------------------------------------------------------------
    # 4️⃣ Обрабатываем пересланное сообщение
    # -------------------------------------------------------------------
    if message.forward:
        try:
            # 🔹 Сначала пытаемся получить username оригинального отправителя
            fwd_username = None
            fwd_name = None

            if message.forward.sender:
                fwd_user = message.forward.sender
                fwd_username = getattr(fwd_user, "username", None)
                if not fwd_username:
                    try:
                        fwd_user_full = await app.get_entity(fwd_user.id)
                        fwd_username = getattr(fwd_user_full, "username", None)
                    except Exception:
                        pass
                fwd_name = fwd_user.first_name or "Unknown User"

            elif message.forward.chat:
                fwd_chat = message.forward.chat
                fwd_username = getattr(fwd_chat, "username", None)
                fwd_name = getattr(fwd_chat, "title", "Unknown Chat")

            elif getattr(message.forward, "from_id", None):
                try:
                    fwd_entity = await app.get_entity(message.forward.from_id)
                    fwd_username = getattr(fwd_entity, "username", None)
                    fwd_name = (
                        getattr(fwd_entity, "first_name", None)
                        or getattr(fwd_entity, "title", "Unknown")
                    )
                except Exception:
                    fwd_name = "Неизвестный источник"

            # Итог: приоритет username > name > fallback
            if fwd_username:
                fwd_info.append(f"@{fwd_username}")
            elif fwd_name:
                fwd_info.append(fwd_name)
            else:
                fwd_info.append("Неизвестный источник")

        except Exception as e:
            logger.info(f"Ошибка обработки forward: {e}")
            fwd_info = ["Неизвестный источник"]

    return entity_name, entity_username, fwd_info