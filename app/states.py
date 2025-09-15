from aiogram.fsm.state import State, StatesGroup
    
class Main(StatesGroup):
    user_db_add = State()
    chat = State()
    
class Admin(StatesGroup):
    send_message = State()
    main = State()
    send_to_all = State()
    choose_user = State()
    new_name = State()
    
