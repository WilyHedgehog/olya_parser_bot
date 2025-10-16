import re
import hashlib
import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
from telethon.tl.types import (
    MessageEntityBold,
    MessageEntityItalic,
    MessageEntityUnderline,
    MessageEntityStrike,
    MessageEntityCode,
    MessageEntityPre,
    MessageEntityTextUrl,
)
from parser.extract_sender import extract_sender_info


# ==============================
# Pydantic модель сериализации
# ==============================
class MessagePayload(BaseModel):
    id: int = Field(..., description="ID сообщения")
    chat_id: int = Field(..., description="ID чата, откуда пришло сообщение")
    sender_id: Optional[int] = None
    sender_name: Optional[str] = None
    sender_username: Optional[str] = None
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
        """
        entity_name, entity_username, fwd_info = await extract_sender_info(message)

        try:
            sender = await message.get_sender()
            sender_name = getattr(sender, "first_name", None)
            sender_username = getattr(sender, "username", None)
        except Exception:
            sender_name = sender_username = None

        link = get_message_link(message)

        return cls(
            id=message.id,
            chat_id=message.chat_id,
            sender_id=getattr(message.sender_id, "user_id", None)
            or getattr(message, "sender_id", None),
            sender_name=sender_name or entity_name,
            sender_username=sender_username or entity_username,
            text=getattr(message, "message", None)
            or getattr(message, "text", None)
            or getattr(message, "caption", None),
            date=message.date,
            flag=flag,
            link=link,
            forward=bool(getattr(message, "forward", None)),
            fwd_from=" ".join(fwd_info) if message.forward else None,
            raw={
                "entities": [
                    e.to_dict() for e in getattr(message, "entities", []) if hasattr(e, "to_dict")
                ]
                if getattr(message, "entities", None)
                else None
            },
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