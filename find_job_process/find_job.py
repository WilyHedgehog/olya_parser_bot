import asyncio
from sentence_transformers import SentenceTransformer, util
from db.requests import stopwords_cache
from db.requests import get_all_professions_parser
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

professions_cache: dict[str, any] = {}
professions_embeddings_cache: dict[str, any] = {}
stopwords_cache: set[str] = set()

def count_stop_words(text: str) -> int:
    """
    Считает количество совпавших стоп-слов в тексте.
    """
    text_lower = text.lower()
    return sum(1 for stop_word in stopwords_cache if stop_word in text_lower)


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


async def analyze_vacancy(text: str, embedding_weight: float = 0.7) -> dict:
    """
    Анализ вакансии через кэш профессий и ключевых слов.
    embedding_weight регулирует важность эмбеддингов.
    """
    # --- стоп-слова ---
    stop_count = count_stop_words(text)
    if stop_count >= 3:
        return {"status": "blocked", "reason": f"{stop_count} stop words found"}

    lowered = text.lower()

    # --- очки по ключевым словам ---
    keyword_scores = {
        name: sum(weight for kw, weight in data["keywords"].items() if kw in lowered)
        for name, data in professions_cache.items()
    }

    # --- сходство по эмбеддингам ---
    text_emb = model.encode(text, convert_to_tensor=True)
    embeddings = get_profession_embeddings()
    embedding_scores = {
        name: util.cos_sim(text_emb, prof_emb).item()
        for name, prof_emb in embeddings.items()
    }

    # --- итоговый рейтинг ---
    final_scores = {
        name: keyword_scores[name] + embedding_weight * embedding_scores[name]
        for name in professions_cache
    }

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
        (prof, score) for prof, score in result["ranked"] if score > 1.0
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
