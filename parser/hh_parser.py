import requests
from db.requests import get_all_professions_parser
from utils.bot_utils import send_message


async def hh_parser():
    #professions = await get_all_professions_parser()

    #prof_names = [item["name"] for item in professions]
    prof_names = ["технический специалист"]

    for prof in prof_names:
        vacancy = await get_hh_data(prof)
        
        name = vacancy.get("name", "Без названия")
        company = vacancy.get("employer", {}).get("name", "Компания не указана")
        city = vacancy.get("area", {}).get("name", "Регион не указан")
        salary = vacancy.get("salary")
        if salary:
            salary_text = f"{salary.get('from', '') or ''}–{salary.get('to', '') or ''} {salary.get('currency', '')}"
        else:
            salary_text = "Не указана"
        
        description = vacancy.get("description", "")
        requirement = vacancy.get("snippet", {}).get("requirement", "")
        responsibility = vacancy.get("snippet", {}).get("responsibility", "")
        link = vacancy.get("alternate_url", "")
        
        formatted = (
            f"📌 *{name}*\n"
            f"🏢 {company}\n"
            f"📍 {city}\n"
            f"💰 Зарплата: {salary_text}\n\n"
            f"🧠 Требования: {requirement}\n"
            f"💼 Обязанности: {responsibility}\n\n"
            f"🔗 [Открыть вакансию]({link})"
        )
        
        await send_message(1058760541, formatted)
        
        

    
    
def get_hh_data(prof):
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": f"{prof}",
        "area": 113,  # вся Россия
        "order_by": "publication_time",
        "per_page": 10
    }

    response = requests.get(url, params=params)
    data = response.json()
    return data

