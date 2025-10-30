import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
from parser.extract_sender import extract_sender_info
from telethon.errors import TypeNotFoundError


# ==============================
# Pydantic модель сериализации
# ==============================
class MessagePayload(BaseModel):
    id: int = Field(..., description="ID сообщения")
    chat_id: int = Field(..., description="ID чата, откуда пришло сообщение")
    sender_id: Optional[int] = None
    sender_name: Optional[str] = None
    sender_username: Optional[str] = None
    sender_link: Optional[str] = None
    text: Optional[str] = None
    date: Optional[datetime.datetime] = None
    flag: Optional[str] = None
    link: Optional[str] = None
    forward: bool = False
    fwd_from: Optional[str] = None
    raw: Optional[dict[str, Any]] = None  # entities и др. вспомогательные данные

    @classmethod
    async def from_telethon(cls, app, message, flag: Optional[str] = None) -> "MessagePayload":
        """
        Преобразует Telethon message в сериализуемую структуру.
        Игнорирует неизвестные TL-конструкторы и логирует ошибки.
        """
        import logging
        logger = logging.getLogger("parser.parser_bot")

        # Получаем инфо через вспомогательную функцию
        try:
            entity_name, entity_username, fwd_info = await extract_sender_info(message)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось получить инфо отправителя: {e}")
            entity_name = entity_username = None
            fwd_info = []

        # Инициализация переменных
        sender_name = sender_username = sender_id = None

        # Безопасное получение отправителя
        try:
            sender = await message.get_sender()
            sender_name = getattr(sender, "first_name", None)
            sender_username = getattr(sender, "username", None)
            sender_id = getattr(sender, "id", None)
        except TypeNotFoundError as e:
            logger.warning(f"⚠️ TypeNotFoundError при получении sender: {e}")
            sender_id = getattr(message, "sender_id", None)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при получении sender: {e}")
            sender_id = getattr(message, "sender_id", None)

        # Формируем ссылку на сообщение
        link = get_message_link(message)

        if sender_username:
            sender_link = f"https://t.me/{sender_username}"
        elif sender_id:
            sender_link = f"tg://user?id={sender_id}"
        else:
            sender_link = "ссылка недоступна"

        # Безопасное получение entities
        entities = []
        for e in getattr(message, "entities", []) or []:
            try:
                entities.append(e.to_dict())
            except Exception as e:
                logger.warning(f"⚠️ Ошибка сериализации entity: {e}")
                continue

        # Формируем fwd_from
        fwd_from = " ".join(fwd_info) if fwd_info else None

        # Текст сообщения
        text = getattr(message, "message", None) \
            or getattr(message, "text", None) \
            or getattr(message, "caption", None)

        # Дата сообщения
        date = getattr(message, "date", None)

        # Формируем объект
        return cls(
            id=getattr(message, "id", 0),
            chat_id=getattr(message, "chat_id", 0),
            sender_id=sender_id,
            sender_name=sender_name or entity_name,
            sender_username=sender_username or entity_username,
            sender_link=sender_link,
            text=text,
            date=date,
            flag=flag,
            link=link,
            forward=bool(getattr(message, "forward", None)),
            fwd_from=fwd_from,
            raw={"entities": entities or None},
        )


# ==============================
# Вспомогательные функции
# ==============================

def get_message_link(message) -> str:
    """Генерирует ссылку на сообщение в Telegram (публичный или приватный чат)."""
    try:
        if getattr(message, "link", None):  # для публичных чатов
            return message.link
    except Exception:
        pass

    if str(message.chat_id).startswith("-100"):  # приватный канал/группа
        return f"https://t.me/c/{str(message.chat_id)[4:]}/{message.id}"
    return "ссылка недоступна"