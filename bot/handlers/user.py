import logging
import re
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import zoneinfo
from aiogram.fsm.context import FSMContext
from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.deep_linking import create_start_link
from bot_setup import bot

from google_logs.google_log import worksheet_append_log

MOSCOW_TZ = zoneinfo.ZoneInfo("Europe/Moscow")

from getcourse.gc_api import (
    gc_request_auto_payment_link,
    gc_request_no_auto_payment_link,
)

from db.requests import (
    db_change_email,
    update_delivery_mode,
    update_users_profession,
    get_all_professions,
    update_all_users_professions,
    get_user_subscription_until,
    activate_promo,
    get_user_by_telegram_id,
    get_all_mails,
    get_pricing_data,
    update_user_pricing_data,
    get_all_users_professions,
    update_autopay_status,
    get_promo_24_hours,
    save_support_message,
    get_user_delivery_mode,
    get_payment_text,
)

from find_job_process.job_dispatcher import send_vacancy_from_queue
from bot.filters.filters import (
    UserNoEmail,
    UserHaveEmail,
    UserHaveProfessions,
    IsNewUser,
)
from bot.lexicon.lexicon import LEXICON_USER, LEXICON_ADMIN
from config.config import load_config
from bot.states.user import Main
from bot.states.admin import Prof
from bot.keyboards.user_keyboard import (
    confirm_email_button_kb,
    start_payment_process_kb,
    back_to_main_kb,
    is_auto_payment_kb,
    get_all_professions_kb,
    get_delivery_mode_kb,
    get_main_reply_kb,
    get_pay_subscription_kb,
    need_admin_for_author_kb,
)
from bot.keyboards.admin_keyboard import get_vacancy_url_kb

# Инициализируем логгер модуля
logger = logging.getLogger(__name__)
config = load_config()

# Инициализируем роутер уровня модуля
router = Router(name="main router")


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email))


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


async def get_user_professions_list(user_id: int):
    professions_list_name = []
    professions = await get_all_professions()
    for user_prof in await get_all_users_professions(user_id):
        if user_prof.is_selected:
            for prof in professions:
                if str(prof.id) == str(user_prof.profession_id):
                    professions_list_name.append(prof.name)
    return professions_list_name


@router.message(CommandStart(deep_link=True), IsNewUser())
async def start_cmd_new_user(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    command: CommandStart,  # <-- вот тут прилетает объект команды
):
    payload = command.args  # в aiogram3 вместо message.args
    if payload and payload.startswith("referral_"):
        try:
            referrer_id = int(payload.split("_")[1])
            if referrer_id != message.from_user.id:
                await get_promo_24_hours(session=session, user_id=referrer_id)
        except Exception:
            pass

    await _start_cmd_no_prof(message, state, is_new=True)


@router.message(CommandStart(), ~IsNewUser(), ~UserHaveProfessions())
async def start_cmd_no_prof(message: Message, state: FSMContext):
    await _start_cmd_no_prof(message, state, is_new=False)


async def _start_cmd_no_prof(message: Message, state: FSMContext, is_new: bool):
    photo = FSInputFile("bot/assets/Добро пожаловать!-1.png")
    # await try_delete_message_old(message, state)

    await try_delete_message(message)

    if is_new:
        caption = LEXICON_USER["first_time_start_cmd"]
    else:
        caption = LEXICON_USER["no_professions_start_cmd"]

    reply = await message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=await get_all_professions_kb(user_id=message.from_user.id, page=1),
    )
    await state.update_data(reply_id=reply.message_id, current_page=1)
    await state.set_state(Main.first_time_choose_prof)


