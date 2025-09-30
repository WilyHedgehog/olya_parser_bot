from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config.config import load_config
from db.requests import (
    get_all_professions,
    get_all_users_professions,
    get_user_delivery_mode,
    get_user_subscription_until,
    get_user_by_telegram_id,
)

config = load_config()  # Загружаем конфигурацию

delivery_modes = {
    "instant": "Мгновенная",
    "two_hours": "Раз в 2 часа",
    "button_click": "По нажатию кнопки",
}

confirm_email_button = InlineKeyboardButton(
    text="Подтвердить", callback_data="confirm_email"
)
choose_all_professions_button = InlineKeyboardButton(
    text="Выбрать все профессии", callback_data="all_professions_choose"
)
dismiss_all_professions_button = InlineKeyboardButton(
    text="Снять выбор со всех профессий", callback_data="all_professions_dismiss"
)
confirm_choice_button = InlineKeyboardButton(
    text="Подтвердить выбор", callback_data="confirm_choice"
)
one_month_start_payment_process_button = InlineKeyboardButton(
    text="1 месяц", callback_data="start_payment_process_1_month"
)
three_months_start_payment_process_button = InlineKeyboardButton(
    text="3 месяца", callback_data="start_payment_process_3_months"
)
back_to_main_button = InlineKeyboardButton(text="Назад", callback_data="back_to_main")
button_divider = InlineKeyboardButton(text="–––––––––––––––––––", callback_data="---")
one_month_auto_payment_button = InlineKeyboardButton(
    text="1 месяц (автооплата)", callback_data="start_payment_process_auto_1_month"
)
three_months_auto_payment_button = InlineKeyboardButton(
    text="3 месяца (автооплата)", callback_data="start_payment_process_auto_3_months"
)
one_month_no_auto_payment_button = InlineKeyboardButton(
    text="1 месяц (без автооплаты)",
    callback_data="start_payment_process_no_auto_1_month",
)
three_months_no_auto_payment_button = InlineKeyboardButton(
    text="3 месяца (без автооплаты)",
    callback_data="start_payment_process_no_auto_3_months",
)
is_auto_payment_true_button = InlineKeyboardButton(
    text="Автооплата", callback_data="auto_payment_true"
)
is_auto_payment_false_button = InlineKeyboardButton(
    text="Ручная оплата", callback_data="auto_payment_false"
)


async def get_all_professions_kb(
    user_id: int, page: int = 1, per_page: int = 5
) -> InlineKeyboardMarkup:
    professions = await get_all_professions()
    user_prof_items = await get_all_users_professions(user_id)

    total_len = len(professions)
    builder = InlineKeyboardBuilder()

    if total_len == 0:
        builder.row(confirm_email_button)
        return builder.as_markup()

    # Создаем быстрый индекс выбранности профессий пользователем
    # profession_id -> is_selected
    user_prof_map = {item.profession_id: item.is_selected for item in user_prof_items}

    # Пагинация
    total_pages = (total_len + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    page_professions = professions[start:end]

    # Формируем кнопки только для текущей страницы
    for profession in page_professions:
        is_selected = user_prof_map.get(profession.id, False)
        if is_selected:
            builder.button(
                text=f"✅ {profession.name}",
                callback_data=f"profession_chosen_{profession.id}",
            )
        else:
            builder.button(
                text=profession.name,
                callback_data=f"profession_unchosen_{profession.id}",
            )

    builder.adjust(1)

    # Навигация
    if total_pages > 1:
        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"uppage_{page-1}"))
        else:
            nav.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        nav.append(
            InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")
        )

        if page < total_pages:
            nav.append(InlineKeyboardButton(text="➡️", callback_data=f"uppage_{page+1}"))
        else:
            nav.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        builder.row(*nav)

    builder.row(button_divider)
    builder.row(choose_all_professions_button)
    builder.row(dismiss_all_professions_button)
    builder.row(confirm_choice_button)
    return builder.as_markup()


