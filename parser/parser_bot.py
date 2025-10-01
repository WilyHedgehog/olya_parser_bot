from telethon import TelegramClient, events
import asyncio
from find_job_process.find_job import find_job_func
import random
from config.config import load_config, Config
import logging
from db.requests import save_vacancy
from find_job_process.job_dispatcher import send_vacancy_to_users
from telethon.tl.types import (
    MessageEntityBold,
    MessageEntityItalic,
    MessageEntityCode,
    MessageEntityPre,
    MessageEntityTextUrl,
    MessageEntityUnderline,
    MessageEntityStrike,
)
from bot_setup import bot
from bot.keyboards.admin_keyboard import get_delete_vacancy_kb

config: Config = load_config()
logger = logging.getLogger(__name__)


old_professions = {
    "Технический специалист онлайн-школ": {
        "keywords": {
            "настройка": 0.8,
            "платформа": 0.9,
            "сервисы": 0.7,
            "интеграция": 1.0,
            "тильда": 0.6,
            "getcourse": 1.0,
            "автоматизация": 0.9,
        },
        "desc": "настройка платформ, интеграции сервисов, техническая поддержка онлайн-школ",
    },
    "Специалист по чат-ботам": {
        "keywords": {
            "чат-бот": 1.0,
            "telegram": 0.9,
            "autofunnel": 0.8,
            "интеграции": 0.7,
            "manychat": 0.9,
            "сценарий": 0.6,
        },
        "desc": "разработка и настройка чат-ботов, интеграции, воронки продаж",
    },
    "Веб-разработчик/дизайнер": {
        "keywords": {
            "html": 1.0,
            "css": 1.0,
            "javascript": 0.9,
            "верстка": 0.9,
            "ui": 0.7,
            "ux": 0.7,
            "лендинг": 0.8,
        },
        "desc": "создание сайтов и лендингов, дизайн интерфейсов, работа с веб-технологиями",
    },
    "Дизайнер": {
        "keywords": {
            "баннер": 0.8,
            "презентация": 0.9,
            "photoshop": 1.0,
            "figma": 0.9,
            "иллюстрация": 0.7,
            "дизайн": 1.0,
        },
        "desc": "графический дизайн, работа в Figma и Photoshop, создание визуалов и баннеров",
    },
    "Монтажёр видео": {
        "keywords": {
            "монтаж": 1.0,
            "premiere": 0.9,
            "after effects": 0.9,
            "видеоролик": 0.8,
            "редактирование": 0.7,
            "обрезка": 0.6,
        },
        "desc": "монтаж и обработка видеороликов, работа в Premiere и After Effects",
    },
    "Reels-мейкер": {
        "keywords": {
            "reels": 1.0,
            "shorts": 0.9,
            "тренды": 0.8,
            "обрезка видео": 0.8,
            "инстаграм": 0.9,
            "вертикальное видео": 0.7,
        },
        "desc": "создание коротких видео для Reels и Shorts, тренды, монтаж вертикальных видео",
    },
    "Копирайтер": {
        "keywords": {
            "тексты": 1.0,
            "продающий": 0.9,
            "статья": 0.8,
            "описание": 0.7,
            "пост": 0.9,
            "рекламный текст": 1.0,
        },
        "desc": "написание продающих текстов, статей, рекламных материалов",
    },
    "Контент-менеджер": {
        "keywords": {
            "контент": 1.0,
            "посты": 0.9,
            "планирование": 0.8,
            "редактирование": 0.7,
            "публикация": 0.9,
            "управление контентом": 1.0,
        },
        "desc": "ведение контент-плана, публикация постов, управление материалами",
    },
    "Сценарист вебинаров": {
        "keywords": {
            "сценарий": 1.0,
            "вебинар": 1.0,
            "структура": 0.8,
            "контент": 0.7,
            "презентация": 0.8,
            "выступление": 0.9,
        },
        "desc": "разработка сценариев вебинаров, структурирование информации, подготовка материалов",
    },
    "Продюсер онлайн-школ": {
        "keywords": {
            "продюсер": 1.0,
            "запуск": 0.9,
            "курс": 0.9,
            "воронка": 0.8,
            "стратегия": 0.8,
            "масштабирование": 0.7,
        },
        "desc": "запуск и продюсирование онлайн-курсов, стратегия развития проектов",
    },
    "Проджект онлайн-школ": {
        "keywords": {
            "проект": 1.0,
            "управление": 0.9,
            "координация": 0.9,
            "команда": 0.8,
            "сроки": 0.8,
            "организация": 0.7,
        },
        "desc": "управление проектами онлайн-школы, координация команды, контроль сроков",
    },
    "SMM-специалист": {
        "keywords": {
            "smm": 1.0,
            "соцсети": 0.9,
            "instagram": 0.9,
            "контент": 0.8,
            "таргет": 0.7,
            "аудитория": 0.8,
        },
        "desc": "ведение социальных сетей, работа с контентом, взаимодействие с аудиторией",
    },
    "Маркетолог онлайн-обучений": {
        "keywords": {
            "маркетинг": 1.0,
            "воронка": 0.9,
            "реклама": 0.9,
            "стратегия": 0.8,
            "анализ": 0.8,
            "онлайн-курс": 0.9,
        },
        "desc": "разработка маркетинговых стратегий для онлайн-курсов и школ",
    },
    "Методолог онлайн-обучений": {
        "keywords": {
            "методология": 1.0,
            "обучение": 0.9,
            "курс": 0.9,
            "структура": 0.8,
            "программа": 0.9,
            "педагогика": 0.7,
        },
        "desc": "разработка методологии и структуры онлайн-курсов, создание программ",
    },
    "Таргетолог": {
        "keywords": {
            "таргет": 1.0,
            "facebook ads": 0.9,
            "реклама": 1.0,
            "аудитория": 0.8,
            "кампания": 0.9,
            "трафик": 0.8,
        },
        "desc": "настройка таргетированной рекламы в соцсетях, работа с трафиком",
    },
    "SEO-специалист": {
        "keywords": {
            "seo": 1.0,
            "оптимизация": 0.9,
            "поисковик": 0.8,
            "ключевые слова": 0.9,
            "google": 0.8,
            "продвижение": 0.9,
        },
        "desc": "оптимизация сайтов под поисковые системы, работа с ключевыми словами",
    },
    "Специалист по рассылкам": {
        "keywords": {
            "рассылка": 1.0,
            "email": 1.0,
            "смс": 0.9,
            "автоматизация": 0.8,
            "писем": 0.8,
            "getresponse": 0.7,
        },
        "desc": "настройка email и SMS-рассылок, автоматизация писем, работа с сервисами",
    },
    "Куратор обучений": {
        "keywords": {
            "куратор": 1.0,
            "поддержка": 0.9,
            "обратная связь": 0.8,
            "студент": 0.8,
            "чат": 0.9,
            "обучение": 0.9,
        },
        "desc": "поддержка студентов, ответы на вопросы, сопровождение обучения",
    },
    "Менеджер по продажам в онлайн-школу": {
        "keywords": {
            "продажи": 1.0,
            "менеджер": 0.9,
            "звонок": 0.8,
            "crm": 0.8,
            "консультация": 0.9,
            "закрытие сделки": 1.0,
        },
        "desc": "продажи курсов, звонки клиентам, работа с CRM",
    },
    "Онлайн-ассистент": {
        "keywords": {
            "ассистент": 1.0,
            "организация": 0.8,
            "помощь": 0.8,
            "админ": 0.7,
            "задачи": 0.8,
            "письма": 0.7,
        },
        "desc": "административная помощь, организация задач, поддержка руководителя",
    },
    "Модератор чатов и каналов тг": {
        "keywords": {
            "модератор": 1.0,
            "чат": 1.0,
            "канал": 0.9,
            "телеграм": 0.9,
            "правила": 0.8,
            "участники": 0.8,
        },
        "desc": "модерация чатов и каналов, поддержка порядка и правил",
    },
}