@router.message(CommandStart(), ~IsNewUser(), UserHaveProfessions())
async def start_cmd_existing_user(
    message: Message, state: FSMContext, session: AsyncSession
):
    photo = FSInputFile("bot/assets/Добро пожаловать!-1.png")
    await try_delete_message_old(message, state)

    await try_delete_message(message)

    professions_list_name = await get_user_professions_list(message.from_user.id)

    try:
        data = await state.get_data()
        user_delivery_mode = data.get("user_delivery_mode")
        await update_delivery_mode(session, message.from_user.id, user_delivery_mode)
    except Exception as e:
        logger.error(
            f"Error updating delivery mode for user {message.from_user.id}: {e}"
        )
        pass

    reply = await message.answer_photo(
        photo=photo,
        caption=LEXICON_USER["start_cmd"].format(
            subscription_status=await get_user_subscription_until(message.from_user.id),
            professions_list=(
                ", ".join(professions_list_name)
                if professions_list_name
                else "Не выбраны"
            ),
        ),
        reply_markup=await get_main_reply_kb(user_id=message.from_user.id),
    )
    await state.update_data(reply_id=reply.message_id)
    await state.set_state(Main.main)


@router.callback_query(F.data.startswith("dmode_"), Main.main)
async def change_delivery_mode(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    data = await state.get_data()
    user_mode = data.get("delivery_mode")  # текущий сохранённый режим

    mode = callback.data.split("_", 1)[1]
    logger.info(f"User {callback.from_user.id} changed delivery mode to {mode}🍏")

    # Если нажали на уже выбранный режим
    if mode == user_mode:
        return

    # if mode == "two_hours":
    #    await callback.answer("Режим скоро будет доступен", show_alert=True)
    #    return

    # Сохраняем новый режим в базе
    await update_delivery_mode(session, callback.from_user.id, mode)
    await callback.answer()
    # Обновляем стейт
    await state.update_data(delivery_mode=mode)
    try:
        # Обновляем клавиатуру
        await callback.message.edit_reply_markup(
            reply_markup=await get_delivery_mode_kb(user_id=callback.from_user.id)
        )
    except Exception as e:
        pass


@router.callback_query(F.data.startswith("profession_"), Main.main)
@router.callback_query(F.data.startswith("profession_"), Main.first_time_choose_prof)
async def change_user_chosen_professions(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    await callback.answer()
    profession_id = callback.data.split("_")[2]
    check = callback.data.split("_")[1]  # chosen или unchosen

    if check == "chosen":
        # Снимаем выбор
        await update_users_profession(
            session, callback.from_user.id, profession_id, is_selected=False
        )
    else:
        # Выбираем профессию
        await update_users_profession(
            session, callback.from_user.id, profession_id, is_selected=True
        )

    # Обновляем клавиатуру
    data = await state.get_data()
    page = data.get("current_page")
    try:
        await callback.message.edit_reply_markup(
            reply_markup=await get_all_professions_kb(
                user_id=callback.from_user.id, page=page
            )
        )
    except Exception as e:
        logger.error(f"Error updating professions keyboard: {e}")


@router.callback_query(F.data == "back_to_start_menu")
@router.callback_query(F.data == "back_to_main")
@router.callback_query(F.data == "confirm_choice", Main.main)
@router.callback_query(
    F.data == "confirm_choice", Main.first_time_choose_prof, UserHaveProfessions()
)
async def confirm_choice(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    try:
        data = await state.get_data()
        user_delivery_mode = data.get("user_delivery_mode")
        if user_delivery_mode:
            await update_delivery_mode(
                session, callback.from_user.id, user_delivery_mode
            )
        else:
            pass
    except Exception as e:
        logger.error(f"Error updating delivery mode on confirm choice: {e}")

    photo = FSInputFile("bot/assets/Добро пожаловать!-1.png")

    await callback.answer()
    professions_list_name = await get_user_professions_list(callback.from_user.id)

    reply = await callback.message.answer_photo(
        photo=photo,
        caption=LEXICON_USER["start_cmd"].format(
            subscription_status=await get_user_subscription_until(
                callback.from_user.id
            ),
            professions_list=(
                ", ".join(professions_list_name)
                if professions_list_name
                else "Не выбраны"
            ),
        ),
        reply_markup=await get_main_reply_kb(user_id=callback.from_user.id),
    )
    try:
        await callback.message.bot.delete_message(
            chat_id=callback.message.chat.id, message_id=await get_reply_id(state)
        )
    except Exception as e:
        pass
    await state.update_data(reply_id=reply.message_id)
    await state.set_state(Main.main)


@router.callback_query(F.data == "confirm_choice", Main.first_time_choose_prof)
async def confirm_choice(callback: CallbackQuery, state: FSMContext):
    await callback.answer(LEXICON_USER["no_professions_chosen"], show_alert=True)
    await callback.answer()


@router.callback_query(F.data.startswith("all_professions_"), Main.main)
@router.callback_query(
    F.data.startswith("all_professions_"), Main.first_time_choose_prof
)
async def choose_all_professions(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    await callback.answer()
    professions = await get_all_professions()
    profession_ids = [str(prof.id) for prof in professions]
    action = callback.data.split("_")[2]  # choose или dismiss

    if action == "dismiss":
        await update_all_users_professions(
            session, callback.from_user.id, profession_ids, False
        )
    else:
        await update_all_users_professions(
            session, callback.from_user.id, profession_ids, True
        )

    data = await state.get_data()
    page = data.get("current_page")

    try:
        await callback.message.edit_reply_markup(
            reply_markup=await get_all_professions_kb(
                user_id=callback.from_user.id, page=page
            )
        )
    except Exception as e:
        pass


@router.callback_query(F.data.startswith("uppage_"), Main.first_time_choose_prof)
@router.callback_query(F.data.startswith("uppage_"), Main.main)
async def change_page(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    page = int(callback.data.split("_")[1])
    try:
        await callback.message.edit_reply_markup(
            reply_markup=await get_all_professions_kb(
                user_id=callback.from_user.id, page=page
            )
        )
        await state.update_data({"current_page": page})
    except Exception as e:
        logger.error(f"Error changing page: {e}")


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "---")
async def noop(callback: CallbackQuery):
    await callback.answer()


@router.message(F.text == "🛠️ Настройки профессий 🛠️", Main.main)
async def settings_professions(message: Message, state: FSMContext):
    await try_delete_message(message)
    await try_delete_message_old(message, state)
    reply = await message.answer(
        LEXICON_USER["settings_professions"],
        reply_markup=await get_all_professions_kb(user_id=message.from_user.id, page=1),
    )
    await state.update_data(reply_id=reply.message_id, current_page=1)


@router.message(F.text == "📬 Настройки параметров доставки вакансий 📬", Main.main)
async def settings_delivery(message: Message, state: FSMContext):
    await try_delete_message(message)
    await try_delete_message_old(message, state)
    reply = await message.answer(
        LEXICON_USER["settings_delivery"],
        reply_markup=await get_delivery_mode_kb(user_id=message.from_user.id),
    )
    await state.update_data(reply_id=reply.message_id)


@router.message(F.text == "💳 Купить подписку 💳", Main.main, UserNoEmail())
@router.message(F.text == "🎟️ Активировать промокод 🎟️", Main.main, UserNoEmail())
async def add_email_prompt(message: Message, state: FSMContext):
    if F.text == "🎟️ Активировать промокод 🎟️":
        await state.update_data(from_promo=True)
    else:
        await state.update_data(from_promo=False)
    await try_delete_message(message)
    await try_delete_message_old(message, state)
    reply = await message.answer(
        LEXICON_USER["no_email_prompt"],
        reply_markup=back_to_main_kb,
    )
    await state.update_data(reply_id=reply.message_id)
    await state.set_state(Main.add_email)  # Переходим в состояние ожидания email


@router.callback_query(F.data.startswith("check_author_"))
async def check_author(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.split("_")[-1]
    # сообщение в котором говортися, что буду звать админа
    await callback.answer(
        "Для уточнения автора вакансии позовут админа. Подведите запрос нажав на кнопку 'Позвать админа' под вакансией.",
        show_alert=True,
    )
    try:
        await callback.message.edit_reply_markup(
            reply_markup=await need_admin_for_author_kb(vacancy_id)
        )
    except Exception as e:
        logger.error(f"Error updating reply markup: {e}")
    await callback.answer()


@router.callback_query(F.data.startswith("need_admin_for_author_"))
async def check_author_admin(callback: CallbackQuery, state: FSMContext):
    vacancy_id = callback.data.split("_")[-1]
    await callback.answer(
        "Запрос на уточнение автора вакансии получен. Мы свяжемся с вами в ближайшее время.",
        show_alert=True,
    )
    if callback.from_user.username is None:
        username = "Не указан"
    else:
        username = "@" + callback.from_user.username

    await bot.send_message(
        chat_id=config.bot.support_chat_id,
        text=LEXICON_ADMIN["need_author"].format(
            vacancy_id=vacancy_id, user_id=callback.from_user.id, username=username
        ),
        reply_markup=await get_vacancy_url_kb(vacancy_id),
    )


@router.message(Main.add_email, F.text)
async def add_email(message: Message, state: FSMContext):
    await try_delete_message_old(message, state)

    if message.text.lower() in [mail.lower() for mail in await get_all_mails()]:
        await try_delete_message(message)
        reply = await message.answer(LEXICON_USER["add_email_exists"])
        await state.update_data(reply_id=reply.message_id)
        return

    await try_delete_message(message)
    email = message.text.lower()
    await state.update_data(email=email)
    reply = await message.answer(
        LEXICON_USER["add_email_confirm"].format(email=email),
        reply_markup=confirm_email_button_kb,
    )
    await state.update_data(reply_id=reply.message_id)


@router.callback_query(F.data == "confirm_email", Main.add_email)
async def confirm_email(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    user_data = await state.get_data()
    email = user_data.get("email")
    if not is_valid_email(email):
        await callback.answer(
            "Некорректный email. Попробуйте еще раз.", show_alert=True
        )
        await state.set_state(Main.add_email)
        return
    if not email:
        await callback.message.edit_text(LEXICON_USER["add_email_fail"])
        await state.set_state(Main.add_email)
        return

    result = await db_change_email(session, callback.from_user.id, email)
    if result:
        try:
            await callback.message.bot.delete_message(
                chat_id=callback.message.chat.id, message_id=await get_reply_id(state)
            )
        except Exception as e:
            pass
        await state.set_state(Main.main)
        if user_data.get("from_promo"):
            await activate_promo_code_from_callback(callback, state)
        else:
            await buy_subscription(callback, state)


async def _start_activate_promo(message: Message, state: FSMContext):
    await try_delete_message(message)
    await try_delete_message_old(message, state)
    reply = await message.answer(
        "Пожалуйста, введите ваш промокод.", reply_markup=back_to_main_kb
    )
    await state.update_data(reply_id=reply.message_id)
    await state.set_state(Main.activate_promo)


@router.message(F.text == "🎟️ Активировать промокод 🎟️", Main.main, UserHaveEmail())
async def activate_promo_code(message: Message, state: FSMContext):
    await _start_activate_promo(message, state)


async def activate_promo_code_from_callback(callback: CallbackQuery, state: FSMContext):
    await _start_activate_promo(callback.message, state)


@router.message(Main.activate_promo, F.text)
async def process_promo_code(
    message: Message, state: FSMContext, session: AsyncSession
):
    try:
        await message.bot.delete_message(
            chat_id=message.chat.id, message_id=await get_reply_id(state)
        )
    except Exception as e:
        pass
    await try_delete_message(message)
    promo_code = message.text.strip()

    text, is_success = await activate_promo(session, message.from_user.id, promo_code)
    photo = FSInputFile("bot/assets/Промокод активирован!-1.png")

    if is_success:
        reply = await message.answer_photo(
            photo=photo, caption=text, reply_markup=back_to_main_kb
        )
        await worksheet_append_log(
            name=message.from_user.full_name,
            action="Промокод активирован!",
            user_id=message.from_user.id,
            time=datetime.now(MOSCOW_TZ).strftime("%d-%m-%Y %H:%M:%S"),
            text=f"Аквивирован промокод: {promo_code}",
        )
    else:
        reply = await message.answer(text, reply_markup=back_to_main_kb)

    await state.update_data(reply_id=reply.message_id)
    await state.set_state(Main.main)  # Возвращаемся в основное состояние


async def _start_buy_subscription(message: Message, state: FSMContext):
    await try_delete_message(message)
    await try_delete_message_old(message, state)
    photo = FSInputFile("bot/assets/Тарифы и доступ 🔑-1.png")
    until_the_end_of_the_day = (
        datetime.now(MOSCOW_TZ)
        .replace(hour=23, minute=59, second=59)
        .strftime("%H:%M %d.%m.%Y")
    )
    caption = await get_payment_text()
    reply = await message.answer_photo(
        photo=photo,
        caption=caption.format(until_the_end_of_the_day=until_the_end_of_the_day),
        reply_markup=start_payment_process_kb,
    )
    await state.update_data(reply_id=reply.message_id)
    await state.set_state(Main.payment_link)


@router.message(F.text == "💳 Купить подписку 💳", Main.main, UserHaveEmail())
async def buy_subscription(message: Message, state: FSMContext):
    await _start_buy_subscription(message, state)


async def buy_subscription_from_callback(callback: CallbackQuery, state: FSMContext):
    await _start_buy_subscription(callback.message, state)


@router.callback_query(F.data == "start_payment_process_3_months", Main.payment_link)
@router.callback_query(F.data == "start_payment_process_1_month", Main.payment_link)
async def pay_subscription(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.bot.delete_message(
            chat_id=callback.message.chat.id, message_id=await get_reply_id(state)
        )
    except Exception as e:
        pass
    if callback.data == "start_payment_process_1_month":
        await state.update_data(chosen_plan="1_month")
    else:
        await state.update_data(chosen_plan="3_months")

    reply = await callback.message.answer(
        LEXICON_USER["buy_subscription_second_stage"], reply_markup=is_auto_payment_kb
    )
    await state.update_data(reply_id=reply.message_id)


@router.callback_query(F.data == "auto_payment_true", Main.payment_link)
async def pay_subscription_auto(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chosen_plan = data.get("chosen_plan")
    await callback.answer()
    if not chosen_plan:
        await callback.answer("Произошла ошибка, попробуйте снова.")
        return

    user = await get_user_by_telegram_id(callback.from_user.id)
    try:
        await update_autopay_status(callback.from_user.id, True)

    except Exception as e:
        pass

    offer_code, offer_id = await get_pricing_data(
        user_id=callback.from_user.id, chosen_plan=chosen_plan
    )

    payment_link = await gc_request_auto_payment_link(
        email=user.mail,
        offer_code=offer_code,
        offer_id=offer_id,
    )

    await update_user_pricing_data(callback.from_user.id, offer_code)

    reply = await callback.message.edit_text(
        LEXICON_USER["buy_subscription_link"].format(payment_link=payment_link),
        disable_web_page_preview=True,
        reply_markup=await get_pay_subscription_kb(payment_link),
    )

    await worksheet_append_log(
        name=callback.from_user.full_name,
        action="Создан заказ",
        user_id=callback.from_user.id,
        text=user.mail,
        text2=chosen_plan,
        time=datetime.now(MOSCOW_TZ).strftime("%d-%m-%Y %H:%M:%S"),
    )

    await state.set_state(Main.main)
    await state.update_data(reply_id=reply.message_id)


@router.callback_query(F.data == "auto_payment_false", Main.payment_link)
async def pay_subscription_no_auto(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chosen_plan = data.get("chosen_plan")
    await callback.answer()
    if not chosen_plan:
        await callback.answer("Произошла ошибка, попробуйте снова.")
        return

    user = await get_user_by_telegram_id(callback.from_user.id)

    try:
        await update_autopay_status(callback.from_user.id, False)
    except Exception as e:
        pass

    offer_code, offer_id = await get_pricing_data(
        user_id=callback.from_user.id, chosen_plan=chosen_plan
    )

    payment_link = await gc_request_no_auto_payment_link(
        email=user.mail,
        offer_code=offer_code,
        offer_id=offer_id,
    )

    await update_user_pricing_data(
        telegram_id=callback.from_user.id, offer_code=offer_code, offer_id=offer_id
    )

    reply = await callback.message.edit_text(
        LEXICON_USER["buy_subscription_link"].format(payment_link=payment_link),
        disable_web_page_preview=True,
        reply_markup=await get_pay_subscription_kb(payment_link),
    )

    await worksheet_append_log(
        name=callback.from_user.full_name,
        action="Создан заказ",
        user_id=callback.from_user.id,
        text=user.mail,
        text2=chosen_plan,
        time=datetime.now(MOSCOW_TZ).strftime("%d-%m-%Y %H:%M:%S"),
    )

    await state.set_state(Main.main)
    await state.update_data(reply_id=reply.message_id)


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.bot.delete_message(
            chat_id=callback.message.chat.id, message_id=await get_reply_id(state)
        )
    except Exception as e:
        pass
    await state.set_state(Main.main)


@router.message(F.text == "Получить накопленные вакансии", Main.main)
async def get_earned_vacancies(message: Message, state: FSMContext):
    await try_delete_message_old(message, state)
    await try_delete_message(message)
    await send_vacancy_from_queue(message.from_user.id)


@router.message(F.text == "👫 Пригласить друга 👭", Main.main)
async def referal(message: Message, state: FSMContext):
    await try_delete_message_old(message, state)
    await try_delete_message(message)
    link = await create_start_link(
        bot=message.bot, payload=f"referral_{message.from_user.id}"
    )
    photo = FSInputFile("bot/assets/Приводи друзей-1.png")
    reply = await message.answer_photo(
        photo=photo,
        caption=LEXICON_USER["referal"].format(referral_link=link),
        reply_markup=back_to_main_kb,
    )
    await state.update_data(reply_id=reply.message_id)


@router.message(F.text == "🆘 Обратиться в поддержку 🆘", Main.main)
@router.message(Command("support"), Main.main)
async def support_cmd(message: Message, state: FSMContext, session: AsyncSession):
    await try_delete_message_old(message, state)
    await try_delete_message(message)
    await state.set_state(Main.support)
    reply = await message.answer(
        LEXICON_USER["support_cmd"], reply_markup=back_to_main_kb
    )
    user_delivery_mode = await get_user_delivery_mode(message.from_user.id)
    await update_delivery_mode(session, message.from_user.id, "support")
    await state.update_data(user_delivery_mode=user_delivery_mode)
    await state.update_data(reply_id=reply.message_id)


@router.message(Main.support)
async def support_message(message: Message, state: FSMContext, session: AsyncSession):
    await bot.send_message(
        chat_id=config.bot.support_chat_id,
        text=f"💬 Новое сообщение в поддержку от {message.from_user.full_name}\nID пользователя: {message.from_user.id}",
    )
    fwd = await bot.copy_message(
        chat_id=config.bot.support_chat_id,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
    await save_support_message(
        session=session,
        user_id=message.from_user.id,
        user_message_id=message.message_id,
        admin_chat_message_id=fwd.message_id,
    )
    reply = await message.answer(
        LEXICON_USER["support_received"], reply_markup=back_to_main_kb
    )
    await state.update_data(reply_id=reply.message_id)


@router.message(Command("help"))
@router.message(Command("help"), Main.main)
async def help_cmd(message: Message, state: FSMContext):
    await try_delete_message_old(message, state)
    await try_delete_message(message)
    await state.set_state(Main.main)
    reply = await message.answer(LEXICON_USER["help_cmd"], reply_markup=back_to_main_kb)
    await state.update_data(reply_id=reply.message_id)


@router.message(
    F.text == "Активировать новый промокод можно только после окончания имеющегося",
    Main.main,
)
async def promo_no_active(message: Message):
    await try_delete_message(message)


@router.message(F.text, Prof.main)
@router.message(F.text, Main.main)
@router.message(F.text)
async def handle_text_message(message: Message, state: FSMContext):
    await try_delete_message(message)
