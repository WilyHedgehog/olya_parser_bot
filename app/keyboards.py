from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from lexicon import LEXICON_BUTTONS
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
import os
from app.parser_database import load_config

load_dotenv()


MONTH_SHORT = {
    1: "янв",
    2: "фев",
    3: "мар",
    4: "апр",
    5: "май",
    6: "июн",
    7: "июл",
    8: "авг",
    9: "сен",
    10: "окт",
    11: "ноя",
    12: "дек",
}

WEEKDAYS_SHORT = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс"}


ALLOWED_WEEKDAYS = [2, 3, 4]




add_word_button = InlineKeyboardButton(
    text="Добавить слова", callback_data="add_word_button"
)
add_chanel_button = InlineKeyboardButton(
    text="Добавить канал", callback_data="add_chanel_button"
)
delete_word_button = InlineKeyboardButton(
    text="Удалить слово", callback_data="delete_word_button"
)


def generate_keywords_keyboard():
    config = load_config()
    keywords = config.get("keywords", [])

    kb = InlineKeyboardBuilder()
    for word in keywords:
        kb.add(InlineKeyboardButton(text=word, callback_data=f"del_kw:{word}"))
    kb.adjust(2)  # кнопки по 2 в ряд
    return kb.as_markup()


admin_panel_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [add_word_button, delete_word_button],
        [add_chanel_button],
    ]
)






main_menu_button = InlineKeyboardButton(
    text="🔙 Назад в Главное меню", callback_data="main_menu"
)
begin_button = InlineKeyboardButton(
    text="Я согласен/согласна", callback_data="begin_button_click"
)
first_time_button = InlineKeyboardButton(
    text="Я первый раз", callback_data="first_time_button_click"
)
old_guy_button = InlineKeyboardButton(
    text="Повторная сессия", callback_data="old_guy_button_click"
)
new_booking_button = InlineKeyboardButton(
    text="🆕 Новая запись", callback_data="new_booking_button_click"
)
cancel_booking_button = InlineKeyboardButton(
    text="❌ Отменить запись", callback_data="cancel_booking_button_click"
)
admin_cancel_booking = InlineKeyboardButton(
    text="❌ Отменить запись", callback_data="admin_cancel_booking"
)
requisites_buton = InlineKeyboardButton(
    text="💰 Способы оплаты", callback_data="requisites_buton_click"
)
check_booking_button = InlineKeyboardButton(
    text="🗓 Проверить время записи", callback_data="check_booking_button_click"
)
send_to_all_button = InlineKeyboardButton(
    text="✉️ Рассылка по базе", callback_data="send_to_all_button_click"
)
admin_button = InlineKeyboardButton(
    text="⚙️ Админ панель", callback_data="admin_button_click"
)
send_to_client = InlineKeyboardButton(
    text="💬 Отправить сообещние пользователю", callback_data="send_to_client"
)
confirm_meeting = InlineKeyboardButton(
    text="☑️ Подтвердить запись пользователя", callback_data="confirm_meeting"
)
one_more_message = InlineKeyboardButton(
    text="💬 Ещё одно сообщение", callback_data="one_more_message"
)
confirm_mailing = InlineKeyboardButton(
    text="☑️ Подтвердить рассылку по базе", callback_data="confirm_mailing"
)
tests_main_button = InlineKeyboardButton(
    text="📝 Тестирования", callback_data="test_button"
)
docs_tests_button = InlineKeyboardButton(
    text="💿 Google Диск", callback_data="drive_tests_button"
)
online_tests_button = InlineKeyboardButton(
    text="💻 Онлайн-формат", callback_data="online_tests_button"
)
back_to_tests_button = InlineKeyboardButton(
    text="⬅️ Назад", callback_data="back_to_test_button"
)
add_to_mentoring = InlineKeyboardButton(
    text="🧑‍🧒 Добавить в наставничество", callback_data="add_to_mentoring"
)
delete_from_mentoring = InlineKeyboardButton(
    text="🚮 Удалить из наставничеста", callback_data="delete_from_mentoring"
)
check_mentoring = InlineKeyboardButton(
    text="❔ Кто сейчас в наставничестве", callback_data="check_mentoring"
)
change_name = InlineKeyboardButton(text="✏️ Изменить имя", callback_data="change_name")
check_booking_by_user = InlineKeyboardButton(
    text="📍 Проверить записи пользователя", callback_data="check_booking_by_user"
)
check_booking_by_week = InlineKeyboardButton(
    text="🕒 Записи на неделю вперед", callback_data="check_booking_by_week"
)
choose_user = InlineKeyboardButton(
    text="🔍 Выбрать пользователя", callback_data="choose_user"
)
back_to_user_button = InlineKeyboardButton(
    text="⬅️ Назад к пользователю", callback_data="back_to_user_button_click"
)
close_access = InlineKeyboardButton(
    text="🚫 Вернуть пользователя к диагностике", callback_data="close_access"
)
open_access = InlineKeyboardButton(
    text="✅ Дать тоступ к 50-минутным сессииям", callback_data="open_access"
)
check_tasks = InlineKeyboardButton(
    text="📂 Меню отложенных задач", callback_data="check_tasks"
)
task_one = InlineKeyboardButton(
    text="1️⃣ Выключить автоомену записи", callback_data="task_one"
)
task_two = InlineKeyboardButton(
    text="2️⃣ Выключить смену статуса пользователя", callback_data="task_two"
)
yes_button = InlineKeyboardButton(text="☑️ Подтверждаю", callback_data="yes_button")

