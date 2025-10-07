from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

class Main(StatesGroup):
    main = State()
    add_email = State()
    change_email = State()
    activate_promo = State()
    payment_link = State()
    first_time_choose_prof = State()
    support = State()
    
