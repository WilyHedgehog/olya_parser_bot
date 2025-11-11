from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config.config import load_config
from db.requests import (
    get_all_professions,
    get_all_keywords_from_profession,
    get_profession_by_id,
    get_all_stopwords,
    get_vacancy_by_id,
    get_admins_list,
)
from db.crud import (
    get_upcoming_mailings,
)

config = load_config()  # Загружаем конфигурацию


back_to_admin_main = InlineKeyboardButton(
    text="◀️ Назад в админку ◀️", callback_data="back_to_admin"
)
back_to_proffs_kb_button = InlineKeyboardButton(
    text="◀️ Назад в меню парсера ◀️", callback_data="back_to_proffs"
)
from_admin_add_proff = InlineKeyboardButton(
    text="Добавить профессию", callback_data="add_proff"
)
from_admin_delete_proff = InlineKeyboardButton(
    text="Удалить профессию", callback_data="delete_proff"
)
from_admin_add_proffs_desc = InlineKeyboardButton(
    text="Добавить описание к профессии", callback_data="add_proffs_desc"
)
from_admin_delete_proffs_desc = InlineKeyboardButton(
    text="Удалить описание у профессии", callback_data="delete_proffs_desc"
)
from_admin_add_keyword = InlineKeyboardButton(
    text="Добавить ключевое слово", callback_data="add_keyword"
)
from_admin_delete_keyword = InlineKeyboardButton(
    text="Удалить ключевое слово", callback_data="delete_keyword"
)
back_to_choosen_prof = InlineKeyboardButton(
    text="◀️ Назад к профессии ◀️", callback_data="back_to_choosen_prof"
)
stopwords_add = InlineKeyboardButton(
    text="Добавить стоп-слова", callback_data="stopwords_add"
)
stopwords_delete = InlineKeyboardButton(
    text="Удалить стоп-слова", callback_data="stopwords_delete"
)
show_stopwords = InlineKeyboardButton(
    text="Показать стоп-слова", callback_data="show_stopwords"
)
button_divider = InlineKeyboardButton(text="–––––––––––––––––––", callback_data="---")
parser_menu_button = InlineKeyboardButton(
    text="🔍 Меню парсера 🔍", callback_data="parser_menu"
)
get_file_id_button = InlineKeyboardButton(
    text="🆔 Получить file_id 🆔", callback_data="get_file_id"
)
mailing_settings_button = InlineKeyboardButton(
    text="🛠 Настройки рассылок 🛠", callback_data="mailing_settings"
)
add_delete_admin_button = InlineKeyboardButton(
    text="👤 Добавить/Удалить админа 👤", callback_data="add_delete_admin"
)
back_to_mailing = InlineKeyboardButton(
    text="◀️ Назад в меню рассылок ◀️", callback_data="back_to_mailing"
)
delete_mailing_button = InlineKeyboardButton(
    text="Удалить рассылку", callback_data="delete_mailing"
)
add_mailing_button = InlineKeyboardButton(
    text="Добавить рассылку", callback_data="add_mailing"
)
back_to_start_menu_button = InlineKeyboardButton(
    text="🔙 Назад в главное меню бота 🔙", callback_data="back_to_start_menu"
)
stats_button = InlineKeyboardButton(
    text="📊 Статистика вакансий 📊", callback_data="stats"
)
background_tasks_button = InlineKeyboardButton(
    text="🔧 Задачи в фоне 🔧", callback_data="background_tasks"
)
delete_admin_message = InlineKeyboardButton(
    text="Удалить сообщение", callback_data="delete_admin_message"
)
one_more_message = InlineKeyboardButton(
    text="Отправить ещё одно сообщение", callback_data="one_more_message"
)



