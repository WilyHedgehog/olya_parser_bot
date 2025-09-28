import logging
from aiogram import F, Router
from aiogram.filters import Command, MagicData
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.keyboards.admin_keyboard import (
    professions_keyboard,
    keywords_keyboard,
    choosen_prof_keyboard,
    stopwords_keyboard,
    back_to_choosen_prof_kb,
    back_to_proffs_kb,
)
from bot.states.admin import Prof
from bot.filters.filters import IsAdminFilter
from db.requests import (
    get_profession_by_id,
    add_keyword_to_profession,
    db_delete_keyword,
    load_stopwords,
    db_add_profession,
    db_delete_profession,
    db_add_profession_desc,
    db_delete_profession_desc,
    db_add_stopword,
    db_delete_stopword,
    get_all_stopwords,
)

from find_job_process.find_job import load_professions

from sqlalchemy.ext.asyncio import AsyncSession
from bot.lexicon.lexicon import LEXICON_PARSER

logger = logging.getLogger(__name__)
logger.info("Admin handler module loaded")
router = Router(name="admin commands router")
# Фильтр: роутер доступен только chat id, равному admin_id,
# который передан в диспетчер
# router.message.filter(MagicData(F.event.chat.id == F.admin_id))  # noqa


async def get_stopwords_text() -> str:
    try:
        stopwords = await get_all_stopwords()
        return (
            ", ".join(sw.word for sw in stopwords)
            if stopwords
            else "Стоп-слова не добавлены"
        )
    except Exception as e:
        logger.error(f"Error fetching stopwords: {e}")
        return "Ошибка при получении стоп-слов"


async def get_keywords_and_desc(profession_id: str) -> tuple[str, str]:
    try:
        profession = await get_profession_by_id(profession_id)
        keywords_text = (
            ", ".join(f"{kw.word}:{kw.weight}" for kw in profession.keywords)
            if profession.keywords
            else "Ключевые слова не добавлены"
        )
        profession_name = profession.name
        description = (
            profession.desc if profession.desc else "<b>Описание не добавлено</b>"
        )
        return keywords_text, description, profession_name
    except Exception as e:
        logger.error(f"Error fetching profession data: {e}")
        return (
            "Ошибка при получении ключевых слов",
            "Ошибка при получении описания",
            "Неизвестная профессия",
        )


@router.message(Command("admin"), IsAdminFilter())
async def admin_cmd(message: Message):
    logger.debug("Entered admin_cmd handler")
    stopwords_text = await get_stopwords_text()
    await message.answer(
        LEXICON_PARSER["parser_main"].format(stopwords_text=stopwords_text),
        reply_markup=await professions_keyboard(),
    )
    logger.info("Admin command processed successfully")


@router.callback_query(IsAdminFilter(), F.data.startswith("ppage_"))
async def process_profession_pagination(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Prof.main)
    await callback.answer()
    page = int(callback.data.split("_")[1])
    await callback.message.edit_reply_markup(
        reply_markup=await professions_keyboard(page=page)
    )


@router.callback_query(IsAdminFilter(), F.data.startswith("kpage_"))
async def process_keyword_pagination(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Prof.main)
    await callback.answer()
    page = int(callback.data.split("_")[1])
    data = await state.get_data()
    profession_id = data.get("profession_id")
    await callback.message.edit_reply_markup(
        reply_markup=await keywords_keyboard(profession_id, page=page)
    )


@router.callback_query(IsAdminFilter(), F.data.startswith("swpage_"))
async def process_stopword_pagination(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Prof.main)
    await callback.answer()
    page = int(callback.data.split("_")[1])
    await callback.message.edit_reply_markup(
        reply_markup=await stopwords_keyboard(page=page)
    )


