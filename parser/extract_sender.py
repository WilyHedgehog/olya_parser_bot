from telethon.tl.types import Message
import logging
from .telethon_client import app

logger = logging.getLogger(__name__)

async def extract_sender_info(message: Message):
    """
    Возвращает максимально точные данные об отправителе:
    (entity_name, entity_username, fwd_info)
    """
    entity_name = "Неизвестный отправитель"
    entity_username = None
    fwd_info = []

    try:
        # 1️⃣ Пытаемся достать из message.get_sender()
        user = None
        try:
            user = await message.get_sender()
        except Exception as e:
            logger.debug(f"Не удалось получить sender: {e}")

        if user:
            entity_username = getattr(user, "username", None)
            if not entity_username:
                # Попытка получить entity напрямую, если username отсутствует
                try:
                    user_full = await app.get_entity(user.id)
                    entity_username = getattr(user_full, "username", None)
                except Exception as e:
                    logger.debug(f"Не удалось обновить entity для {user.id}: {e}")

            # Формируем имя
            if entity_username:
                entity_name = f"@{entity_username}"
            else:
                entity_name = getattr(user, "first_name", None) or "Неизвестный отправитель"

        # 2️⃣ Если get_sender() ничего не вернул — пробуем по from_id
        elif getattr(message, "from_id", None):
            try:
                entity = await app.get_entity(message.from_id)
                entity_username = getattr(entity, "username", None)
                if entity_username:
                    entity_name = f"@{entity_username}"
                else:
                    entity_name = (
                        getattr(entity, "first_name", None)
                        or getattr(entity, "title", None)
                        or "Неизвестный отправитель"
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
                    else getattr(peer, "title", "Неизвестный отправитель")
                )
            except Exception as e:
                logger.debug(f"Ошибка получения entity по peer_id: {e}")

    except Exception as e:
        logger.warning(f"Ошибка получения отправителя: {e}")

    # -------------------------------------------------------------------
    # 4️⃣ Обрабатываем пересланное сообщение (forward)
    # -------------------------------------------------------------------
    if getattr(message, "forward", None):
        try:
            fwd_username = None
            fwd_name = None
            forward = message.forward

            # Если это переслано от пользователя
            if getattr(forward, "sender", None):
                fwd_user = forward.sender
                fwd_username = getattr(fwd_user, "username", None)
                if not fwd_username:
                    try:
                        fwd_user_full = await app.get_entity(fwd_user.id)
                        fwd_username = getattr(fwd_user_full, "username", None)
                    except Exception:
                        pass
                fwd_name = getattr(fwd_user, "first_name", None) or "Неизвестный пользователь"

            # Если переслано от чата
            elif getattr(forward, "chat", None):
                fwd_chat = forward.chat
                fwd_username = getattr(fwd_chat, "username", None)
                fwd_name = getattr(fwd_chat, "title", None) or "Неизвестный чат"

            # Если переслано через from_id (например, канал без sender/chat)
            elif getattr(forward, "from_id", None):
                try:
                    fwd_entity = await app.get_entity(forward.from_id)
                    fwd_username = getattr(fwd_entity, "username", None)
                    fwd_name = (
                        getattr(fwd_entity, "first_name", None)
                        or getattr(fwd_entity, "title", None)
                        or "Неизвестный источник"
                    )
                except Exception:
                    fwd_name = "Неизвестный источник"

            # Финальный выбор приоритета
            if fwd_username:
                fwd_info.append(f"@{fwd_username}")
            elif fwd_name:
                fwd_info.append(fwd_name)
            else:
                fwd_info.append("Неизвестный источник")

        except Exception as e:
            logger.info(f"Ошибка обработки forward: {e}")
            fwd_info = ["Неизвестный источник"]

    # -------------------------------------------------------------------
    # Финальный возврат
    # -------------------------------------------------------------------
    if not entity_name:
        entity_name = "Неизвестный отправитель"
    if not entity_username:
        entity_username = None
    if not fwd_info:
        fwd_info = ["Без пересылки"]

    return entity_name, entity_username, fwd_info