from telethon import TelegramClient, events
from telethon.tl.types import PeerUser
import asyncio
from dotenv import load_dotenv
import os
import random
from app.parser_database import load_config


load_dotenv()

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
PHONE_NUMBER = os.environ.get("PHONE_NUMBER")
TARGET_USER_ID = int(
    os.environ.get("TARGET_CHAT_ID")
)  # куда пересылать найденные сообщения
KEYWORDS = load_config().get("keywords", [])  # список ключевых слов
CHANNELS = load_config().get("channels", [])
DELAY_MIN = 2
DELAY_MAX = 5
LIMIT_MESSAGES = 10  # сколько сообщений парсить в каждом чате


app = TelegramClient("Telethon_UserBot", API_ID, API_HASH)


def get_message_link(message):
    try:
        if message.link:  # для публичных чатов
            return message.link
    except Exception:
        pass

    if str(message.chat_id).startswith("-100"):  # приватный канал/группа
        return f"https://t.me/c/{str(message.chat_id)[4:]}/{message.id}"
    return "ссылка недоступна"


async def process_message(message):
    """
    message — объект Telethon Message
    """
    chat_id = message.chat_id

    # Собираем текст из всех полей
    message_text = (
        message.text
        or message.message
        or message.raw_text
        or getattr(message, "caption", "")
        or ""
    ).strip()

    print(f"Проверяем сообщение {message.id}: {message.date}")

    # Если это документ/аудио/файл — проверяем имя файла
    if message.media and getattr(message.media, "document", None):
        for attr in message.media.document.attributes:
            if hasattr(attr, "file_name") and attr.file_name:
                message_text += f" [Файл: {attr.file_name}]"

    # Проверка ключевых слов
    if any(
        keyword.lower() in message_text.lower() for keyword in KEYWORDS if message_text
    ):
        clean_text = message_text or "(без текста)"
        message_link = get_message_link(message)

        # Логирование
        log_text = f"[{chat_id}] {clean_text}"
        print(log_text)

        # Сохраняем текст и ссылку
        with open("parsed_messages.txt", "a", encoding="utf-8") as f:
            f.write(f"{log_text} | {message_link}\n")

        # Пробуем переслать
        try:
            await app.forward_messages(
                entity=PeerUser(TARGET_USER_ID), messages=message.id, from_peer=chat_id
            )
            print(f"Сообщение переслано пользователю {TARGET_USER_ID}")
        except Exception as e:
            print(f"Не удалось переслать полностью: {e}")

            # Если есть медиа (включая аудио/документы/видео) — пробуем отправить напрямую
            if message.media:
                try:
                    await app.send_file(
                        PeerUser(TARGET_USER_ID),
                        message.media,
                        caption=(
                            f"{clean_text}\n{message_link}"
                            if clean_text
                            else message_link
                        ),
                    )
                    print("Медиа (включая аудио/файлы) отправлено копированием")
                except Exception as e2:
                    print(f"Ошибка при отправке медиа: {e2}")
            elif clean_text:
                try:
                    await app.send_message(
                        PeerUser(TARGET_USER_ID),
                        f"[{chat_id}] {clean_text}\n{message_link}",
                    )
                    print(f"Текст сообщения отправлен пользователю {TARGET_USER_ID}")
                except Exception as e2:
                    print(f"Ошибка при отправке текста: {e2}")

        # Задержка для безопасности
        await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


@app.on(events.NewMessage(chats=CHANNELS))
async def on_new_message(event):
    if event.out:
        return
    await process_message(event.message)


async def list_all_chats():
    await app.start(phone=PHONE_NUMBER)
    print("Список чатов и каналов:")

    with open("all_chats.txt", "w", encoding="utf-8") as f:
        async for dialog in app.iter_dialogs():
            name = dialog.name
            chat_id = dialog.id
            chat_type = type(dialog.entity).__name__
            line = f"Name: {name}, ID: {chat_id}, Type: {chat_type}"
            print(line)
            f.write(line + "\n")

    print("Список сохранён в all_chats.txt")


async def parser_main():
    await app.start(phone=PHONE_NUMBER)
    await app.run_until_disconnected()