app = TelegramClient("Telethon_UserBot", config.parser.api_id, config.parser.api_hash)


def get_message_link(message):
    try:
        if message.link:  # для публичных чатов
            return message.link
    except Exception:
        pass

    if str(message.chat_id).startswith("-100"):  # приватный канал/группа
        return f"https://t.me/c/{str(message.chat_id)[4:]}/{message.id}"
    return "ссылка недоступна"


import re


def markdown_to_html(text: str) -> str:
    # Жирный
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    # Курсив
    text = re.sub(r"_(.*?)_", r"<i>\1</i>", text)
    return text


def message_to_html(message) -> str:

    html = message
    if not getattr(message, "entities", None):
        return html  # просто возвращаем текст если нет entities

    # Сортируем entities по offset (от конца к началу чтобы корректно вставлять теги)
    entities = sorted(message.entities, key=lambda e: e.offset + e.length, reverse=True)

    for ent in entities:
        start, end = ent.offset, ent.offset + ent.length
        entity_text = html[start:end]

        if isinstance(ent, MessageEntityBold):
            html = html[:start] + f"<b>{entity_text}</b>" + html[end:]
        elif isinstance(ent, MessageEntityItalic):
            html = html[:start] + f"<i>{entity_text}</i>" + html[end:]
        elif isinstance(ent, MessageEntityUnderline):
            html = html[:start] + f"<u>{entity_text}</u>" + html[end:]
        elif isinstance(ent, MessageEntityStrike):
            html = html[:start] + f"<s>{entity_text}</s>" + html[end:]
        elif isinstance(ent, MessageEntityCode):
            html = html[:start] + f"<code>{entity_text}</code>" + html[end:]
        elif isinstance(ent, MessageEntityPre):
            # ent.language можно использовать для подсветки
            html = html[:start] + f"<pre>{entity_text}</pre>" + html[end:]
        elif isinstance(ent, MessageEntityTextUrl):
            html = html[:start] + f'<a href="{ent.url}">{entity_text}</a>' + html[end:]
        # Можно добавить другие entity, если потребуется

    return html

