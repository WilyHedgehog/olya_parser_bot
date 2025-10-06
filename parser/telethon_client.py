from telethon import TelegramClient
from config.config import load_config

config = load_config()
app = TelegramClient("Telethon_UserBot", config.parser.api_id, config.parser.api_hash)