def get_pagination_keyboard(current: int, total: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру со стрелками навигации."""
    buttons = []
    if total > 1:
        row = []
        if current > 0:
            row.append(InlineKeyboardButton(text="⬅️", callback_data=f"page:{current - 1}"))
        row.append(InlineKeyboardButton(text=f"{current + 1}/{total}", callback_data="noop"))
        if current < total - 1:
            row.append(InlineKeyboardButton(text="➡️", callback_data=f"page:{current + 1}"))
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_keyboard(super_admin: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(parser_menu_button)
    builder.row(get_file_id_button)
    builder.row(mailing_settings_button)
    builder.row(stats_button)
    if super_admin:
        builder.row(add_delete_admin_button)
        builder.row(background_tasks_button)
    builder.row(button_divider)
    builder.row(back_to_start_menu_button)
    builder.adjust(1)  # Располагаем кнопки в один столбец
    return builder.as_markup()


def mailing_settings_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(add_mailing_button)
    builder.row(delete_mailing_button)
    builder.row(button_divider)
    builder.row(back_to_admin_main)
    builder.adjust(1)  # Располагаем кнопки в один столбец
    return builder.as_markup()


def background_tasks_start_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Автоудаление вакансий", callback_data="autodelete_vacancy"))
    builder.row(InlineKeyboardButton(text="Рассылка раз в 2 часа", callback_data="two_hours_send_vacancy"))
    builder.row(button_divider)
    builder.row(back_to_admin_main)
    return builder.as_markup()


def stopwords_pagination_keyboard(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Навигационные кнопки
    nav_buttons = []
    if total_pages > 1:
        if current_page > 1:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️", callback_data=f"stoppage_{current_page - 1}")
            )
        else:
            nav_buttons.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        nav_buttons.append(
            InlineKeyboardButton(
                text=f"{current_page}/{total_pages}", callback_data="noop"
            )
        )

        if current_page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(text="➡️", callback_data=f"stoppage_{current_page + 1}")
            )
        else:
            nav_buttons.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        builder.row(*nav_buttons)

    # Кнопка "Назад"
    builder.row(back_to_proffs_kb_button)

    return builder.as_markup()


async def professions_keyboard(
    page: int = 1,
    per_page: int = 4,  # 2 columns * 3 rows (остальные 2 строки под навигацию и back)
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    professions = await get_all_professions()
    total = len(professions)
    if total == 0:
        builder.row(from_admin_add_proff)
        builder.row(back_to_admin_main)
        return builder.as_markup()

    total_pages = (total + per_page - 1) // per_page
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    page_profs = professions[start:end]

    for prof in page_profs:
        builder.button(text=prof.name, callback_data=f"proff_{prof.id}")

    # Раскладываем proff-кнопки по 2 в строке
    builder.adjust(1)

    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️", callback_data=f"ppage_{page-1}")
            )
        else:
            nav_buttons.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        nav_buttons.append(
            InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")
        )

        if page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(text="➡️", callback_data=f"ppage_{page+1}")
            )
        else:
            nav_buttons.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        builder.row(*nav_buttons)
    builder.row(button_divider)
    # Кнопка Назад в админку
    builder.row(from_admin_add_proff)
    stopwords = await get_all_stopwords()
    if stopwords:
        builder.row(stopwords_add)
        builder.row(stopwords_delete)
        builder.row(show_stopwords)
    else:
        builder.row(stopwords_add)
    builder.row(back_to_admin_main)

    return builder.as_markup()


async def choosen_prof_keyboard(profession_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    profession = await get_profession_by_id(profession_id)
    if not profession:
        builder.button(text="Профессия не найдена", callback_data="noop")
        builder.row(back_to_proffs_kb_button)
        return builder.as_markup()

    if not profession.keywords:
        builder.row(from_admin_add_keyword)
    else:
        builder.row(from_admin_add_keyword, from_admin_delete_keyword)

    if profession.desc:
        builder.row(from_admin_delete_proffs_desc)
    else:
        builder.row(from_admin_add_proffs_desc)
    builder.row(from_admin_delete_proff)
    builder.row(back_to_proffs_kb_button)
    return builder.as_markup()


async def keywords_keyboard(
    profession_id: int,
    page: int = 1,
    per_page: int = 8,  # 2 columns * 4 rows (остальные 2 строки под навигацию и back)
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    keywords = await get_all_keywords_from_profession(profession_id)
    total = len(keywords)

    total_pages = (total + per_page - 1) // per_page
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    page_keywords = keywords[start:end]

    for kw in page_keywords:
        builder.button(text=kw.word, callback_data=f"keyword_{kw.id}")

    # Раскладываем keyword-кнопки по 2 в строке (макс 4 строки при per_page=8)
    builder.adjust(2)

    # Навигация (если больше 1 страницы)
    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️", callback_data=f"kwpage_{profession_id}_{page-1}"
                )
            )
        else:
            nav_buttons.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        nav_buttons.append(
            InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")
        )

        if page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="➡️", callback_data=f"kwpage_{profession_id}_{page+1}"
                )
            )
        else:
            nav_buttons.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        builder.row(*nav_buttons)
    builder.row(button_divider)

    # Кнопка Назад к профессиям
    builder.row(back_to_choosen_prof)

    return builder.as_markup()


async def stopwords_keyboard(
    page: int = 1,
    per_page: int = 8,  # 2 columns * 4 rows (остальные 2 строки под навигацию и back)
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    stopwords = await get_all_stopwords()
    total = len(stopwords)

    total_pages = (total + per_page - 1) // per_page
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    page_stopwords = stopwords[start:end]

    for sw in page_stopwords:
        builder.button(text=sw.word, callback_data=f"stopword_{sw.id}")

    # Раскладываем stopword-кнопки по 2 в строке (макс 4 строки при per_page=8)
    builder.adjust(2)

    # Навигация (если больше 1 страницы)
    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️", callback_data=f"swpage_{page-1}")
            )
        else:
            nav_buttons.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        nav_buttons.append(
            InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")
        )

        if page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(text="➡️", callback_data=f"swpage_{page+1}")
            )
        else:
            nav_buttons.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        builder.row(*nav_buttons)

    builder.row(button_divider)
    # Кнопка Назад к профессиям
    builder.row(back_to_proffs_kb_button)

    return builder.as_markup()


async def get_delete_mailing_kb(
    page: int = 1,
    per_page: int = 10,  # Количество рассылок на странице
) -> InlineKeyboardMarkup:

    builder = InlineKeyboardBuilder()
    mailings = await get_upcoming_mailings(limit=30)
    if not mailings:
        builder.row(
            InlineKeyboardButton(
                text="Нет запланированных рассылок", callback_data="noop"
            )
        )
        builder.row(back_to_mailing)
        return builder.as_markup()

    total = len(mailings)

    total_pages = (total + per_page - 1) // per_page
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    page_mailings = mailings[start:end]

    for m in page_mailings:
        display_text = f"{m.task_name} | {m.run_at.strftime('%Y-%m-%d %H:%M')}"
        builder.button(
            text=display_text,
            callback_data=f"delete_mailing_{m.id}",
        )

    builder.adjust(1)

    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️", callback_data=f"mpage_{page-1}")
            )
        else:
            nav_buttons.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        nav_buttons.append(
            InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")
        )

        if page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(text="➡️", callback_data=f"mpage_{page+1}")
            )
        else:
            nav_buttons.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        builder.row(*nav_buttons)

    # Раскладываем кнопки по 1 в строке
    builder.adjust(1)
    builder.row(button_divider)
    builder.row(back_to_admin_main)
    return builder.as_markup()


async def delete_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    admins = await get_admins_list()
    if not admins:
        builder.row(
            InlineKeyboardButton(text="Нет админов для удаления", callback_data="noop")
        )
        builder.row(back_to_admin_main)
        return builder.as_markup()

    for admin in admins:
        admin_id = str(admin.telegram_id)
        builder.button(
            text=f"{admin.full_name}",
            callback_data=f"del_admin_{admin_id}",
        )
    return builder.as_markup()


async def get_delete_vacancy_kb(vacancy_id) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Удалить вакансию", callback_data="delete_vacancy_" + str(vacancy_id)
        )
    )
    return builder.as_markup()


async def get_vacancy_url_kb(vacancy_id: str) -> InlineKeyboardMarkup:
    vacancy = await get_vacancy_by_id(vacancy_id)
    builder = InlineKeyboardBuilder()
    if not vacancy:
        builder.row(
            InlineKeyboardButton(text="Вакансия не найдена", callback_data="noop")
        )
        return builder.as_markup()
    elif vacancy.admin_chat_url is None:
        builder.row(
            InlineKeyboardButton(
                text="Оригинальная ссылка на вакансию", url=vacancy.url
            )
        )
        return builder.as_markup()
    else:
        url = f"https://t.me/c/{str(config.bot.chat_id)[4:]}/{vacancy.admin_chat_url}"
        builder.row(
            InlineKeyboardButton(
                text="Ссылка на вакансию в админ-чате", url=url,
            )
        )
        return builder.as_markup()


def cancel_task_kb(id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Отменить задание", callback_data=f"cancel_task_{id}")
    )
    return builder.as_markup()

def after_message_keyboard(reply_one, reply_two, target_user_id):
    builder = InlineKeyboardBuilder()
    builder.row(one_more_message)
    builder.row(InlineKeyboardButton(text="Удалить отправленное", callback_data=f"delmsg_{reply_one}_{reply_two}_{target_user_id}"))
    builder.row(back_to_admin_main)
    return builder.as_markup()

back_to_choosen_prof_kb = InlineKeyboardMarkup(inline_keyboard=[[back_to_choosen_prof]])

back_to_proffs_kb = InlineKeyboardMarkup(inline_keyboard=[[back_to_proffs_kb_button]])

back_to_admin_main_kb = InlineKeyboardMarkup(inline_keyboard=[[back_to_admin_main]])

