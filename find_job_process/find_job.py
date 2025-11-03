import asyncio
from sentence_transformers import SentenceTransformer, util
from db.requests import stopwords_cache
from db.requests import get_all_professions_parser, get_all_stopwords
from db.database import Sessionmaker
from db.models import StopWord
from utils.bot_utils import send_message
from sqlalchemy.future import select
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

professions_cache: dict[str, any] = {}
professions_embeddings_cache: dict[str, any] = {}
stopwords_cache: set[str] = set()
stop_embeddings = set()


STOP_EMBEDDINGS_ADS = [
    "Подпишись на мой канал",
    "Реклама — залог успеха",
    "Пиар и продвижение в социальных сетях",
    "Помогу вам развить бизнес",
    "Оказываю услуги по продвижению",
    "Продвижение аккаунтов Instagram и Telegram",
    "Реклама в телеграм каналах",
    "Сотрудничество и реклама",
    "Заработай 1000 рублей в день",
    "Работа без вложений",
    "Доход на крипте и инвестициях",
    "Пройди по ссылке и получи бонус",
    "Заработок без опыта и знаний",
    "Подписывайся, чтобы узнать больше",
    "Бесплатный курс по заработку",
]

STOP_EMBEDDINGS_RESUME = [
    "Готов работать удаленно",
    "Рассмотрю любые предложения",
    "Мое резюме прикреплено ниже",
    "Опыт работы 3 года",
    "Меня зовут Анна, я маркетолог",
    "Готов к переезду и командировкам",
    "Ищу стажировку",
    "Мой опыт в IT больше 5 лет",
    "Хочу развиваться в этой сфере",
    "Рассмотрю офферы",
    "Пишите, если ищете дизайнера",
    "Готов к тестовому заданию",
]


STOP_EMBEDDINGS_SCAM = [
    "Гарантированный доход без риска",
    "Инвестиции с быстрой прибылью",
    "Деньги на карту за регистрацию",
    "Пиши в личку, расскажу как заработать",
    "Проверенная схема заработка",
    "Никаких вложений, только прибыль",
    "Схема обогащения без опыта",
    "Реферальная программа с бонусами",
    "Зарабатывай, не выходя из дома",
    "Крипта растет, успей вложиться",
    "Ставки и казино — быстрые деньги",
    "Только сегодня — акция и бонус",
    "Розыгрыш и бесплатные призы",
]


STOP_EMBEDDINGS_EDU = [
    "Запишись на курс по дизайну",
    "Обучаю копирайтингу с нуля",
    "Мастер-класс для начинающих",
    "Вебинар о том, как заработать онлайн",
    "Бесплатный интенсив по маркетингу",
    "Прокачай свои навыки SMM",
    "Обучение таргетингу и рекламе",
    "Новый поток курса по Python",
    "Онлайн-школа для фрилансеров",
    "Наставничество и менторство",
    "Присоединяйся к обучающему чату",
    "Обучение без вложений",
]

STOP_EMBEDDINGS_MISC = [
    "Всем привет! Новый пост на канале",
    "Делюсь полезной информацией",
    "Поделюсь своим опытом работы",
    "Наш проект запускается",
    "Покупайте у нас, скидка сегодня",
    "Приглашаю всех на мой канал",
    "Расскажу, как начать зарабатывать онлайн",
    "Вступай в сообщество успешных людей",
    "Советую подписаться на наш канал",
    "Акция только сегодня",
]



STOP_EMBEDDINGS = {
    "resume": STOP_EMBEDDINGS_RESUME,
    "ads": STOP_EMBEDDINGS_ADS,
    "scam": STOP_EMBEDDINGS_SCAM,
    "edu": STOP_EMBEDDINGS_EDU,
    "misc": STOP_EMBEDDINGS_MISC,
}

def load_stop_embeddings():
    global stop_embeddings
    
    stop_embeddings = {
        cat: [model.encode(text, convert_to_tensor=True) for text in samples]
        for cat, samples in STOP_EMBEDDINGS.items()
    }


def check_stop_embeddings(text: str, threshold: float = 0.55) -> str | None:
    stop_embeddings = get_stop_embeddings()
    text_emb = model.encode(text, convert_to_tensor=True)
    for cat, emb_list in stop_embeddings.items():
        sims = [util.cos_sim(text_emb, e).item() for e in emb_list]
        if max(sims) > threshold:
            return cat
    return None


def get_stop_embeddings() -> dict[str, any]:
    return stop_embeddings


def count_stop_words(text: str) -> int:
    """
    Считает количество совпавших стоп-слов в тексте.
    Логирует найденные стоп-слова.
    """
    text_lower = text.lower()
    text_words = set(re.findall(r"\b\w+\b", text_lower))  # разбиваем на слова
    found_words = stopwords_cache.intersection(text_words)
    # print(f"Stop words cache: {stopwords_cache}")
    # print(f"Words in text: {text_words}")
    # print(f"Found stop words: {found_words}")
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

    pattern = re.compile(
        "|".join(re.escape(k.lower()) for k in keywords), re.IGNORECASE
    )

    def search():
        matches = pattern.findall(text.lower())
        for match in matches:
            logger.info(f"Found stop word: {match}")
        return bool(matches)

    return await asyncio.to_thread(search)


async def analyze_vacancy(text: str, embedding_weight: float = 1.5) -> dict:
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
    # print(f"Очки по ключевым словам: {keyword_scores}")

    # --- сходство по эмбеддингам ---
    text_emb = model.encode(text, convert_to_tensor=True)
    embeddings = get_profession_embeddings()
    embedding_scores = {}
    for name, prof_emb in embeddings.items():
        sim = util.cos_sim(text_emb, prof_emb).item()
        embedding_scores[name] = sim
    # print(f"Сходство по эмбеддингам: {embedding_scores}")

    # --- итоговый рейтинг ---
    final_scores = {
        name: keyword_scores[name] + embedding_weight * embedding_scores[name]
        for name in professions_cache
    }
    # print(f"Итоговые рейтинги: {final_scores}")

    ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    return {"status": "ok", "ranked": ranked}


# === Пример использования ===
async def find_job_func(vacancy_text: str, embedding_weight: float = 1.5):

    result = await analyze_vacancy(vacancy_text, embedding_weight=embedding_weight)

    if result["status"] == "blocked":
        # print(f"🚫 Вакансия заблокирована ({result['reason']})")
        return False

    vacancy_professions = [
        (prof, score) for prof, score in result["ranked"] if score > 1.3
    ]

    if not vacancy_professions:
        # print("⚠️ Вакансия не подходит ни под одну из профессий.")
        return False

    # print("🔎 Результаты анализа вакансии:"

    return vacancy_professions
