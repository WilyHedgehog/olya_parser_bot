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

config = load_config()  # Загружаем конфигурацию


back_to_admin_kb = InlineKeyboardButton(
    text="Назад в админку", callback_data="back_to_admin"
)
back_to_proffs_kb_button = InlineKeyboardButton(
    text="Назад в меню парсера", callback_data="back_to_proffs"
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
    text="Назад к профессии", callback_data="back_to_choosen_prof"
)
stopwords_add = InlineKeyboardButton(
    text="Добавить стоп-слова", callback_data="stopwords_add"
)
stopwords_delete = InlineKeyboardButton(
    text="Удалить стоп-слова", callback_data="stopwords_delete"
)
button_divider = InlineKeyboardButton(text="–––––––––––––––––––", callback_data="---")


def admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Рассылка", callback_data="mailing")
    builder.button(text="Статистика", callback_data="stats")
    builder.button(text="Добавить промокод", callback_data="add_promo")
    builder.button(text="Удалить промокод", callback_data="delete_promo")
    builder.button(text="Посмотреть все промокоды", callback_data="view_promos")
    builder.button(text="Закрыть", callback_data="close")
    builder.adjust(1)  # Располагаем кнопки в один столбец
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
        builder.row(back_to_admin_kb)
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
    else:
        builder.row(stopwords_add)
    builder.row(back_to_admin_kb)

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
    builder.row(back_to_admin_kb)

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
    if not vacancy or vacancy.admin_chat_url is None:
        builder.row(
            InlineKeyboardButton(text="Ошика с получением ссылки", callback_data="noop")
        )
        return builder.as_markup()
    builder.row(
        InlineKeyboardButton(
            text="Оригинальная ссылка на вакансию", url=vacancy.admin_chat_url
        )
    )
    return builder.as_markup()


back_to_choosen_prof_kb = InlineKeyboardMarkup(inline_keyboard=[[back_to_choosen_prof]])

back_to_proffs_kb = InlineKeyboardMarkup(inline_keyboard=[[back_to_proffs_kb_button]])