@router.callback_query(IsAdminFilter(), F.data.startswith("proff_"))
async def process_profession_selection(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Prof.main)
    profession_id = callback.data.split("_")[1]
    await state.update_data(profession_id=profession_id)

    keywords_text, description, profession_name = await get_keywords_and_desc(
        profession_id
    )

    await callback.message.edit_text(
        LEXICON_PARSER["choosen_profession_base"].format(
            profession_name=profession_name,
            profession_desc=description,
            keywords_text=keywords_text,
        ),
        reply_markup=await choosen_prof_keyboard(profession_id=profession_id),
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data == "add_keyword")
async def add_keyword(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        LEXICON_PARSER["add_keyword_prompt"],
        reply_markup=back_to_choosen_prof_kb,
    )
    await state.set_state(Prof.add_keyword)
    await callback.answer()


@router.message(Prof.add_keyword, IsAdminFilter())
async def process_new_keyword(
    message: Message, state: FSMContext, session: AsyncSession
):
    data = await state.get_data()
    new_keyword = " ".join(message.text.strip().split()[:-1])
    input_weight = (
        message.text.strip().split()[-1]
        if len(message.text.strip().split()) > 1
        else None
    )

    try:
        weight = float(input_weight)
    except (TypeError, ValueError):
        return await message.answer(
            LEXICON_PARSER["add_keyword_format_err"],
            reply_markup=back_to_choosen_prof_kb,
        )

    try:
        if not (0.1 <= float(weight) <= 1.0):
            raise ValueError("Вес должен быть между 0.1 и 1.0")
    except ValueError as e:
        await message.answer(
            LEXICON_PARSER["add_keyword_weight_err"],
            reply_markup=back_to_choosen_prof_kb,
        )
        return

    profession_id = data.get("profession_id")
    if not profession_id:
        await message.answer("Ошибка: не удалось получить ID профессии.")
        logger.error("Failed to get profession ID from state data")
        return

    success = await add_keyword_to_profession(
        session=session,
        profession_id=profession_id,
        word=new_keyword,
        weight=float(weight),
    )

    keywords_text, description, profession_name = await get_keywords_and_desc(
        profession_id
    )

    if success:
        await message.answer(
            LEXICON_PARSER["choosen_profession_after_add_keyword"].format(
                profession_name=profession_name,
                profession_desc=description,
                keywords_text=keywords_text,
                new_keyword=new_keyword,
                weight=weight,
            ),
            reply_markup=await choosen_prof_keyboard(profession_id),
        )
        logger.info(
            f"Added keyword '{new_keyword}' with weight {weight} to profession ID {profession_id}"
        )
    else:
        await message.answer(
            LEXICON_PARSER["choosen_profession_after_add_keyword_err"].format(
                profession_name=profession_name,
                profession_desc=description,
                keywords_text=keywords_text,
                new_keyword=new_keyword,
                weight=weight,
            ),
            reply_markup=await choosen_prof_keyboard(profession_id),
        )
        logger.error(
            f"Failed to add keyword '{new_keyword}' to profession ID {profession_id}"
        )

    await load_professions()


