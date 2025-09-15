from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from app.usersDatabase import usrsdb
from app.states import Main
from app.bot_instance import bot, scheduler
from dotenv import load_dotenv
from lexicon import LEXICON_TEXTS, LEXICON_URLS
import os


from app.keyboards import (
    back_to_admin_keyboard
)

load_dotenv()
user = Router()





@user.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    text_log = "Данный пользователь нажал комманду /start"
    text = LEXICON_TEXTS["hello"]
    await message.answer(text, reply_markup=back_to_admin_keyboard)


