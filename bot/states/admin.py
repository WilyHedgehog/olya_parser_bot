from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

class Prof(StatesGroup):
    adding_desc_main = State()
    adding_desc_additional = State()
    main = State()
    add_keyword = State()
    add_profession = State()
    adding_stopwords = State()
    

class Admin(StatesGroup):
    main = State()
    file_id = State()
    add_mailing = State()
    mailing_file_id = State()
    mailing_datetime = State()
    mailing_text = State()
    mailing_name = State()
    add_admin = State()
    send_message = State()