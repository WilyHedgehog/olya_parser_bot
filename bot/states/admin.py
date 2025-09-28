from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

class Prof(StatesGroup):
    adding_desc_main = State()
    adding_desc_additional = State()
    main = State()
    add_keyword = State()
    add_profession = State()
    adding_stopwords = State()
    