tasks_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[task_one], [task_two], [back_to_user_button]]
)

yes_keyboard = InlineKeyboardMarkup(inline_keyboard=[[yes_button]])


def generate_user_events_kb(events: list, action: str):
    """
    Генерирует inline клавиатуру с кнопками событий пользователя.
    action: 'cancel' или 'reschedule'
    На кнопке отображается только дата и время в формате ДД.ММ ЧЧ:ММ.
    """
    kb = InlineKeyboardBuilder()
    for event in events:
        start_time_str = event["start"].get("dateTime", event["start"].get("date"))
        start_dt = datetime.fromisoformat(start_time_str)
        formatted_time = start_dt.strftime("%d.%m %H:%M")
        kb.button(text=formatted_time, callback_data=f"{action}:{event['id']}")
    kb.adjust(1)  # 1 кнопка в ряду
    kb.row(main_menu_button)

    return kb.as_markup()


def build_hours_keyboard_with_datetime(
    date: datetime.date, free_keys: list[str]
) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()

    # Кнопки со слотами
    for key in free_keys:
        time_str = LEXICON_BUTTONS[key]  # '10:00', '12:00' и т.д.
        dt_iso = datetime.combine(
            date, datetime.strptime(time_str, "%H:%M").time()
        ).isoformat()
        builder.button(text=time_str, callback_data=f"slot:{dt_iso}")

    builder.adjust(3)  # по 3 кнопки в ряд

    # Добавляем кнопку "Назад" отдельным рядом
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back"))

    return builder


def generate_days_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    days_found = 0
    # смещаем на (2 дня + номер_страницы * 6)
    current_day = datetime.now(ZoneInfo("Europe/Moscow")) + timedelta(days=2 + page * 6)

    # Находим 6 ближайших доступных дней
    while days_found < 6:
        if current_day.weekday() in ALLOWED_WEEKDAYS:
            weekday = WEEKDAYS_SHORT[current_day.weekday()]
            month = MONTH_SHORT[current_day.month]
            day_text = f"{weekday} {current_day.day} {month}"
            callback = f"day:{current_day.strftime('%Y-%m-%d')}"
            builder.button(text=day_text, callback_data=callback)
            days_found += 1
        current_day += timedelta(days=1)

    # Разбиваем кнопки по 3 в ряд
    builder.adjust(3)

    # Навигация вперед/назад
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"calendar_page:{page-1}"
            )
        )
    nav_buttons.append(
        InlineKeyboardButton(text="➡️ Вперёд", callback_data=f"calendar_page:{page+1}")
    )
    builder.row(*nav_buttons)

    builder.row(main_menu_button)

    return builder.as_markup()


def get_manage_booking_keyboard(user_id):
    admin_ids = [
        x.strip() for x in os.environ.get("ADMIN_ID", "").split(",") if x.strip()
    ]
    is_admin = str(user_id) in admin_ids

    kb_builder = InlineKeyboardBuilder()
    buttons: list[InlineKeyboardButton] = [
        new_booking_button,
        cancel_booking_button,
        requisites_buton,
    ]
    kb_builder.row(*buttons, width=2)

    kb_builder.row(check_booking_button)
    kb_builder.row(tests_main_button)

    if is_admin:
        kb_builder.row(admin_button)

    return kb_builder.as_markup()


def get_requisites_keyboard(user_id):
    admin_ids = [
        x.strip() for x in os.environ.get("ADMIN_ID", "").split(",") if x.strip()
    ]
    is_admin = str(user_id) in admin_ids

    kb_builder = InlineKeyboardBuilder()
    buttons = (
        InlineKeyboardButton(text="Т-Банк", callback_data="tbank"),
        InlineKeyboardButton(text="СберБанк", callback_data="sberbank"),
        InlineKeyboardButton(text="GetCourse", callback_data="getcourse"),
    )

    kb_builder.row(*buttons, width=1)

    if is_admin:
        kb_builder.row(InlineKeyboardButton(text="PayPal", callback_data="paypal"))
        kb_builder.row(
            InlineKeyboardButton(text="ПриватБанк", callback_data="privatbank")
        )

    kb_builder.row(main_menu_button)

    return kb_builder.as_markup()


choose_user_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [send_to_client],
        [confirm_meeting],
        [check_booking_by_user],
        [add_to_mentoring],
        [delete_from_mentoring],
        [close_access],
        [open_access],
        [change_name],
        [check_tasks],
        [admin_cancel_booking],
        [admin_button],
    ]
)


admin_panel_v2_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [choose_user],
        [send_to_all_button],
        [check_mentoring],
        [check_booking_by_week],
        [main_menu_button],
    ]
)


back_to_requisites_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data="back_to_requisites_button_click"
            )
        ]
    ]
)


manage_booking_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[new_booking_button, cancel_booking_button]]
)


begin_keyboard = InlineKeyboardMarkup(inline_keyboard=[[begin_button]])


tests_main_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[docs_tests_button], [online_tests_button], [main_menu_button]]
)


back_to_tests_keyboard = InlineKeyboardMarkup(inline_keyboard=[[back_to_tests_button]])


is_first_time_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[first_time_button, old_guy_button]]
)


new_messsage_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[one_more_message], [back_to_user_button]]
)


back_to_admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[[admin_button]])

back_to_user_keyboard = InlineKeyboardMarkup(inline_keyboard=[[back_to_user_button]])

send_to_all_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[confirm_mailing], [admin_button]]
)


main_menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[[main_menu_button]])
