import logging
import pickle
from aiogram import F, Router
from aiogram.filters import Command, MagicData
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.background_tasks.dunning import schedule_dunning, cancel_dunning_tasks
from bot.background_tasks.aps_utils import clear
from bot.background_tasks.aps_utils import cancel_mailing_by_id
from bot.background_tasks.delete_old_vacancy import schedule_vacancy_clear
from bot.background_tasks.sand_two_hours_vacancy import schedule_sand_two_hours
from google_logs.google_log import worksheet_append_row
from parser.hh_parser import hh_parser
from bot_setup import bot
from datetime import datetime
from zoneinfo import ZoneInfo
from bot.keyboards.admin_keyboard import (
    professions_keyboard,
    keywords_keyboard,
    choosen_prof_keyboard,
    stopwords_keyboard,
    admin_keyboard,
    mailing_settings_keyboard,
    get_delete_mailing_kb,
    delete_admin_keyboard,
    stopwords_pagination_keyboard,
    background_tasks_start_kb,
    back_to_choosen_prof_kb,
    back_to_proffs_kb,
    back_to_admin_main_kb
)
from bot.states.admin import Prof, Admin
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
    delete_vacancy_everywhere,
    update_user_access,
    is_super_admin,
    get_admins_list,
    add_to_admins,
    remove_from_admins,
    get_vac_points,
    return_vacancy_by_id,
    save_in_trash,
    get_all_user_info,
)
from db.crud import (
    get_upcoming_mailings,
    cancel_admin_mailings,
)

from find_job_process.find_job import load_professions

from sqlalchemy.ext.asyncio import AsyncSession
from bot.lexicon.lexicon import LEXICON_PARSER, LEXICON_ADMIN


MAX_MESSAGE_LENGTH = 3500

logger = logging.getLogger(__name__)
logger.info("Admin handler module loaded")
router = Router(name="admin commands router")
MOSCOW_TZ = ZoneInfo("Europe/Moscow")
# Фильтр: роутер доступен только chat id, равному admin_id,
# который передан в диспетчер
# router.message.filter(MagicData(F.event.chat.id == F.admin_id))  # noqa



@router.callback_query(IsAdminFilter(), F.data.startswith("stoppage_"))
async def change_text_page(callback: CallbackQuery, state: FSMContext):
    pages = await get_stopwords_text_pages()

    current_page = int(callback.data.split("_")[1])
    total_pages = len(pages)

    keyboard = stopwords_pagination_keyboard(current_page, total_pages)
    await callback.message.edit_text(
        text=pages[current_page - 1],
        reply_markup=keyboard
    )
    await callback.answer()


