import requests
import json
from db.requests import get_all_professions_parser
from utils.bot_utils import send_message
from utils.nats_connect import get_nats_connection
from logging import getLogger

logger = getLogger(__name__)


async def hh_parser():
    #professions = await get_all_professions_parser()

    #prof_names = [item["name"] for item in professions]
    prof_names = ["технический специалист онлайн школы"]

    for prof in prof_names:
        vacancies = get_hh_vacancies(prof)
        
        for vac in vacancies:
            name = vac.get("name", "Без названия")
            company = vac.get("employer", {}).get("name", "Компания не указана")
            city = vac.get("area", {}).get("name", "Регион не указан")
            salary = vac.get("salary")
            if salary:
                salary_text = f"{salary.get('from', '') or ''}–{salary.get('to', '') or ''} {salary.get('currency', '')}"
            else:
                salary_text = "Не указана"

            requirement = vac.get("snippet", {}).get("requirement", "")
            responsibility = vac.get("snippet", {}).get("responsibility", "")
            link = vac.get("alternate_url", "")

            formatted = (
                f"📌 *{name}*\n"
                f"🏢 {company}\n"
                f"📍 {city}\n"
                f"💰 Зарплата: {salary_text}\n\n"
                f"🧠 Требования: {requirement}\n"
                f"💼 Обязанности: {responsibility}\n\n"
                f"🔗 [Открыть вакансию]({link})"
            )
            
            try:
                nc, js = await get_nats_connection()
            except Exception as e:
                logger.error(f"❌ Ошибка подключения к NATS: {e}")
                return
            
            try:
                await js.publish("vacancy.queue", formatted.encode(), headers={"flag": str(prof)})
                logger.info(f"📤 Отправлена вакансия из HH по профессии '{prof}' в очередь")
            except Exception as e:
                logger.error(f"❌ Ошибка публикации задачи в NATS: {e}")

            await send_message(1058760541, formatted)
        

def get_hh_vacancies(prof, per_page=1):
    """Возвращает список вакансий для профессии по всей России"""
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": f"NAME:({prof})",
        "area": 113,  # вся Россия
        "order_by": "publication_time",
        "per_page": per_page
    }
    response = requests.get(url, params=params)
    data = response.json()
    return data.get("items", [])  # список вакансий