processed_messages = set() 

async def process_message(message):
    # Проверка, что сообщение ещё не обрабатывалось
    if message.id in processed_messages:
        logger.info(f"Сообщение {message.id} уже обработано, пропускаем.")
        return
    processed_messages.add(message.id)

    # Собираем текст сообщения
    message_text = (
        message.text
        or message.message
        or message.raw_text
        or getattr(message, "caption", "")
        or ""
    ).strip()

    if not message_text:
        logger.info(f"Сообщение {message.id} пустое, пропускаем.")
        return

    logger.info(f"Проверяем сообщение {message.id}: {message.date}")

    clean_text = message_text
    markdown_text = markdown_to_html(clean_text)
    html_text = message_to_html(markdown_text)
    message_link = get_message_link(message)

    # Находим профессии
    found_proffs = await find_job_func(vacancy_text=clean_text)
    if not found_proffs:
        logger.warning(f"⚠️ Вакансия не подходит ни под одну из профессий: {message.id}")
        return

    # Фильтруем дубли профессий
    unique_proffs = {prof_name: score for prof_name, score in found_proffs}

    for prof_name, score in unique_proffs.items():
        logger.info(f"Найдена профессия '{prof_name}' с оценкой {score:.2f} в сообщении {message.id}")

        # Пересылаем сообщение в канал
        try:
            forwarded_msg = await app.forward_messages(
                entity=config.bot.wacancy_chat_id,
                messages=message.id,
                from_peer=message.chat_id
            )
            chat_id = forwarded_msg.chat_id
            msg_id = forwarded_msg.id
            link = f"https://t.me/c/{str(chat_id)[4:]}/{msg_id}"
            logger.info(f"Вакансия переслана в канал через Telethon: {link}")
        except Exception as e:
            logger.error(f"Ошибка пересылки вакансии: {e}")
            link = None

        # Сохраняем вакансию в БД
        vacancy_id = await save_vacancy(
            text=html_text,
            profession_name=prof_name,
            score=score,
            url=link,
        )

        if vacancy_id:
            logger.info(f"Вакансия по профессии '{prof_name}' сохранена в БД с ID {vacancy_id}.")
            await bot.send_message(
                config.bot.chat_id,
                f"Новая вакансия по профессии '{prof_name}':\n{link}\nОценка: {score:.2f}\nID вакансии: {vacancy_id}\n\n\n{html_text}",
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=await get_delete_vacancy_kb(vacancy_id),
            )
            await send_vacancy_to_users(vacancy_id)
        else:
            logger.info(f"Вакансия по профессии '{prof_name}' уже существует в БД, пропускаем.")

    # Задержка между обработкой сообщений
    await asyncio.sleep(random.uniform(config.parser.delay_min, config.parser.delay_max))

# ==================== Обработка новых сообщений в реальном времени ====================
# Список чатов, которые нужно игнорировать
EXCLUDED_CHAT_IDS = [-1003096281707, 7877140188, -4816957611]  # примеры chat_id

@app.on(events.NewMessage())
async def on_new_message(event):
    # Игнорируем исходящие сообщения
    if event.out:
        return

    # Игнорируем сообщения из определённых чатов
    if event.chat_id in EXCLUDED_CHAT_IDS:
        return

    await process_message(event.message)


# ==================== Главная функция ====================
async def main():
    await app.start(phone=config.parser.phone_number)
    logger.info("Userbot запущен")

    logger.info("Парсер перешел в режим ожидания новых сообщений...")
    await app.run_until_disconnected()


async def list_all_chats():
    await app.start(phone=config.parser.phone_number)
    logger.info("Список чатов и каналов:")

    with open("all_chats.txt", "w", encoding="utf-8") as f:
        async for dialog in app.iter_dialogs():
            name = dialog.name
            chat_id = dialog.id
            chat_type = type(dialog.entity).__name__
            line = f"Name: {name}, ID: {chat_id}, Type: {chat_type}"
            print(line)
            f.write(line + "\n")

    logger.info("Список сохранён в all_chats.txt")


if __name__ == "__main__":
    try:
        # asyncio.run(list_all_chats())
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Userbot остановлен")
