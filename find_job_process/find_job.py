import asyncio
from sentence_transformers import SentenceTransformer, util
from db.requests import stopwords_cache
from db.requests import get_all_professions_parser
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
    print(f"Stop words cache: {stopwords_cache}")
    print(f"Words in text: {text_words}")
    print(f"Found stop words: {found_words}")
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


from sentence_transformers import util

async def load_stopwords():
    # если кэш уже есть, возвращаем его
    if hasattr(load_stopwords, "cache"):
        return load_stopwords.cache

    async with Sessionmaker() as session:
        result = await session.execute(select(StopWord))
        stopwords = result.scalars().all()

    load_stopwords.cache = {sw.word.lower() for sw in stopwords}
    print(f"Stopwords loaded: {len(load_stopwords.cache)}")
    return load_stopwords.cache


async def analyze_vacancy(text: str, embedding_weight: float = 0.7) -> dict:
    print("=== Анализ вакансии ===")
    print(f"Текст вакансии: {text[:100]}...")  # первые 100 символов

    # --- стоп-слова ---
    stopwords = await load_stopwords()
    words_in_text = {w.lower() for w in text.split()}
    found_stopwords = words_in_text & stopwords
    stop_count = len(found_stopwords)
    print(f"Stop words cache: {stopwords}")
    print(f"Words in text: {words_in_text}")
    print(f"Found stop words: {found_stopwords}")
    print(f"Количество стоп-слов: {stop_count}")
    if stop_count >= 1:
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
    print(f"Очки по ключевым словам: {keyword_scores}")

    # --- сходство по эмбеддингам ---
    text_emb = model.encode(text, convert_to_tensor=True)
    embeddings = get_profession_embeddings()
    embedding_scores = {}
    for name, prof_emb in embeddings.items():
        sim = util.cos_sim(text_emb, prof_emb).item()
        embedding_scores[name] = sim
    print(f"Сходство по эмбеддингам: {embedding_scores}")

    # --- итоговый рейтинг ---
    final_scores = {
        name: keyword_scores[name] + embedding_weight * embedding_scores[name]
        for name in professions_cache
    }
    print(f"Итоговые рейтинги: {final_scores}")

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
        print(f"🚫 Вакансия заблокирована ({result['reason']})")
        return False

    vacancy_professions = [
        (prof, score) for prof, score in result["ranked"] if score > 2.0
    ]

    if not vacancy_professions:
        print("⚠️ Вакансия не подходит ни под одну из профессий.")
        return False

    print("🔎 Результаты анализа вакансии:")
    for prof, score in vacancy_professions:
        print(f"  {prof}: {score:.3f}")

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
