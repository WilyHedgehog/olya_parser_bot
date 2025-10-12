from aiogram import Router
from bot.keyboards.add_mail_keyboard import (
    is_mail_with_file,
    is_mail_with_keyboard,
    keyboards_for_mailings,
    mailing_segments_keyboard,
    get_mailing_keyboard,
    back_to_mailing_kb,
    final_add_mail_kb,
    confirm_mailing_kb,
)
from db.requests import (
    get_all_professions,
)
from utils.bot_utils import send_message, send_photo
from bot.background_tasks.admin_mailing import set_admin_mailing
from aiogram import F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from bot.filters.filters import IsAdminFilter
from bot.states.admin import Admin
from bot.lexicon.lexicon import LEXICON_ADMIN
from logging import getLogger
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


router = Router(name="add mailing router")
logger = getLogger(__name__)


async def generate_segments_for_mailing():
    # словарь с полными данными
    mailing_dict = {
        "Все пользователи": {"selected": False, "date": None},
        "Все с подпиской": {"selected": False, "date": None},
        "Все без подписки": {"selected": False, "date": None},
        "У кого кончилась подписка": {"selected": False, "date": None},
    }

    professions = await get_all_professions()
    if professions:
        for i, prof in enumerate(professions):
            mailing_dict[prof.name] = {"selected": False, "date": None}

    # создаём словарь для коротких ID
    segment_ids = {name: str(i) for i, name in enumerate(mailing_dict.keys())}

    return mailing_dict, segment_ids


@router.callback_query(IsAdminFilter(), F.data == "add_mailing")
async def process_add_mailing(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Admin.add_mailing)
    try:
        await callback.message.edit_text(
            LEXICON_ADMIN["add_mailing_stg1"], reply_markup=is_mail_with_file()
        )
    except Exception as e:
        logger.error(f"Error in process_add_mailing: {e}")


@router.callback_query(IsAdminFilter(), F.data == "with_file", Admin.add_mailing)
async def process_with_file(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Admin.mailing_file_id)
    try:
        await callback.message.edit_text(
            LEXICON_ADMIN["add_mailing_get_id"], reply_markup=back_to_mailing_kb
        )
    except Exception as e:
        logger.error(f"Error in process_with_file: {e}")


@router.message(IsAdminFilter(), F.text, Admin.mailing_file_id)
@router.callback_query(IsAdminFilter(), F.data == "without_file", Admin.add_mailing)
async def process_without_file_or_file_id(
    message: Message | CallbackQuery, state: FSMContext
):
    if isinstance(message, Message):
        file_id = message.text
        await state.update_data(mailing_file_id=file_id)
        await state.set_state(Admin.mailing_text)
        try:
            await message.answer(
                LEXICON_ADMIN["add_mailing_stg2"], reply_markup=is_mail_with_keyboard()
            )
        except Exception as e:
            logger.error(f"Error in process_without_file_or_file_id: {e}")
            return

    else:
        await message.answer()
        file_id = None
        await state.update_data(mailing_file_id=file_id)
        await state.set_state(Admin.mailing_text)
        try:
            await message.message.edit_text(
                LEXICON_ADMIN["add_mailing_stg2"], reply_markup=is_mail_with_keyboard()
            )
        except Exception as e:
            logger.error(f"Error in process_without_file_or_file_id: {e}")
            return