@router.callback_query(IsAdminFilter(), F.data == "back_to_proffs")
async def back_to_proffs_func(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Prof.main)
    stopwords_text = await get_stopwords_text()
    await callback.message.edit_text(
        LEXICON_PARSER["parser_main"].format(stopwords_text=stopwords_text),
        reply_markup=await professions_keyboard(),
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data == "delete_keyword")
async def delete_keyword(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    profession_id = data.get("profession_id")
    await callback.message.edit_text(
        LEXICON_PARSER["delete_keyword_prompt"],
        reply_markup=await keywords_keyboard(profession_id),
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("keyword_"))
async def process_delete_keyword(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    keyword_id = callback.data.split("_")[1]

    success = await db_delete_keyword(session=session, keyword_id=keyword_id)

    data = await state.get_data()
    profession_id = data.get("profession_id")

    keywords_text, description, profession_name = await get_keywords_and_desc(
        profession_id
    )

    if success:
        await callback.message.edit_text(
            LEXICON_PARSER["choosen_profession_after_delete_keyword"].format(
                profession_name=profession_name,
                profession_desc=description,
                keywords_text=keywords_text,
            ),
            reply_markup=await choosen_prof_keyboard(profession_id),
        )
    else:
        await callback.message.edit_text(
            LEXICON_PARSER["choosen_profession_after_delete_keyword_err"].format(
                profession_name=profession_name,
                profession_desc=description,
                keywords_text=keywords_text,
            ),
            reply_markup=await choosen_prof_keyboard(profession_id),
        )

    await load_professions()
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data == "add_proff")
async def add_profession(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        LEXICON_PARSER["add_profession_prompt"], reply_markup=back_to_proffs_kb
    )
    await state.set_state(Prof.add_profession)
    await callback.answer()


@router.message(Prof.add_profession, IsAdminFilter())
async def process_new_profession(
    message: Message, state: FSMContext, session: AsyncSession
):
    await state.update_data(new_profession=message.text)
    await message.answer(
        LEXICON_PARSER["add_profession_desc_prompt"].format(
            profession_name=message.text
        ),
        reply_markup=back_to_proffs_kb,
    )
    await state.set_state(Prof.adding_desc_main)


@router.message(Prof.adding_desc_main, IsAdminFilter())
async def process_new_profession_desc(
    message: Message, state: FSMContext, session: AsyncSession
):
    data = await state.get_data()
    new_profession = data.get("new_profession")
    description = message.text

    if not new_profession:
        await message.answer("Ошибка: не удалось получить название профессии.")
        logger.error("Failed to get new profession name from state data")
        return

    success = await db_add_profession(
        session=session,
        name=new_profession,
        desc=description,
    )
    stopwords_text = await get_stopwords_text()

    if success:
        await message.answer(
            LEXICON_PARSER["parser_main_after_add_profession"].format(
                profession_name=new_profession, stopwords_text=stopwords_text
            ),
            reply_markup=await professions_keyboard(),
        )
        logger.info(f"Added new profession '{new_profession}'")
    else:
        await message.answer(
            LEXICON_PARSER["parser_main_after_add_profession_err"].format(
                profession_name=new_profession, stopwords_text=stopwords_text
            ),
            reply_markup=await professions_keyboard(),
        )
        logger.error(f"Failed to add profession '{new_profession}'")

    await load_professions()


@router.callback_query(IsAdminFilter(), F.data == "delete_proff")
async def delete_profession(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    data = await state.get_data()
    profession_id = data.get("profession_id")

    stopwords_text = await get_stopwords_text()

    success = await db_delete_profession(session=session, profession_id=profession_id)
    if success:
        await callback.message.edit_text(
            LEXICON_PARSER["parser_main_after_delete_profession"].format(
                stopwords_text=stopwords_text
            )
        )
    else:
        await callback.message.edit_text(
            LEXICON_PARSER["parser_main_after_delete_profession_err"].format(
                stopwords_text=stopwords_text
            )
        )
    await load_professions()
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data == "delete_proffs_desc")
async def delete_profession_desc(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    data = await state.get_data()
    profession_id = data.get("profession_id")

    success = await db_delete_profession_desc(
        session=session, profession_id=profession_id
    )

    keywords_text, description, profession_name = await get_keywords_and_desc(
        profession_id
    )

    if success:
        await callback.message.edit_text(
            LEXICON_PARSER["choosen_profession_after_delete_proffs_desc"].format(
                profession_name=profession_name,
                profession_desc=description,
                keywords_text=keywords_text,
            ),
            reply_markup=await choosen_prof_keyboard(profession_id),
        )
    else:
        await callback.message.edit_text(
            LEXICON_PARSER["choosen_profession_after_delete_proffs_desc_err"].format(
                profession_name=profession_name,
                profession_desc=description,
                keywords_text=keywords_text,
            ),
            reply_markup=await choosen_prof_keyboard(profession_id),
        )
    await load_professions()
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data == "add_proffs_desc")
async def add_profession_desc(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    profession_id = data.get("profession_id")

    if not profession_id:
        await callback.message.edit_text("Ошибка: не удалось получить ID профессии.")
        return

    await callback.message.edit_text(
        LEXICON_PARSER["add_profession_desc_prompt"].format(
            profession_name=(await get_profession_by_id(profession_id)).name
        ),
        reply_markup=back_to_choosen_prof_kb,
    )
    await state.set_state(Prof.adding_desc_additional)
    await callback.answer()


@router.message(Prof.adding_desc_additional, IsAdminFilter())
async def process_new_profession_desc_additional(
    message: Message, state: FSMContext, session: AsyncSession
):
    data = await state.get_data()
    description = message.text
    profession_id = data.get("profession_id")

    if not profession_id:
        await message.answer("Ошибка: не удалось получить ID профессии.")
        return

    success = await db_add_profession_desc(
        session=session,
        profession_id=profession_id,
        desc=description,
    )

    keywords_text, description, profession_name = await get_keywords_and_desc(
        profession_id
    )

    if success:
        await message.answer(
            LEXICON_PARSER["choosen_profession_after_add_proffs_desc"].format(
                profession_name=profession_name,
                profession_desc=description,
                keywords_text=keywords_text,
            ),
            reply_markup=await choosen_prof_keyboard(profession_id),
        )
        logger.info(f"Updated description for profession ID {profession_id}")
    else:
        await message.answer(
            LEXICON_PARSER["choosen_profession_after_add_proffs_desc_err"].format(
                profession_name=profession_name,
                profession_desc=description,
                keywords_text=keywords_text,
            ),
            reply_markup=await choosen_prof_keyboard(profession_id),
        )
        logger.error(f"Failed to update description for profession ID {profession_id}")

    await load_professions()


@router.callback_query(IsAdminFilter(), F.data == "back_to_choosen_prof")
async def back_to_choosen_prof(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    profession_id = data.get("profession_id")

    keywords_text, description, profession_name = await get_keywords_and_desc(
        profession_id
    )

    await callback.message.edit_text(
        LEXICON_PARSER["choosen_profession_base"].format(
            profession_name=profession_name,
            profession_desc=description,
            keywords_text=keywords_text,
        ),
        reply_markup=await choosen_prof_keyboard(profession_id),
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data == "stopwords_add")
async def stopwords_add(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        LEXICON_PARSER["add_stopword_prompt"], reply_markup=back_to_proffs_kb
    )
    await state.set_state(Prof.adding_stopwords)
    await callback.answer()


@router.message(Prof.adding_stopwords, IsAdminFilter())
async def process_adding_stopwords(
    message: Message, state: FSMContext, session: AsyncSession
):
    stopword = message.text
    success = await db_add_stopword(session=session, word=stopword)

    stopwords_text = await get_stopwords_text()

    if success:
        await message.answer(
            LEXICON_PARSER["parser_main_after_add_stopword"].format(
                stopwords_text=stopwords_text, stopword=stopword
            ),
            reply_markup=await professions_keyboard(),
        )
        logger.info(f"Added stop-word '{stopword}'")
    else:
        await message.answer(
            LEXICON_PARSER["parser_main_after_add_stopword_err"].format(
                stopword=stopword
            ),
            reply_markup=await professions_keyboard(),
        )
        logger.error(f"Failed to add stop-word '{stopword}'")

    await load_stopwords()


@router.callback_query(IsAdminFilter(), F.data == "stopwords_delete")
async def stopwords_delete(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    await callback.message.edit_text(
        "Выберите стоп-слово для удаления:",
        reply_markup=await stopwords_keyboard(),
    )
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data.startswith("stopword_"))
async def process_delete_stopword(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    stopword_id = callback.data.split("_")[1]

    success = await db_delete_stopword(session=session, stopword_id=stopword_id)

    stopwords_text = await get_stopwords_text()

    if success:
        await callback.message.edit_text(
            LEXICON_PARSER["parser_main_after_delete_stopword"].format(
                stopwords_text=stopwords_text
            ),
            reply_markup=await professions_keyboard(),
        )
        logger.info(f"Deleted stop-word ID {stopword_id}")
    else:
        await callback.message.edit_text("Ошибка при удалении стоп-слова.")
        logger.error(f"Failed to delete stop-word ID {stopword_id}")

    await load_stopwords()
    await callback.answer()
