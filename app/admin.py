from aiogram import Router, F
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import Message, CallbackQuery
from collections import defaultdict
from aiogram.fsm.context import FSMContext
from app.usersDatabase import usrsdb
from app.states import Admin
from app.bot_instance import bot, scheduler
from datetime import datetime
import os, asyncio
from dotenv import load_dotenv


from app.keyboards import (
    back_to_user_keyboard,
    admin_panel_keyboard,
    generate_keywords_keyboard,
)

from app.parser_database import load_config, save_config


admin = Router()
load_dotenv()


async def find_user_in_base(message: Message):
    if message.text.isdigit():
        user = usrsdb.get_user(message.text)
        if user:
            return message.text, user["name"]
        else:
            await message.answer(
                "❌ Пользователь с таким ID не найден. Попробуйте снова."
            )
            return None
    else:
        user = usrsdb.get_user_by_username(message.text)
        if not user:
            await message.answer(
                "❌ Пользователь с таким ником не найден. Попробуйте снова."
            )
            return None
        return user["user_id"], user["name"]


async def echo_handler(message: Message):
    if message.text:
        await message.answer(message.text)

    elif message.photo:
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=message.photo[-1].file_id,
            caption=message.caption or "",
        )

    elif message.document:
        await bot.send_document(
            chat_id=message.chat.id,
            document=message.document.file_id,
            caption=message.caption or "",
        )

    elif message.video:
        await bot.send_video(
            chat_id=message.chat.id,
            video=message.video.file_id,
            caption=message.caption or "",
        )

    elif message.voice:
        await bot.send_voice(
            chat_id=message.chat.id,
            voice=message.voice.file_id,
            caption=message.caption or "",
        )

    elif message.sticker:
        await bot.send_sticker(chat_id=message.chat.id, sticker=message.sticker.file_id)

    else:
        await message.answer("⚠️ Этот тип сообщений я пока не умею повторять.")


@admin.callback_query(F.data == "admin_button_click")
async def send_to_client_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Admin.main)
    await callback.message.edit_text(
        "Админ-панель открыта", reply_markup=admin_panel_keyboard
    )
    await callback.answer()


@admin.callback_query(F.data == "send_to_client")
async def send_to_client_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Admin.send_message)
    await callback.message.edit_text(
        f"Введите сообщение для отправки:",
        reply_markup=back_to_user_keyboard,
    )


@admin.callback_query(F.data == "delete_word_button")
async def show_keywords(callback: CallbackQuery):
    await callback.message.edit_text(
        "Список ключевых слов:", reply_markup=generate_keywords_keyboard()
    )


@admin.callback_query(F.data.startswith("del_kw:"))
async def delete_keyword(callback: CallbackQuery):
    word = callback.data.split(":", 1)[1]

    config = load_config()
    if word in config["keywords"]:
        config["keywords"].remove(word)
        save_config(config)
        await callback.answer(f"Удалено: {word}")
    else:
        await callback.answer("Слово уже удалено", show_alert=True)

    # обновляем клавиатуру
    await callback.message.edit_reply_markup(reply_markup=generate_keywords_keyboard())
