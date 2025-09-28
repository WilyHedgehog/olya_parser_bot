from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

class BotStates(StatesGroup):
    reply_id = State()
    