@router.callback_query(IsAdminFilter(), F.data == "with_kb", Admin.mailing_text)
async def process_with_keyboard(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.edit_text(
            LEXICON_ADMIN["add_mailing_choose_kb"],
            reply_markup=keyboards_for_mailings(),
        )
    except Exception as e:
        logger.error(f"Error in process_with_keyboard: {e}")


@router.callback_query(
    IsAdminFilter(), F.data.startswith("mail_kb_"), Admin.mailing_text
)
@router.callback_query(IsAdminFilter(), F.data == "without_kb", Admin.mailing_text)
async def process_after_keyboard_choice(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    keyboard_choice = (
        callback.data.split("_")[-1] if callback.data.startswith("mail_kb_") else None
    )
    await state.update_data(mailing_keyboard=keyboard_choice)

    mailing_segments, segment_ids = await generate_segments_for_mailing()
    await state.update_data(mailing_segments=mailing_segments, segment_ids=segment_ids)

    try:
        await callback.message.edit_text(
            LEXICON_ADMIN["add_mailing_stg3"],
            reply_markup=mailing_segments_keyboard(mailing_segments, segment_ids),
        )
    except Exception as e:
        logger.error(f"Error in process_after_keyboard_choice: {e}")


@router.callback_query(
    IsAdminFilter(), F.data.startswith(("prof_", "base_")), Admin.mailing_text
)
async def process_segment_selection(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    mailing_segments = data.get("mailing_segments", {})
    segment_ids = data.get("segment_ids", {})

    segment_id = callback.data.split("_")[1]
    segment_name = next(
        (name for name, sid in segment_ids.items() if sid == segment_id), None
    )
    if not segment_name or segment_name not in mailing_segments:
        logger.error(f"Segment {segment_id} not found in mailing_segments")
        return

    mailing_segments[segment_name]["selected"] = not mailing_segments[segment_name]["selected"]
    await state.update_data(mailing_segments=mailing_segments)

    # сохраняем текущую страницу, чтобы кнопки не "прыгают"
    current_page = data.get("current_page", 1)
    try:
        await callback.message.edit_reply_markup(
            reply_markup=mailing_segments_keyboard(
                mailing_segments, segment_ids, page=current_page
            )
        )
    except Exception as e:
        logger.error(f"Error in process_segment_selection: {e}")


@router.callback_query(
    IsAdminFilter(), F.data.startswith("mailing_seg_page_"), Admin.mailing_text
)
async def process_segment_page_change(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    page = int(callback.data.split("_")[-1])
    data = await state.get_data()
    mailing_segments = data.get("mailing_segments", {})
    segment_ids = data.get("segment_ids", {})

    try:
        await callback.message.edit_reply_markup(
            reply_markup=mailing_segments_keyboard(
                mailing_segments, segment_ids, page=page
            )
        )
    except Exception as e:
        logger.error(f"Error in process_segment_page_change: {e}")


@router.callback_query(
    IsAdminFilter(), F.data == "confirm_segments", Admin.mailing_text
)
async def process_confirm_segments(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        LEXICON_ADMIN["add_mailing_stg4"], reply_markup=back_to_mailing_kb
    )
    await state.set_state(Admin.mailing_datetime)


@router.message(IsAdminFilter(), F.text, Admin.mailing_datetime)
async def process_mailing_datetime(message: Message, state: FSMContext):
    datetime_str = message.text

    if not datetime_str:
        await message.answer(
            LEXICON_ADMIN["add_mailing_stg4_error1"], reply_markup=back_to_mailing_kb
        )
        return

    # В формате ДД.ММ.ГГГГ ЧЧ:ММ
    try:
        mailing_datetime = datetime.strptime(datetime_str, "%d.%m.%Y %H:%M").replace(
            tzinfo=MOSCOW_TZ
        )
    except ValueError:
        await message.answer(
            LEXICON_ADMIN["add_mailing_stg4_error2"], reply_markup=back_to_mailing_kb
        )
        return

    if mailing_datetime < datetime.now(MOSCOW_TZ) + timedelta(minutes=10):
        await message.answer(
            LEXICON_ADMIN["add_mailing_stg4_error3"],
            reply_markup=back_to_mailing_kb,
        )
        return

    try:
        mailing_datetime_obj = datetime.strptime(datetime_str, "%d.%m.%Y %H:%M").replace(
            tzinfo=MOSCOW_TZ
        )
    except ValueError:
        await message.answer(
            LEXICON_ADMIN["add_mailing_stg4_error4"], reply_markup=back_to_mailing_kb
        )
        return
    await state.update_data(mailing_datetime=mailing_datetime_obj)
    await message.answer(
        LEXICON_ADMIN["add_mailing_stg5"], reply_markup=back_to_mailing_kb
    )
    await state.set_state(Admin.mailing_text)


@router.message(IsAdminFilter(), F.text, Admin.mailing_text)
async def process_mailing_text(message: Message, state: FSMContext):
    mailing_text = message.text
    if not mailing_text:
        await message.answer(
            LEXICON_ADMIN["add_mailing_stg5_error"], reply_markup=back_to_mailing_kb
        )
        return

    await state.update_data(mailing_text=mailing_text)
    await state.set_state(Admin.add_mailing)

    await message.answer(
        LEXICON_ADMIN["add_mailing_stg6"], reply_markup=back_to_mailing_kb
    )
    await state.set_state(Admin.mailing_name)


@router.message(IsAdminFilter(), F.text, Admin.mailing_name)
async def process_mailing_name(message: Message, state: FSMContext):
    mailing_name = message.text
    if not mailing_name:
        await message.answer(
            LEXICON_ADMIN["add_mailing_stg6_error"], reply_markup=back_to_mailing_kb
        )
        return
    await state.update_data(mailing_name=mailing_name)
    await state.set_state(Admin.add_mailing)

    data = await state.get_data()
    file_id = data.get("mailing_file_id")
    keyboard_choice = data.get("mailing_keyboard")
    mailing_datetime = data.get("mailing_datetime")
    mailing_segments = data.get("mailing_segments", {})
    
    if isinstance(mailing_datetime, str):
        mailing_datetime = datetime.fromisoformat(mailing_datetime)

    selected_segments = [seg for seg, selected in mailing_segments.items() if selected]
    segments_str = (
        ", ".join(selected_segments) if selected_segments else "Нет сегментов"
    )

    await message.answer(
        LEXICON_ADMIN["add_mailing_confirm"].format(
            mailing_name=mailing_name,
            run_at=mailing_datetime.strftime("%d.%m.%Y %H:%M"),
            user_categories=segments_str,
            file_info=file_id if file_id else "Нет файла",
            keyboard_info=keyboard_choice if keyboard_choice else "Без клавиатуры",
        ),
        reply_markup=final_add_mail_kb,
    )


@router.callback_query(
    IsAdminFilter(), F.data == "next_step_mailing", Admin.add_mailing
)
async def process_next_step_mailing(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Admin.add_mailing)
    data = await state.get_data()
    file_id = data.get("mailing_file_id")
    mailing_text = data.get("mailing_text")
    keyboard_choice = data.get("mailing_keyboard")
    
    reply_markup = (
        await get_mailing_keyboard(keyboard_choice) if keyboard_choice else None
    )

    if file_id and keyboard_choice:
        await send_photo(
            chat_id=callback.from_user.id,
            file_id=file_id,
            caption=mailing_text,
            reply_markup=reply_markup,
        )
    elif file_id and not keyboard_choice:
        await send_photo(
            chat_id=callback.from_user.id, file_id=file_id, caption=mailing_text
        )
    elif keyboard_choice:
        await send_photo(
            chat_id=callback.from_user.id,
            file_id=file_id,
            caption=mailing_text,
            reply_markup=reply_markup,
        )
    else:
        await send_message(
            chat_id=callback.from_user.id,
            text=mailing_text,
        )

    await callback.message.answer(
        LEXICON_ADMIN["add_mailing_final"], reply_markup=confirm_mailing_kb
    )


@router.callback_query(IsAdminFilter(), F.data == "confirm_mailing", Admin.add_mailing)
async def process_confirm_mailing(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    mailing_name = data.get("mailing_name")
    mailing_text = data.get("mailing_text")
    file_id = data.get("mailing_file_id")
    keyboard_choice = data.get("mailing_keyboard")
    mailing_datetime = data.get("mailing_datetime")
    mailing_segments = data.get("mailing_segments", {})
    
    if isinstance(mailing_datetime, str):
        mailing_datetime = datetime.fromisoformat(mailing_datetime)

    selected_segments = [seg for seg, selected in mailing_segments.items() if selected]
    if not selected_segments:
        await callback.message.answer(
            "Ошибка: не выбран ни один сегмент. Пожалуйста, начните заново.",
            reply_markup=back_to_mailing_kb,
        )
        return

    await set_admin_mailing(
        mailing_datetime=mailing_datetime,
        message=mailing_text,
        file_id=file_id,
        keyboard=keyboard_choice,
        segment=selected_segments,
        task_name=mailing_name,
    )
    await callback.message.edit_text(
        "✅ Рассылка запланирована успешно!", reply_markup=back_to_mailing_kb
    )
