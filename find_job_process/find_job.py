import asyncio
from sentence_transformers import SentenceTransformer, util
from db.requests import stopwords_cache
from db.requests import get_all_professions_parser, get_all_stopwords
from db.database import Sessionmaker
from db.models import StopWord
from sqlalchemy.future import select
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

professions_cache: dict[str, any] = {}
professions_embeddings_cache: dict[str, any] = {}
stopwords_cache: set[str] = set()

def count_stop_words(text: str) -> int:
    """
    Считает количество совпавших стоп-слов в тексте.
    Логирует найденные стоп-слова.
    """
    text_lower = text.lower()
    text_words = set(re.findall(r"\b\w+\b", text_lower))  # разбиваем на слова
    found_words = stopwords_cache.intersection(text_words)
    #print(f"Stop words cache: {stopwords_cache}")
    #print(f"Words in text: {text_words}")
    #print(f"Found stop words: {found_words}")
    return len(found_words)


async def load_professions():
    """
    Загружаем все профессии и ключевые слова из БД и обновляем кэши:
    professions_cache и professions_embeddings_cache.
    """
    global professions_cache, professions_embeddings_cache

    professions = await get_all_professions_parser()

    # кеш с описаниями и ключевыми словами
    professions_cache = {
        p["name"]: {
            "desc": p.get("desc", ""),
            "keywords": p.get("keywords", {}),
        }
        for p in professions
    }

    # кеш с эмбеддингами описаний
    professions_embeddings_cache = {
        name: model.encode(data["desc"], convert_to_tensor=True)
        for name, data in professions_cache.items()
    }


def get_profession_embeddings() -> dict[str, any]:
    return professions_embeddings_cache



import re
import asyncio



async def contains_any_regex_async(text: str) -> bool:
    stopwords = await get_all_stopwords()
    keywords = [sw.word for sw in stopwords]
    
    pattern = re.compile("|".join(re.escape(k.lower()) for k in keywords), re.IGNORECASE)

    def search():
        matches = pattern.findall(text.lower())
        for match in matches:
            logger.info(f"Found stop word: {match}")
        return bool(matches)

    return await asyncio.to_thread(search)



async def analyze_vacancy(text: str, embedding_weight: float = 0.7) -> dict:
    stop_count = await contains_any_regex_async(text)
    if stop_count:
        return {"status": "blocked", "reason": f"{stop_count} stop words found"}

    lowered = text.lower()

    # --- очки по ключевым словам ---
    keyword_scores = {}
    for name, data in professions_cache.items():
        score = 0
        for kw, weight in data["keywords"].items():
            if kw.lower() in lowered:
                score += weight
        keyword_scores[name] = score
    #print(f"Очки по ключевым словам: {keyword_scores}")

    # --- сходство по эмбеддингам ---
    text_emb = model.encode(text, convert_to_tensor=True)
    embeddings = get_profession_embeddings()
    embedding_scores = {}
    for name, prof_emb in embeddings.items():
        sim = util.cos_sim(text_emb, prof_emb).item()
        embedding_scores[name] = sim
    #print(f"Сходство по эмбеддингам: {embedding_scores}")

    # --- итоговый рейтинг ---
    final_scores = {
        name: keyword_scores[name] + embedding_weight * embedding_scores[name]
        for name in professions_cache
    }
    #print(f"Итоговые рейтинги: {final_scores}")

    ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    return {"status": "ok", "ranked": ranked}

# === Пример использования ===
async def find_job_func(
    vacancy_text: str, embedding_weight: float = 0.7
):

    result = await analyze_vacancy(
        vacancy_text, embedding_weight=embedding_weight
    )

    if result["status"] == "blocked":
        #print(f"🚫 Вакансия заблокирована ({result['reason']})")
        return False

    vacancy_professions = [
        (prof, score) for prof, score in result["ranked"] if score > 2.0
    ]

    if not vacancy_professions:
        #print("⚠️ Вакансия не подходит ни под одну из профессий.")
        return False

    #print("🔎 Результаты анализа вакансии:"

    return vacancy_professions


# === Запуск ===
if __name__ == "__main__":
    professions = {
        "SMM-специалист": {
            "desc": "Работа с социальными сетями, продвижение брендов и проектов.",
            "keywords": {"smm": 2, "соцсети": 1, "instagram": 1, "facebook": 1},
        },
        "Копирайтер": {
            "desc": "Создание текстов для сайтов, блогов, соцсетей и рассылок.",
            "keywords": {"тексты": 2, "копирайтинг": 2, "статьи": 1, "контент": 1},
        },
    }

    text1 = "Требуется специалист по SMM для продвижения в Instagram"
    text2 = "Удаленная работа: казино, ставки на спорт, азартные игры, пари"

    asyncio.run(find_job_func(text1, professions))
    asyncio.run(find_job_func(text2, professions))


# --- Стоп-слова (можно вынести в БД) ---
STOP_WORDS = ["помогу", "изучу", "меня зовут", "возьму на себя", "ищу работу"]
