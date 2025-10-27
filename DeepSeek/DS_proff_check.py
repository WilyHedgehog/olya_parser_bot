# Please install OpenAI SDK first: `pip3 install openai`
import os
from openai import OpenAI
from config.config import load_config
from utils.bot_send_mes_queue import send_message
config = load_config()
api = config.deepseek.api_key

client = OpenAI(api_key=api, base_url="https://api.deepseek.com")

async def ai_proff_check(text, proff):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "Ты анализатор вакансий. Твоя задача проанализировать текст. Если это вакансия и она совпадает со специализацией, то ты возращаешь '1'. Если это не вакансия, а что-то другое (например резюме) или если вакансия не совпадает со специализацией, то ты возращаешь '0'. Ответ должен состочть только из 1 символа - или 1 или 0"},
            {"role": "user", "content": f"Текст: {text}\nСпециализация: {proff}"},
        ],
        stream=False
    )
    text = f"Текст: {text}\nСпециализация: {proff}"
    await send_message(-4822276897, response.choices[0].message.content)
    await send_message(-4822276897, text)
    return response.choices[0].message.content