async def get_delivery_mode_kb(
    user_id: int, page: int = 1, per_page: int = 3
) -> InlineKeyboardMarkup:
    user_mode = await get_user_delivery_mode(user_id)
    builder = InlineKeyboardBuilder()
    modes = list(delivery_modes.items())
    total = len(modes)
    if total == 0:
        builder.row(confirm_email_button)
        return builder.as_markup()

    total_pages = (total + per_page - 1) // per_page
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    page_modes = modes[start:end]

    for mode_key, mode_name in page_modes:
        if mode_key == user_mode:
            builder.button(text=f"✅ {mode_name}", callback_data=f"dmode_{mode_key}")
        else:
            builder.button(text=mode_name, callback_data=f"dmode_{mode_key}")

    # Раскладываем mode-кнопки по 2 в строке
    builder.adjust(2)

    builder.row(button_divider)
    builder.row(confirm_choice_button)
    return builder.as_markup()


async def get_pay_subscription_kb(link: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Перейти к оплате", url=link))
    builder.row(back_to_main_button)
    return builder.as_markup()


async def get_main_reply_kb(user_id: int) -> ReplyKeyboardMarkup:
    user_delivery_mode = await get_user_delivery_mode(user_id)
    user = await get_user_by_telegram_id(user_id)

    buy_subscription_text = "💳 Купить подписку 💳"
    get_earned_vacancies_text = "Получить накопленные вакансии"
    profeessions_settings_text = "🛠️ Настройки профессий 🛠️"
    delivery_settings_text = "📬 Настройки параметров доставки вакансий 📬"
    promo_text = "🎟️ Активировать промокод 🎟️"
    referal_text = "👫 Пригласить друга 👭"
    if user.active_promo and user.active_promo.lower() in [
        "club2425vip",
        "club2425",
        "fm091025",
    ]:
        promo_text = (
            " Активировать новый промокод можно только после окончания имеющегося"
        )
        if user_delivery_mode == "button_click":
            buttons = [
                [KeyboardButton(text=profeessions_settings_text)],
                [KeyboardButton(text=delivery_settings_text)],
                [
                    KeyboardButton(text=get_earned_vacancies_text),
                    KeyboardButton(text=referal_text),
                ],
                [KeyboardButton(text=promo_text)],
                [KeyboardButton(text=buy_subscription_text)],
            ]
        else:
            buttons = [
                [KeyboardButton(text=profeessions_settings_text)],
                [KeyboardButton(text=delivery_settings_text)],
                [
                    KeyboardButton(text=buy_subscription_text),
                    KeyboardButton(text=referal_text),
                ],
                [KeyboardButton(text=promo_text)],
            ]
    else:
        if user_delivery_mode == "button_click":
            buttons = [
                [KeyboardButton(text=profeessions_settings_text)],
                [KeyboardButton(text=delivery_settings_text)],
                [
                    KeyboardButton(text=get_earned_vacancies_text),
                    KeyboardButton(text=promo_text),
                ],
                [
                    KeyboardButton(text=buy_subscription_text),
                    KeyboardButton(text=referal_text),
                ],
            ]
        else:
            buttons = [
                [KeyboardButton(text=profeessions_settings_text)],
                [KeyboardButton(text=delivery_settings_text)],
                [
                    KeyboardButton(text=promo_text),
                    KeyboardButton(text=buy_subscription_text),
                ],
                [KeyboardButton(text=referal_text)],
            ]
    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите действие",
    )
    return keyboard


confirm_email_button_kb = InlineKeyboardMarkup(
    inline_keyboard=[[confirm_email_button], [back_to_main_button]]
)

start_payment_process_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            one_month_start_payment_process_button,
            three_months_start_payment_process_button,
        ],
        [back_to_main_button],
    ]
)

is_auto_payment_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [is_auto_payment_true_button],
        [is_auto_payment_false_button],
        [back_to_main_button],
    ]
)

back_to_main_kb = InlineKeyboardMarkup(inline_keyboard=[[back_to_main_button]])

keyboard_remove_reply = ReplyKeyboardRemove()
