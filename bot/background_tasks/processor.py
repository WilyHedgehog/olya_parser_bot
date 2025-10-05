import hashlib
import random
import logging
from main import app
from bot_setup import bot
from bot.utils import markdown_to_html, message_to_html, get_message_link, save_vacancy_hash, send_vacancy_to_users, get_delete_vacancy_kb
from db.requests import get_vacancy_by_hash, record_vacancy_sent
from find_job_process.find_job import find_job_func
from config.config import load_config

config = load_config()
logger = logging.getLogger(__name__)

processed_messages = set()

async def process_message(message):
    # Твоя текущая реализация process_message
    ...