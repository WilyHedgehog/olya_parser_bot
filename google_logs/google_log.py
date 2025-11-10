import gspread
import os
import json
import asyncio
from google.oauth2.service_account import Credentials
from config.config import load_config
from datetime import datetime
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

config = load_config()


SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

google_creds = config.google.api_key
google_creds_dict = json.loads(google_creds)

CREDS = Credentials.from_service_account_info(google_creds_dict, scopes=SCOPE)
client = gspread.authorize(CREDS)


spreadsheet = client.open("proonlinejob-bot")
worksheet_first = spreadsheet.sheet1
worksheet_second = spreadsheet.get_worksheet(1)
worksheet_third = spreadsheet.get_worksheet(2)


async def worksheet_append_row(
    user_id,
    time,
    name,
    action,
    text,
    vacancy_text=None,
    stopword=None,
    keyword=None,
    profession=None,
):
    if action == "delete_vacancy":
        await asyncio.to_thread(
            worksheet_first.append_row,
            [user_id, time, name, text, vacancy_text],
        )
    elif action == "add_stopword":
        await asyncio.to_thread(
            worksheet_second.append_row, [user_id, time, name, text, stopword]
        )
    elif action == "delete_stopword":
        await asyncio.to_thread(
            worksheet_second.append_row, [user_id, time, name, text, stopword]
        )
    elif action == "add_keyword":
        await asyncio.to_thread(
            worksheet_third.append_row,
            [user_id, time, name, text, keyword, profession],
        )
    elif action == "delete_keyword":
        await asyncio.to_thread(
            worksheet_third.append_row,
            [user_id, time, name, text, keyword, profession],
        )
        
        
async def worksheet_append_log(name, action, user_id=None, time=None, text=None, text2=None):
    await asyncio.to_thread(
        worksheet_third.append_row, [user_id, time, name, action, text, text2]
    )