async def close_clock(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception as e:
        pass

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


async def try_delete_message_old(message: Message, state: FSMContext):
    try:
        await message.bot.delete_message(
            chat_id=message.chat.id, message_id=await get_reply_id(state)
        )
    except Exception as e:
        pass


async def try_delete_message(message: Message):
    try:
        await message.delete()
    except Exception as e:
        pass


async def get_reply_id(state: FSMContext):
    data = await state.get_data()
    return data.get("reply_id")


@router.callback_query(F.data == "back_to_admin")
@router.message(Command("admin"), IsAdminFilter())
async def admin_cmd(message: Message | CallbackQuery, state: FSMContext):
    await try_delete_message(message)
    await try_delete_message_old(message, state)
    
    
    if await is_super_admin(message.from_user.id):
        super_admin = True
    else:
        super_admin = False
    
    if isinstance(message, Message):
        reply = await message.answer(
            LEXICON_ADMIN["admin_welcome"],
            reply_markup=admin_keyboard(super_admin=super_admin),
        )
    else:
        reply = await message.message.edit_text(
            LEXICON_ADMIN["admin_welcome"],
            reply_markup=admin_keyboard(super_admin=super_admin),
        )
    await state.set_state(Admin.main)
    await state.update_data(reply_id=reply.message_id)


@router.callback_query(IsAdminFilter(), F.data == "parser_menu")
async def parser_menu_button(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception as e:
        pass
    try:
        await callback.message.edit_text(
            LEXICON_PARSER["parser_main"],
            reply_markup=await professions_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error updating parser menu: {e}")


@router.callback_query(IsAdminFilter(), F.data.startswith("ppage_"))
async def process_profession_pagination(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Prof.main)
    await close_clock(callback)
    page = int(callback.data.split("_")[1])
    try:
        await callback.message.edit_reply_markup(
            reply_markup=await professions_keyboard(page=page)
        )
    except Exception as e:
        logger.error(f"Error updating professions keyboard: {e}")


@router.callback_query(IsAdminFilter(), F.data.startswith("kpage_"))
async def process_keyword_pagination(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Prof.main)
    await close_clock(callback)
    page = int(callback.data.split("_")[1])
    data = await state.get_data()
    profession_id = data.get("profession_id")
    try:
        await callback.message.edit_reply_markup(
            reply_markup=await keywords_keyboard(profession_id, page=page)
        )
    except Exception as e:
        logger.error(f"Error updating keywords keyboard: {e}")


@router.callback_query(IsAdminFilter(), F.data.startswith("swpage_"))
async def process_stopword_pagination(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Prof.main)
    await close_clock(callback)
    page = int(callback.data.split("_")[1])
    try:
        await callback.message.edit_reply_markup(
            reply_markup=await stopwords_keyboard(page=page)
        )
    except Exception as e:
        logger.error(f"Error updating stopwords keyboard: {e}")


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
    await close_clock(callback)


@router.callback_query(IsAdminFilter(), F.data == "add_keyword")
async def add_keyword(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        LEXICON_PARSER["add_keyword_prompt"],
        reply_markup=back_to_choosen_prof_kb,
    )
    await state.set_state(Prof.add_keyword)
    await close_clock(callback)


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
    await callback.message.edit_text(
        LEXICON_PARSER["parser_main"],
        reply_markup=await professions_keyboard(),
    )
    await close_clock(callback)


@router.callback_query(IsAdminFilter(), F.data == "delete_keyword")
async def delete_keyword(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    profession_id = data.get("profession_id")
    await callback.message.edit_text(
        LEXICON_PARSER["delete_keyword_prompt"],
        reply_markup=await keywords_keyboard(profession_id),
    )
    await close_clock(callback)


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
    await close_clock(callback)


@router.callback_query(IsAdminFilter(), F.data.startswith("kwpage_"))
async def process_keyword_pagination(callback: CallbackQuery, state: FSMContext):
    await close_clock(callback)
    await state.set_state(Prof.main)
    page = int(callback.data.split("_")[-1])
    data = await state.get_data()
    profession_id = data.get("profession_id")
    try:
        await callback.message.edit_reply_markup(
            reply_markup=await keywords_keyboard(profession_id, page=page)
        )
    except Exception as e:
        logger.error(f"Error updating keywords keyboard: {e}")


@router.callback_query(IsAdminFilter(), F.data == "add_proff")
async def add_profession(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        LEXICON_PARSER["add_profession_prompt"], reply_markup=back_to_proffs_kb
    )
    await state.set_state(Prof.add_profession)
    await close_clock(callback)


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

    if success:
        await message.answer(
            LEXICON_PARSER["parser_main_after_add_profession"].format(
                profession_name=new_profession
            ),
            reply_markup=await professions_keyboard(),
        )
        logger.info(f"Added new profession '{new_profession}'")
    else:
        await message.answer(
            LEXICON_PARSER["parser_main_after_add_profession_err"].format(
                profession_name=new_profession
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


    success = await db_delete_profession(session=session, profession_id=profession_id)
    if success:
        await callback.message.edit_text(
            LEXICON_PARSER["parser_main_after_delete_profession"]
        )
    else:
        await callback.message.edit_text(
            LEXICON_PARSER["parser_main_after_delete_profession_err"]
        )
    await load_professions()
    await close_clock(callback)


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
    await close_clock(callback)


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
    await close_clock(callback)


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
    await close_clock(callback)


@router.callback_query(IsAdminFilter(), F.data == "stopwords_add")
async def stopwords_add(callback: CallbackQuery, state: FSMContext):
    await close_clock(callback)
    try:
        await callback.message.edit_text(
            LEXICON_PARSER["add_stopword_prompt"], reply_markup=back_to_proffs_kb
        )
        await state.set_state(Prof.adding_stopwords)
    except Exception as e:
        logger.error(f"Error in stopwords_add: {e}")


@router.message(Prof.adding_stopwords, IsAdminFilter())
async def process_adding_stopwords(
    message: Message, state: FSMContext, session: AsyncSession
):
    stopword = message.text
    success = await db_add_stopword(session=session, word=stopword)

    if success:
        await worksheet_append_row(
                user_id=message.from_user.id,
                time=datetime.now(MOSCOW_TZ).strftime("%Y-%m-%d %H:%M:%S"),
                name=message.from_user.full_name,
                action="add_stopword",
                text=f"Добавлено стоп-слово.",
                stopword=stopword,
            )
        await message.answer(
            LEXICON_PARSER["parser_main_after_add_stopword"].format(
                stopword=stopword
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
    await state.set_state(Prof.main)


@router.callback_query(IsAdminFilter(), F.data == "stopwords_delete")
async def stopwords_delete(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    await callback.message.edit_text(
        "Выберите стоп-слово для удаления:",
        reply_markup=await stopwords_keyboard(),
    )
    await close_clock(callback)

@router.callback_query(IsAdminFilter(), F.data.startswith("stopword_"))
async def process_delete_stopword(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    stopword_id = callback.data.split("_")[1]
    await close_clock(callback)

    success = await db_delete_stopword(session=session, stopword_id=stopword_id)

    if success:
        await callback.message.edit_text(
            LEXICON_PARSER["parser_main_after_delete_stopword"],
            reply_markup=await professions_keyboard(),
        )
        logger.info(f"Deleted stop-word ID {stopword_id}")
    else:
        await callback.message.edit_text("Ошибка при удалении стоп-слова.")
        logger.error(f"Failed to delete stop-word ID {stopword_id}")

    await load_stopwords()


@router.callback_query(IsAdminFilter(), F.data.startswith("delete_vacancy_"))
async def process_delete_vacancy(callback: CallbackQuery, session: AsyncSession):
    try:
        await callback.answer()
    except Exception as e:
        logger.error(f"Error answering callback: {e}")
        pass
    vacancy_id = callback.data.split("_")[2]
    vacancy = await return_vacancy_by_id(vacancy_id, session)
    vacancy_text = vacancy.text
    try:
        result = await delete_vacancy_everywhere(session, vacancy_id)
        if result:
            await save_in_trash(vacancy_text, vacancy.hash)
            await callback.message.answer("Вакансия успешно удалена.")
            logger.info(f"Vacancy {vacancy_id} deleted successfully.")
            await worksheet_append_row(
                user_id=callback.from_user.id,
                time=datetime.now(MOSCOW_TZ).strftime("%Y-%m-%d %H:%M:%S"),
                name=callback.from_user.full_name,
                action="delete_vacancy",
                text=f"Вакансия была удалена.",
                vacancy_text=vacancy_text,
            )
        else:
            await callback.message.answer("Ошибка при удалении вакансии.")
            logger.error(f"Failed to delete vacancy {vacancy_id}.")
    except Exception as e:
        logger.error(f"Exception while deleting vacancy {vacancy_id}: {e}")
        await callback.message.answer("Произошла ошибка при удалении вакансии.")


@router.message(Command("adminsub"), IsAdminFilter())
async def admin_subs_cmd(message: Message):
    await update_user_access(message.from_user.id, True)


@router.callback_query(IsAdminFilter(), F.data == "get_file_id")
async def get_file_id(callback: CallbackQuery, state: FSMContext):
    await close_clock(callback)
    await callback.message.edit_text(
        "Отправьте мне любое медиа-сообщение (голосовое, аудио, документ, видео или фото), и я верну вам его file_id.",
        reply_markup=back_to_admin_main_kb,
    )
    await state.set_state(Admin.file_id)


@router.message(Admin.file_id, IsAdminFilter())
async def process_file_id(message: Message, state: FSMContext):
    file_id = get_file_id_from_message(message)
    if file_id:
        await message.answer(f"file_id: {file_id}", reply_markup=back_to_admin_main_kb)
    else:
        await message.answer(
            "<b>Ошибка:</b> в этом сообщении нет поддерживаемого медиа-контента.\nДля новой попытки вернитесь в админ-панель и зайдите снова.",
            reply_markup=back_to_admin_main_kb,
        )
    await state.set_state(Admin.main)
    


def get_file_id_from_message(message: Message) -> str | None:
    """
    Получает file_id из сообщения Telegram.
    Поддерживаются: voice, audio, document, video, photo (берет последний размер)
    """
    if message.voice:
        return message.voice.file_id
    if message.audio:
        return message.audio.file_id
    if message.document:
        return message.document.file_id
    if message.video:
        return message.video.file_id
    if message.photo:
        # Telegram присылает список фото разного размера, берем самый большой
        return message.photo[-1].file_id
    return None


@router.callback_query(IsAdminFilter(), F.data == "back_to_mailing")
@router.callback_query(IsAdminFilter(), F.data == "mailing_settings")
async def mailing_settings(callback: CallbackQuery, state: FSMContext):
    mailings = await get_upcoming_mailings()
    if mailings:
        upcoming_mailings = "\n".join(
            f"- Название: {m.task_name}, Запланировано на: {m.run_at.strftime('%Y-%m-%d %H:%M')}, Сообщение: {m.message[:30]}..."
            for m in mailings
        )
    else:
        upcoming_mailings = "Ближайшие запланированные рассылки отсутствуют."
        
    await close_clock(callback)
    await callback.message.edit_text(
        LEXICON_ADMIN["mailing_menu"].format(upcoming_mailings=upcoming_mailings),
        reply_markup=mailing_settings_keyboard()
    )
    await state.set_state(Admin.main)
    
    
@router.callback_query(IsAdminFilter(), F.data == "delete_mailing")
async def delete_mailing(callback: CallbackQuery, state: FSMContext):
    await close_clock(callback)
    try:
        await callback.message.edit_text(
            "Выберите рассылку для удаления:",
            reply_markup=await get_delete_mailing_kb()
        )
    except Exception as e:
        logger.error(f"Error in delete_mailing: {e}")
        
        
@router.callback_query(IsAdminFilter(), F.data.startswith("delete_mailing_"))
async def process_delete_mailing(callback: CallbackQuery, state: FSMContext):
    mailing_id = callback.data.split("_")[-1]
    await close_clock(callback)

    success = await cancel_admin_mailings(mailing_id)

    if success:
        await callback.message.edit_text(
            "Рассылка успешно удалена.",
            reply_markup=mailing_settings_keyboard()
        )
        logger.info(f"Mailing {mailing_id} deleted successfully.")
    else:
        await callback.message.edit_text(
            "Ошибка при удалении рассылки.",
            reply_markup=mailing_settings_keyboard()
        )
        logger.error(f"Failed to delete mailing {mailing_id}.")
        
        
@router.callback_query(IsAdminFilter(), F.data == "mpage_")
async def process_mailing_pagination(callback: CallbackQuery, state: FSMContext):
    await close_clock(callback)
    await state.set_state(Admin.main)
    page = int(callback.data.split("_")[1])
    try:
        await callback.message.edit_reply_markup(
            reply_markup=await get_delete_mailing_kb(page=page)
        )
    except Exception as e:
        logger.error(f"Error updating mailings keyboard: {e}")
        
        
@router.callback_query(IsAdminFilter(), F.data == "add_delete_admin")
async def add_delete_admin(callback: CallbackQuery, state: FSMContext): 
    await close_clock(callback)
    await callback.message.edit_text(
        "Отправьте мне <b>id</b> пользователя, чтобы добавить его в администраторы.\n\n"
        "Чтобы удалить администратора, выберите его на клавиатуре ниже.",
        reply_markup=await delete_admin_keyboard()
    )
    await state.set_state(Admin.add_admin)
    
    
@router.message(Admin.add_admin, IsAdminFilter())
async def process_add_admin(message: Message, state: FSMContext):
    try:
        new_admin_id = int(message.text.strip())
    except ValueError:
        await message.answer("Ошибка: id должен быть числом. Попробуйте еще раз.")
        return
    
    admins_list = await get_admins_list()
    if new_admin_id in [admin.telegram_id for admin in admins_list]:
        await message.answer("Этот пользователь уже является администратором.")
        return

    success = await add_to_admins(new_admin_id)
    if success:
        await message.answer(f"Пользователь с id {new_admin_id} успешно добавлен в администраторы.", reply_markup=back_to_admin_main_kb)
        logger.info(f"User {new_admin_id} added as admin.")
    else:
        await message.answer("Ошибка при добавлении пользователя в администраторы.", reply_markup=back_to_admin_main_kb)
        logger.error(f"Failed to add user {new_admin_id} as admin.")
    await state.set_state(Admin.main)
    
    
@router.callback_query(IsAdminFilter(), F.data.startswith("delete_admin_"))
async def process_delete_admin(callback: CallbackQuery, state: FSMContext):
    admin_id = int(callback.data.split("_")[-1])
    await close_clock(callback)

    success = await remove_from_admins(admin_id)

    if success:
        await callback.message.edit_text(
            f"Администратор с id {admin_id} успешно удален.",
            reply_markup=back_to_admin_main_kb
        )
        logger.info(f"Admin {admin_id} deleted successfully.")
    else:
        await callback.message.edit_text(
            "Ошибка при удалении администратора.",
            reply_markup=back_to_admin_main_kb
        )
        logger.error(f"Failed to delete admin {admin_id}.")
        
        
import textwrap

async def get_stopwords_text_pages():
    text = await get_stopwords_text()
    if not text:
        return []

    # Разбиваем текст на страницы по длине, не разрывая слова
    pages = textwrap.wrap(text, width=MAX_MESSAGE_LENGTH, replace_whitespace=False)
    return pages

@router.callback_query(IsAdminFilter(), F.data == "show_stopwords")
async def show_paginated_text(callback: CallbackQuery):
    logger.info("show_stopwords")
    pages = await get_stopwords_text_pages()
    logger.info(pages)
    total_pages = len(pages)
    current_page = 1

    keyboard = stopwords_pagination_keyboard(current_page, total_pages)

    await callback.message.edit_text(pages[current_page - 1], reply_markup=keyboard)
    await callback.answer()
    
@router.callback_query(IsAdminFilter(), F.data == "stats")
async def show_stats(callback: CallbackQuery):
    raw_text = await get_vac_points()
    text = "Перед вами статистика вакансий:\n\n"
    for key, value in raw_text.items():
        text += f"<b>{key}:</b> {value}\n"
    await callback.message.edit_text(text, reply_markup=back_to_admin_main_kb)
    await callback.answer()


@router.callback_query(IsAdminFilter(), F.data == "background_tasks")
async def show_background_tasks(callback: CallbackQuery):
    text = "Запуск фоновых задач кнопкой:\n\n"
    await callback.message.edit_text(text, reply_markup=background_tasks_start_kb())
    await callback.answer()
    
    
@router.callback_query(IsAdminFilter(), F.data == "autodelete_vacancy")
async def autodelete_vacancy(callback: CallbackQuery):
    await schedule_vacancy_clear()
    text = "Фоновая задача запущена\n\n"
    await callback.message.edit_text(
        text,
        reply_markup=back_to_admin_main_kb
    )
    await callback.answer()
    
    
@router.callback_query(IsAdminFilter(), F.data == "two_hours_send_vacancy")
async def two_hours_send_vacancy(callback: CallbackQuery):
    await schedule_sand_two_hours()
    text = "Фоновая задача запущена\n\n"
    await callback.message.edit_text(
        text,
        reply_markup=back_to_admin_main_kb
    )
    await callback.answer()
    

@router.message(Command("hh"), IsAdminFilter())
async def start_hh(message: Message):
    await hh_parser()
    
    
@router.message(Command("uinfo"), IsAdminFilter())
async def admin_get_user_info(message: Message):
    args = message.text.split()  # получаем аргументы команды
    if len(args) < 2:
        await message.reply("Использование: /uinfo <user_id>")
        return

    user_id = int(args[1])
    try:
        chat = await bot.get_chat(user_id)
        user = await get_all_user_info(user_id)
        if user:
            text = f"Данные о пользователе:\n\nUsername: @{chat.username if chat.username else '—'}\n"
            for par in user:
                text += f"{par}: {user[par]}\n"
            await message.answer(text)
        else:
            await message.reply("Пользователь не найден.")
    except Exception as e:
        logger.error("Failed to get user info: %s", e)