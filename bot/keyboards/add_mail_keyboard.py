from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config.config import load_config
from db.requests import (
    get_all_professions,
    get_all_keywords_from_profession,
    get_profession_by_id,
    get_all_stopwords,
    get_vacancy_by_id,
)
from db.crud import (
    get_upcoming_mailings,
)
from .admin_keyboard import back_to_mailing, button_divider

config = load_config()  # Загружаем конфигурацию

back_to_mailing_kb = InlineKeyboardMarkup(inline_keyboard=[[back_to_mailing]])


next_button = InlineKeyboardButton(
    text="Далее ➡️", callback_data="next_step_mailing"
)
confirm_mailing_button = InlineKeyboardButton(
    text="Подтвердить рассылку", callback_data="confirm_mailing"
)

final_add_mail_kb = InlineKeyboardMarkup(inline_keyboard=[[back_to_mailing, next_button]])

confirm_mailing_kb = InlineKeyboardMarkup(inline_keyboard=[[back_to_mailing, confirm_mailing_button]])

def is_mail_with_file():
    builder = InlineKeyboardBuilder()
    button_yes = InlineKeyboardButton(text="Да, с файлом", callback_data="with_file")
    button_no = InlineKeyboardButton(
        text="Нет, просто текст", callback_data="without_file"
    )
    builder.row(button_yes, button_no)
    builder.row(back_to_mailing)
    return builder.as_markup()


def is_mail_with_keyboard():
    builder = InlineKeyboardBuilder()
    button_yes = InlineKeyboardButton(text="Да, с клавиатурой", callback_data="with_kb")
    button_no = InlineKeyboardButton(
        text="Нет, без клавиатуры", callback_data="without_kb"
    )
    builder.row(button_yes, button_no)
    builder.row(back_to_mailing)
    return builder.as_markup()


def keyboards_for_mailings():
    builder = InlineKeyboardBuilder()
    hello_keyboard = InlineKeyboardButton(
        text="Приветственная клавиатура", callback_data="mail_kb_1"
    )
    builder.row(hello_keyboard)
    builder.row(back_to_mailing)
    return builder.as_markup()


def mailing_segments_keyboard(
    segments: dict,
    segment_ids: dict,
    page: int = 1,
    per_page: int = 5,
) -> InlineKeyboardMarkup:

    builder = InlineKeyboardBuilder()
    segment_items = list(segments.items())

    # первые 4 базовые сегмента
    for segment_name, data in segment_items[:4]:
        text = f"✅ {segment_name}" if data["selected"] else segment_name
        button = InlineKeyboardButton(
            text=text,
            callback_data=f"base_{segment_ids[segment_name]}"
        )
        builder.row(button)

    builder.row(button_divider)

    # профессиональные сегменты
    prof_segments = segment_items[4:]
    total = len(prof_segments)
    total_pages = (total + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    page_prof_segments = prof_segments[start:end]

    for segment_name, data in page_prof_segments:
        text = f"✅ {segment_name}" if data["selected"] else segment_name
        button = InlineKeyboardButton(
            text=text,
            callback_data=f"prof_{segment_ids[segment_name]}"
        )
        builder.row(button)

    builder.adjust(1)

    # кнопки навигации
    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"mailing_seg_page_{page - 1}"
                )
            )
        if page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="Вперёд ➡️",
                    callback_data=f"mailing_seg_page_{page + 1}"
                )
            )
        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(
            text="Подтвердить сегменты",
            callback_data="confirm_segments"
        )
    )
    builder.row(back_to_mailing)
    return builder.as_markup()


async def get_mailing_keyboard(keyboard_type: str):
    try:
        keyboard_num = keyboard_type.split("_")[-1]
    except Exception:
        keyboard_num = keyboard_type
        
    if keyboard_num == "1":
        builder = InlineKeyboardBuilder()
        hello_button = InlineKeyboardButton(
            text="Приветствие 👋", callback_data="hello_from_mailing"
        )
        builder.row(hello_button)
        return builder.as_markup()
    return None