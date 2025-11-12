import logging
from datetime import datetime, timedelta
from sqlalchemy import delete, select, update, func
from sqlalchemy.dialects.postgresql import insert as upsert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from zoneinfo import ZoneInfo
from uuid import UUID
from bot.lexicon.lexicon import LEXICON_SUBSCRIBE
from getcourse.gc_api import gc_request_no_payment_link
from bot_setup import bot
from sqlalchemy.exc import IntegrityError
import hashlib
import asyncio

from db.database import Sessionmaker
from db.models import (
    User,
    Keyword,
    Profession,
    UserProfession,
    Vacancy,
    VacancySent,
    PromoCode,
    UserPromo,
    StopWord,
    VacancyQueue,
    PricingPlan,
    VacancyTwoHours,
    SupportMessage,
    Admins,
    Trash,
    VacancyStat,
)


MOSCOW_TZ = ZoneInfo("Europe/Moscow")
logger = logging.getLogger(__name__)


async def upsert_user(
    session: AsyncSession,
    telegram_id: int,
    first_name: str,
    last_name: str | None = None,
    mail: str | None = None,
    delivery_mode: str = "instant",
    subscription_until: datetime | None = None,
):
    values = {
        "telegram_id": telegram_id,
        "first_name": first_name,
        "last_name": last_name,
        "delivery_mode": delivery_mode,
    }

    # добавляем только если явно переданы
    if mail is not None:
        values["mail"] = mail
    if subscription_until is not None:
        values["subscription_until"] = subscription_until

    stmt = upsert(User).values(values)

    # формируем динамический set_
    update_values = {
        "first_name": first_name,
        "last_name": last_name,
    }
    if mail is not None:
        update_values["mail"] = mail
    if subscription_until is not None:
        update_values["subscription_until"] = subscription_until

    stmt = stmt.on_conflict_do_update(
        index_elements=["telegram_id"],
        set_=update_values,
    )

    await session.execute(stmt)
    await session.commit()


async def db_add_profession(session: AsyncSession, name: str, desc: str):
    stmt = upsert(Profession).values(name=name, desc=desc)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["name"]  # если профессия уже есть
    )
    try:
        await session.execute(stmt)
        await session.commit()
        return True
    except Exception as e:
        logger.error(f"Error adding profession '{name}': {e}")
        return False


async def add_keyword_to_profession(
    session: AsyncSession, profession_id: int, word: str, weight: float
):
    # получаем имя профессии по id
    profession = await session.get(Profession, profession_id)
    if not profession:
        logger.error(f"Profession with ID {profession_id} not found")
        return False
    profession_name = profession.name

    stmt = upsert(Keyword).values(
        profession_id=profession_id,
        word=word,
        weight=weight,
        profession_name=profession_name,
    )
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["profession_id", "word"]  # чтобы не дублировать
    )
    try:
        await session.execute(stmt)
        await session.commit()
        return True
    except Exception as e:
        logger.error(
            f"Error adding keyword '{word}' to profession {profession_name}: {e}"
        )
        return False


async def send_vacancy(session: AsyncSession, user_id: int, vacancy_id: int):
    stmt = upsert(VacancySent).values(user_id=user_id, vacancy_id=vacancy_id)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["user_id", "vacancy_id"]  # чтобы не дублировать
    )
    await session.execute(stmt)
    await session.commit()


async def update_delivery_mode(session: AsyncSession, telegram_id: int, mode: str):
    stmt = (
        update(User).where(User.telegram_id == telegram_id).values(delivery_mode=mode)
    )
    await session.execute(stmt)
    await session.commit()


async def update_users_profession(
    session: AsyncSession,
    telegram_id: int,
    profession_id: UUID,
    is_selected: bool,
):
    stmt = (
        update(UserProfession)
        .where(
            UserProfession.user_id == telegram_id,
            UserProfession.profession_id == profession_id,
        )
        .values(is_selected=is_selected)
    )
    await session.execute(stmt)
    await session.commit()


async def update_all_users_professions(
    session: AsyncSession,
    telegram_id: int,
    profession_ids: list[str],
    is_selected: bool,
):
    stmt = upsert(UserProfession).values(
        [
            {"user_id": telegram_id, "profession_id": pid, "is_selected": is_selected}
            for pid in profession_ids
        ]
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "profession_id"], set_={"is_selected": is_selected}
    )
    await session.execute(stmt)
    await session.commit()


async def activate_promo(
    session: AsyncSession, telegram_id: int, promo_code: str
) -> str:
    user = await session.get(User, telegram_id)
    if not user:
        logger.error(
            f"User with telegram_id {telegram_id} not found for promo activation"
        )
        return None, False

    promo_code_lower = promo_code.lower()

    # ищем промокод
    stmt = select(PromoCode).where(func.lower(PromoCode.code) == promo_code_lower)
    result = await session.execute(stmt)
    promo = result.scalar_one_or_none()
    if not promo:
        text = LEXICON_SUBSCRIBE["unknown_promo"]
        return text, False

    # проверка общего лимита
    if promo.usage_limit is not None and promo.used_count >= promo.usage_limit:
        text = LEXICON_SUBSCRIBE["used_limit"]
        return text, False

    # проверка: использовал ли этот юзер именно этот промокод
    stmt = select(UserPromo).where(
        UserPromo.user_id == user.telegram_id,
        UserPromo.promo_id == promo.id,
    )
    result = await session.execute(stmt)
    already_used = result.scalars().first()
    if already_used:
        text = LEXICON_SUBSCRIBE["used_promo"]
        return text, False

    stmt = select(UserPromo).where(UserPromo.user_id == user.telegram_id)
    result = await session.execute(stmt)
    promos = result.scalars().all()

    if promo_code_lower in [
        "club2425vip",
        "club2425",
        "fm091025",
    ]:
        for user_code in promos:  
            if user_code.promo_id in [3, 5, 7]:  # если уже был активирован один из этих промокодов
                text = LEXICON_SUBSCRIBE["vip_used_limit"]
                return text, False

    await gc_request_no_payment_link(
        email=user.mail, offer_code=promo.offer_code, offer_id=promo.offer_id
    )

    user.active_promo = promo_code_lower

    # обновляем статистику промокода
    promo.used_count += 1

    # создаём запись о том, что юзер использовал промо
    session.add(UserPromo(user_id=user.telegram_id, promo_id=promo.id))

    await session.commit()
    text = LEXICON_SUBSCRIBE["promo_activated"].format(promo_code=promo_code)
    return text, True


async def get_promo_24_hours(session: AsyncSession, user_id: int) -> PromoCode | None:
    try:
        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            logger.error(f"User with telegram_id {user_id} not found for promo check")
            return False

        now = datetime.now(MOSCOW_TZ)

        # Приводим subscription_until к aware datetime в MOSCOW_TZ
        subscription_until = (
            user.subscription_until.replace(tzinfo=MOSCOW_TZ)
            if user.subscription_until is not None
            else None
        )

        if subscription_until is None or subscription_until < now:
            user.subscription_until = now + timedelta(days=1)
        else:
            user.subscription_until = subscription_until + timedelta(days=1)

        await bot.send_message(user_id, LEXICON_SUBSCRIBE["referral_bonus_24h"])
        await session.commit()
        return True

    except Exception as e:
        logger.error(f"Error fetching user ID {user_id}: {e}")
        return False


async def set_new_days(mail: str, days: int):
    async with Sessionmaker() as session:
        stmt = select(User).where(func.lower(User.mail) == mail.lower())
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            logger.error(f"User with mail {mail} not found for setting new days")
            return None

        user.subscription_until = days
        user_id = user.telegram_id
        user.three_days_free_active = "used_with"
        user.cancelled_subscription_date = None
        publick_date = user.subscription_until - timedelta(days=1)
        text = f"{publick_date:%d.%m.%Y}"
        await session.commit()
        return user_id, text


async def check_banned_user(session: AsyncSession, telegram_id: int) -> bool:
    stmt = select(User.is_banned).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    is_banned = result.scalar_one_or_none()
    return bool(is_banned)


async def delete_old_vacancies(session: AsyncSession):
    cutoff = datetime.now(MOSCOW_TZ) - timedelta(days=2)
    stmt = delete(Vacancy).where(Vacancy.created_at < cutoff)
    await session.execute(stmt)
    await session.commit()


async def db_delete_profession(session: AsyncSession, profession_id: int) -> bool:
    try:
        # Удаляем зависимости
        await session.execute(
            delete(UserProfession).where(UserProfession.profession_id == profession_id)
        )
        await session.execute(
            delete(VacancyQueue).where(VacancyQueue.profession_id == profession_id)
        )
        await session.execute(
            delete(Keyword).where(Keyword.profession_id == profession_id)
        )

        # Получаем вакансии профессии
        vacancy_ids = await session.scalars(
            select(Vacancy.id).where(Vacancy.profession_id == profession_id)
        )
        vacancy_ids = vacancy_ids.all()

        if vacancy_ids:
            # Удаляем связанные VacancySent
            await session.execute(
                delete(VacancySent).where(VacancySent.vacancy_id.in_(vacancy_ids))
            )
            # Удаляем сами вакансии
            await session.execute(delete(Vacancy).where(Vacancy.id.in_(vacancy_ids)))

        # Удаляем профессию
        result = await session.execute(
            delete(Profession).where(Profession.id == profession_id)
        )
        if result.rowcount == 0:
            logger.warning(f"⚠️ Профессия с ID={profession_id} не найдена.")
            await session.rollback()
            return False

        await session.commit()
        logger.info(
            f"✅ Профессия ID={profession_id} и все связанные записи успешно удалены."
        )
        return True

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка при удалении профессии ID={profession_id}: {e}")
        return False


async def get_all_professions_parser() -> list[dict]:
    """Возвращает список профессий в виде словарей, без привязки к сессии"""
    async with Sessionmaker() as session:
        result = await session.execute(
            select(Profession).options(selectinload(Profession.keywords))
        )
        professions = result.scalars().all()

        # Преобразуем ORM -> чистые dict
        professions_data = []
        for p in professions:
            professions_data.append(
                {
                    "id": str(p.id),
                    "name": p.name,
                    "desc": p.desc or "",
                    "keywords": {kw.word: kw.weight for kw in p.keywords},
                }
            )
        return professions_data


stopwords_cache = {}


async def add_to_vacancy_queue(text: str, profession_id: UUID, user_id: int):
    async with Sessionmaker() as session:
        stmt = select(VacancyQueue).where(
            VacancyQueue.user_id == user_id, VacancyQueue.text == text
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            logger.info(f"Vacancy already exists in queue for user {user_id}.")
            return False
        try:
            vacancy = VacancyQueue(
                text=text, is_sent=False, profession_id=profession_id, user_id=user_id
            )
            session.add(vacancy)
            await session.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding vacancy to queue: {e}")
            await session.rollback()
            return False


async def add_to_two_hours(text: str, profession_id: UUID, user_id: int):
    async with Sessionmaker() as session:
        stmt = select(VacancyTwoHours).where(
            VacancyTwoHours.user_id == user_id, VacancyTwoHours.text == text
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            logger.info(f"Vacancy already exists in two hours for user {user_id}.")
            return False
        try:
            vacancy = VacancyTwoHours(
                text=text, is_sent=False, profession_id=profession_id, user_id=user_id
            )
            session.add(vacancy)
            await session.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding vacancy to two hours: {e}")
            await session.rollback()
            return False


async def get_unsent_vacancies_by_user(user_id: int) -> list[VacancyQueue]:
    async with Sessionmaker() as session:
        result = await session.execute(
            select(VacancyQueue)
            .where(VacancyQueue.user_id == user_id, VacancyQueue.is_sent == False)
            .order_by(VacancyQueue.created_at.asc())
        )

        return result.scalars().all()


async def get_two_hours_vacancies_by_user(user_id: int) -> list[VacancyQueue]:
    async with Sessionmaker() as session:
        result = await session.execute(
            select(VacancyTwoHours)
            .where(VacancyTwoHours.user_id == user_id, VacancyTwoHours.is_sent == False)
            .order_by(VacancyTwoHours.created_at.asc())
        )

        return result.scalars().all()


async def mark_vacancy_as_sent(user_id: int, vacancy_id: str):
    async with Sessionmaker() as session:
        result = await session.execute(
            select(VacancyQueue).where(
                VacancyQueue.user_id == user_id, VacancyQueue.id == vacancy_id
            )
        )
        vacancy = result.scalar_one_or_none()
        if vacancy:
            vacancy.is_sent = True
            await session.commit()


async def mark_vacancy_as_sent_queue(user_id: int, vacancy_id):
    async with Sessionmaker() as session:
        stmt = select(Vacancy).where(Vacancy.id == vacancy_id)
        result = await session.execute(stmt)
        main_vacancy = result.scalar_one_or_none()

        result = await session.execute(
            select(VacancyQueue).where(
                VacancyQueue.user_id == user_id, VacancyQueue.text == main_vacancy.text
            )
        )
        vacancy = result.scalar_one_or_none()
        if vacancy:
            vacancy.is_sent = True
            await session.commit()
        else:
            logger.error(f"Vacancy with text {vacancy_id} not found for user {user_id}")
            await session.rollback()


async def mark_vacancies_as_sent_two_hours(user_id: int, vacancy_id):
    async with Sessionmaker() as session:
        stmt = select(Vacancy).where(Vacancy.id == vacancy_id)
        result = await session.execute(stmt)
        main_vacancy = result.scalar_one_or_none()

        result = await session.execute(
            select(VacancyTwoHours).where(
                VacancyTwoHours.user_id == user_id,
                VacancyTwoHours.text == main_vacancy.text,
            )
        )
        vacancy = result.scalar_one_or_none()
        if vacancy:
            vacancy.is_sent = True
            await session.commit()
        else:
            logger.error(f"Vacancy with text {vacancy_id} not found for user {user_id}")
            await session.rollback()


async def get_users_by_profession(profession_id: UUID) -> list[User]:
    async with Sessionmaker() as session:
        result = await session.execute(
            select(User)
            .join(UserProfession)
            .where(
                UserProfession.profession_id == profession_id,
                UserProfession.is_selected == True,
                User.is_banned == False,
            )
        )
    return result.scalars().all()


async def record_vacancy_sent(user_id: int, vacancy_id: UUID, message_id: int):
    async with Sessionmaker() as session:
        stmt = (
            upsert(VacancySent)
            .values(user_id=user_id, vacancy_id=vacancy_id, message_id=message_id)
            .on_conflict_do_update(
                index_elements=["user_id", "vacancy_id"],
                set_={"message_id": message_id},
            )
        )
        await session.execute(stmt)
        await session.commit()


async def cleanup_old_data(days: int = 2):
    threshold = datetime.now(MOSCOW_TZ) - timedelta(days=days)
    async with Sessionmaker() as session:
        await session.execute(
            delete(VacancyQueue).where(VacancyQueue.created_at < threshold)
        )
        await session.execute(
            delete(VacancyTwoHours).where(VacancyTwoHours.created_at < threshold)
        )
        await session.execute(delete(Vacancy).where(Vacancy.created_at < threshold))
        await session.commit()


async def delete_vacancy_everywhere(session: AsyncSession, vacancy_id: UUID) -> bool:
    """Удаляет вакансию и все дубликаты с одинаковым текстом, включая связанную рассылку."""

    try:
        # 1️⃣ Находим исходную вакансию
        result = await session.execute(select(Vacancy).where(Vacancy.id == vacancy_id))
        vacancy = result.scalar_one_or_none()

        if not vacancy:
            logger.warning(f"⚠️ Вакансия с ID {vacancy_id} не найдена.")
            return False

        text = vacancy.text

        # 2️⃣ Получаем все вакансии с тем же текстом (включая основную)
        result = await session.execute(select(Vacancy).where(Vacancy.text == text))
        vacancies = result.scalars().all()

        if not vacancies:
            logger.info(f"Нет вакансий с текстом '{text}' — нечего удалять.")
            return False

        logger.warning(f"🥵 Удаляем {len(vacancies)} вакансий с одинаковым текстом. 🥵")

        # 3️⃣ Удаляем связанные данные для каждой вакансии
        for vac in vacancies:
            vac_id = vac.id

            try:
                # --- Удаляем отправленные вакансии ---
                sent_result = await session.execute(
                    select(VacancySent).where(VacancySent.vacancy_id == vac_id)
                )
                sent_vacancies = sent_result.scalars().all()

                for sent in sent_vacancies:
                    try:
                        await bot.delete_message(sent.user_id, sent.message_id)
                        logger.info(
                            f"Удалено сообщение {sent.message_id} у пользователя {sent.user_id}"
                        )
                        await asyncio.sleep(0.2)  # избегаем flood limit
                    except Exception as e:
                        logger.warning(
                            f"Не удалось удалить сообщение {sent.message_id} у {sent.user_id}: {e}"
                        )

                # --- Удаляем записи из VacancySent ---
                await session.execute(
                    delete(VacancySent).where(VacancySent.vacancy_id == vac_id)
                )

                # --- Удаляем из очередей (по тексту) ---
                await session.execute(
                    delete(VacancyQueue).where(VacancyQueue.text == text)
                )
                await session.execute(
                    delete(VacancyTwoHours).where(VacancyTwoHours.text == text)
                )

                # --- Удаляем саму вакансию ---
                await session.execute(delete(Vacancy).where(Vacancy.id == vac_id))
                logger.info(f"✅ Удалена вакансия {vac_id}")

            except Exception as e:
                logger.error(f"Ошибка при удалении вакансии {vac_id}: {e}")
                await session.rollback()
                return False

        # 4️⃣ Коммитим изменения один раз после цикла
        await session.commit()
        logger.info(f"🎉 Все вакансии с текстом '{text}' успешно удалены.")
        return True

    except Exception as e:
        logger.error(f"Ошибка при удалении вакансий по ID {vacancy_id}: {e}")
        await session.rollback()
        return False


async def dublicate_check(user_id: int, vacancy: Vacancy) -> bool:
    # Проверка: отправлялась ли уже вакансия с тем же "именем" (используем vacancy.text) этому пользователю
    async with Sessionmaker() as session:
        stmt = (
            select(VacancySent.id)
            .join(Vacancy, Vacancy.id == VacancySent.vacancy_id)
            .where(
                VacancySent.user_id == user_id,
                Vacancy.text
                == vacancy.text,  # если у модели есть поле name, замените на Vacancy.name == vacancy.name
            )
            .limit(1)
        )
        result = await session.execute(stmt)
        if result.scalar_one_or_none() is not None:
            logger.info("Vacancy with same text already sent to user, skipping.")
            return False
    return True


def make_message_hash(text: str) -> str:
    """Создаем хэш для текста вакансии"""
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()


async def get_vacancy_by_hash(text_hash: str):
    async with Sessionmaker() as session:
        stmt = select(Vacancy).where(Vacancy.hash == text_hash)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def save_vacancy_hash(
    text,
    proffname,
    score,
    url,
    text_hash,
    vacancy_source=None,
    forwarding_source=None,
) -> UUID | None:
    async with Sessionmaker() as session:
        # Проверяем, есть ли вакансия с таким хэшем
        existing = await get_vacancy_by_hash(text_hash)
        if existing:
            return existing.id

        res = select(Profession).where(Profession.name == proffname)
        result = await session.execute(res)
        profession = result.scalar_one_or_none()
        if not profession:
            logger.error(f"Profession '{proffname}' not found, skipping save.")
            return None

        # Создаём новую вакансию
        vacancy = Vacancy(
            text=text,
            profession_id=profession.id,  # используем profession_id, а не profession_name
            score=score,
            url=url,
            hash=text_hash,
            vacancy_source=vacancy_source,
            forwarding_source=forwarding_source,
        )
        session.add(vacancy)
        try:
            await session.commit()
            await session.refresh(vacancy)
            return vacancy.id
        except IntegrityError:
            await session.rollback()
            existing = await get_vacancy_by_hash(text_hash)
            return existing.id if existing else None


async def update_vacancy_hash_admin_chat_url(vacancy_id: UUID, url: str) -> bool:
    async with Sessionmaker() as session:
        vacancy = await session.get(Vacancy, vacancy_id)
        if not vacancy:
            logger.error(f"Vacancy with ID {vacancy_id} not found for URL update")
            return False
        vacancy.admin_chat_url = url
        await session.commit()
        return True


async def get_vacancy_by_id(vacancy_id: UUID) -> Vacancy | None:
    async with Sessionmaker() as session:
        vacancy = await session.get(Vacancy, vacancy_id)
        await session.commit()
        return vacancy


async def return_vacancy_by_id(
    vacancy_id: UUID, session: AsyncSession
) -> Vacancy | None:
    stmt = select(Vacancy).where(Vacancy.id == vacancy_id)
    result = await session.execute(stmt)
    vacancy = result.scalar_one_or_none()
    return vacancy


async def load_stopwords():
    # если кэш уже есть, возвращаем его
    if hasattr(load_stopwords, "cache"):
        return load_stopwords.cache

    async with Sessionmaker() as session:
        result = await session.execute(select(StopWord))
        stopwords = result.scalars().all()

    # создаём кэш и сохраняем как атрибут функции
    load_stopwords.cache = {sw.word.lower() for sw in stopwords}
    print(f"Stopwords loaded: {len(load_stopwords.cache)}")
    return load_stopwords.cache


async def give_three_days_free(telegram_id: int) -> bool:
    async with Sessionmaker() as session:
        user = await session.get(User, telegram_id)
        if not user:
            logger.error(f"User with telegram_id {telegram_id} not found for free days")
            return False
        if user.three_days_free_active in ["active", "used", "used_with"]:
            logger.info(f"User {telegram_id} has already used or has active free days")
            return False
        user.subscription_until = (
            datetime.now(MOSCOW_TZ) + timedelta(days=3)
            if not user.subscription_until
            or user.subscription_until < datetime.now(MOSCOW_TZ)
            else user.subscription_until + timedelta(days=3)
        )
        user.three_days_free_active = "active"
        await session.commit()
        return True


async def update_user_access(telegram_id: int, has_access: bool):
    async with Sessionmaker() as session:
        user = await session.get(User, telegram_id)
        if user:
            if has_access:
                logger.info(f"Granting access to user {telegram_id}")
                user.subscription_until = datetime.now(MOSCOW_TZ) + timedelta(weeks=240)
                user.three_days_free_active = "admin"
                await session.commit()
            else:
                logger.info(f"Revoking access from user {telegram_id}")
                user.subscription_until = None
                if user.three_days_free_active == "active":
                    user.three_days_free_active = "used"
                user.cancelled_subscription_date = datetime.now(MOSCOW_TZ)
                user.active_promo = None
                user.first_price_offer_code = None
                user.first_price_offer_id = None
                await session.commit()


async def get_user_by_telegram_id(telegram_id: int) -> User | None:
    async with Sessionmaker() as session:
        res = await session.get(User, telegram_id)
        await session.commit()
        return res


async def get_all_users() -> list[User]:
    async with Sessionmaker() as session:
        result = await session.execute(select(User))
        await session.commit()
        return result.scalars().all()


async def get_all_professions() -> list[Profession]:
    async with Sessionmaker() as session:
        result = await session.execute(select(Profession))
        await session.commit()
        return result.scalars().all()


async def get_all_keywords_from_profession(profession_id: int) -> list[Keyword]:
    async with Sessionmaker() as session:
        result = await session.execute(
            select(Keyword).where(Keyword.profession_id == profession_id)
        )
        await session.commit()
        return result.scalars().all()


async def get_all_mails() -> list[str]:
    async with Sessionmaker() as session:
        result = await session.execute(select(User.mail).where(User.mail != None))  # type: ignore
        await session.commit()
        return [row[0] for row in result.fetchall()]  # type: ignore


async def db_delete_keyword(session: AsyncSession, keyword_id: int):
    stmt = delete(Keyword).where(Keyword.id == keyword_id)
    try:
        await session.execute(stmt)
    except Exception as e:
        logger.error(f"Error deleting keyword ID {keyword_id}: {e}")
        return False
    await session.commit()
    return True


async def return_profession_by_id(session: AsyncSession, profession_id):
    stmt = select(Profession).where()
    result = await session.execute(stmt)
    await session.commit()
    return result.scalar_one()


async def get_profession_by_id(profession_id: int) -> Profession | None:
    async with Sessionmaker() as session:
        stmt = (
            select(Profession)
            .options(selectinload(Profession.keywords))
            .where(Profession.id == profession_id)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one()


async def db_add_profession_desc(session: AsyncSession, profession_id: int, desc: str):
    profession = await session.get(Profession, profession_id)
    if profession:
        profession.desc = desc
        await session.commit()
        return True
    else:
        logger.error(f"Failed to add description to profession ID {profession_id}")
        return False


async def db_delete_profession_desc(session: AsyncSession, profession_id: int):
    profession = await session.get(Profession, profession_id)
    if profession:
        profession.desc = None
        await session.commit()
        return True
    else:
        logger.error(f"Failed to delete description from profession ID {profession_id}")
        return False


async def db_add_stopword(session: AsyncSession, word: str):
    stmt = upsert(StopWord).values(word=word)
    stmt = stmt.on_conflict_do_nothing(index_elements=["word"])  # чтобы не дублировать
    try:
        await session.execute(stmt)
        await session.commit()
        return True
    except Exception as e:
        logger.error(f"Error adding stopword '{word}': {e}")
        return False


async def db_delete_stopword(session: AsyncSession, stopword_id: str):
    stmt = delete(StopWord).where(StopWord.id == stopword_id)
    try:
        await session.execute(stmt)
        await session.commit()
        return True
    except Exception as e:
        logger.error(f"Error deleting stopword ID {stopword_id}: {e}")
        return False


async def get_all_stopwords() -> list[StopWord]:
    async with Sessionmaker() as session:
        result = await session.execute(select(StopWord))
        await session.commit()
        return result.scalars().all()


async def db_change_email(session: AsyncSession, telegram_id: int, new_email: str):
    user = await session.get(User, telegram_id)
    if user:
        user.mail = new_email
        await session.commit()
        return True
    else:
        logger.error(f"Failed to change email for user ID {telegram_id}")
        return False


async def get_all_users_professions(telegram_id: int) -> list[UserProfession]:
    async with Sessionmaker() as session:
        stmt = (
            select(UserProfession)
            .options(joinedload(UserProfession.profession))
            .where(UserProfession.user_id == telegram_id)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.scalars().all()


async def get_user_delivery_mode(telegram_id: int) -> str | None:
    async with Sessionmaker() as session:
        user = await session.get(User, telegram_id)
        await session.commit()
        if user:
            return user.delivery_mode
        return None


async def upsert_user_professions(
    session: AsyncSession, telegram_id: int, professions: list[UUID]
):
    stmt = upsert(UserProfession).values(
        [
            {"user_id": telegram_id, "profession_id": pid, "is_selected": False}
            for pid in professions
        ]
    )
    stmt = stmt.on_conflict_do_nothing(index_elements=["user_id", "profession_id"])
    await session.execute(stmt)
    await session.commit()


async def get_user_subscription_until(telegram_id: int) -> datetime | None:
    async with Sessionmaker() as session:
        user = await session.get(User, telegram_id)
        await session.commit()
        if user:
            if user.subscription_until is not None:
                public_date = user.subscription_until - timedelta(days=1)
                text = f"Подписка активна до {public_date:%d.%m.%Y}"
                return text
            else:
                text = "Подписка не активна"
                return text
        return "Ошибка при получении статуса подписки"


async def get_pricing_data(user_id: int, chosen_plan: str):
    async with Sessionmaker() as session:
        # ищем пользователя
        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user and user.is_pay_status == True:
            return user.first_price_offer_code, user.first_price_offer_id
        print(chosen_plan)
        # выбираем план
        plan_name = None
        if chosen_plan == "1_month":
            plan_name = "1_month"
        elif chosen_plan == "3_months":
            plan_name = "3_months"

        if plan_name is None:
            return None, None  # или бросить исключение
        print(plan_name)
        stmt = select(PricingPlan).where(PricingPlan.name == plan_name)
        result = await session.execute(stmt)
        data = result.scalar_one_or_none()  # один объект или None

        if data is None:
            return None, None  # план не найден
        return data.offer_code, data.offer_id


async def update_user_pricing_data(
    telegram_id: int, offer_code: str = None, offer_id: str = None
):
    async with Sessionmaker() as session:
        user = await session.get(User, telegram_id)
        if user:
            user.first_price_offer_code = offer_code
            user.first_price_offer_id = offer_id
            await session.commit()
            return True
        else:
            logger.error(f"Failed to update pricing data for user ID {telegram_id}")
            return False


async def update_user_is_pay_status(telegram_id: int, is_pay_status: bool):
    async with Sessionmaker() as session:
        user = await session.get(User, telegram_id)
        if user:
            user.is_pay_status = is_pay_status
            await session.commit()
            return True
        else:
            logger.error(f"Failed to update pricing data for user ID {telegram_id}")
            return False


async def update_autopay_status(telegram_id: int, is_autopay: bool):
    async with Sessionmaker() as session:
        user = await session.get(User, telegram_id)
        if user:
            user.is_autopay = is_autopay
            await session.commit()
            return True
        else:
            logger.error(f"Failed to update autopay status for user ID {telegram_id}")
            return False


async def select_two_hours_users() -> list[User]:
    async with Sessionmaker() as session:
        result = await session.execute(
            select(User).where(
                User.is_banned == False,
                User.delivery_mode == "two_hours",
                User.subscription_until > datetime.now(MOSCOW_TZ),
            )
        )
        users = result.scalars().all()
        # создаем список id пользователей
        user_ids = [user.telegram_id for user in users]
        await session.commit()
        return user_ids


async def check_user_has_active_subscription(telegram_id: int) -> bool:
    async with Sessionmaker() as session:
        user = await session.get(User, telegram_id)
        if (
            user
            and user.subscription_until
            and user.subscription_until > datetime.now(MOSCOW_TZ)
        ):
            return True
        return False


async def get_vacancy_by_text(text: str) -> Vacancy | None:
    async with Sessionmaker() as session:
        stmt = select(Vacancy).where(Vacancy.text == text)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def save_support_message(
    session: AsyncSession,
    user_id: int,
    user_message_id: int,
    admin_chat_message_id: int,
):
    try:
        support_msg = SupportMessage(
            user_id=user_id,
            user_message_id=user_message_id,
            admin_chat_message_id=admin_chat_message_id,
        )

        session.add(support_msg)
        await session.commit()
        return True
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to save support message: {e}")
        return False


async def get_user_by_admin_chat_message_id(
    admin_chat_message_id: int,
) -> SupportMessage | None:
    async with Sessionmaker() as session:
        try:
            stmt = select(SupportMessage.user_id).where(
                SupportMessage.admin_chat_message_id == admin_chat_message_id
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"Failed to get user by admin chat message ID {admin_chat_message_id}: {e}"
            )
            return None


async def get_admins_list() -> list[Admins]:
    async with Sessionmaker() as session:
        stmt = select(Admins)
        try:
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get admins list: {e}")
            return []


async def is_super_admin(telegram_id: int) -> bool:
    async with Sessionmaker() as session:
        stmt = select(Admins).where(
            Admins.telegram_id == telegram_id, Admins.is_superadmin == True
        )
        try:
            result = await session.execute(stmt)
            admin = result.scalar_one_or_none()
            if admin:
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to check super admin status for {telegram_id}: {e}")
            return False


async def add_to_admins(telegram_id: int) -> bool:
    async with Sessionmaker() as session:
        try:
            user = await session.get(User, telegram_id)
            if not user:
                logger.error(
                    f"User with telegram_id {telegram_id} not found for admin add"
                )
                return False
            full_name = user.first_name
        except Exception as e:
            logger.error(f"Error fetching user {telegram_id} for admin add: {e}")
            return False
        stmt = upsert(Admins).values(
            telegram_id=telegram_id, is_admin=True, full_name=full_name
        )
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["telegram_id"]
        )  # чтобы не дублировать
        try:
            await session.execute(stmt)
            await session.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding admin '{telegram_id}': {e}")
            return False


async def remove_from_admins(telegram_id: int) -> bool:
    async with Sessionmaker() as session:
        stmt = delete(Admins).where(Admins.telegram_id == telegram_id)
        try:
            result = await session.execute(stmt)
            if result.rowcount == 0:
                logger.warning(
                    f"Admin with telegram_id {telegram_id} not found for removal"
                )
                return False
            await session.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing admin '{telegram_id}': {e}")
            return False


async def save_in_trash(text, hash) -> bool:
    async with Sessionmaker() as session:
        trash = Trash(text=text, hash=hash)
        session.add(trash)
        await session.commit()
        return True


async def is_in_trash(hash) -> bool:
    async with Sessionmaker() as session:
        stmt = select(Trash).where(Trash.hash == hash)
        result = await session.execute(stmt)
        trash = result.scalar_one_or_none()
        if trash:
            return True
        else:
            return False


async def add_vac_point(vacancy_name):
    async with Sessionmaker() as session:
        point = VacancyStat(quantity=1, profession_name=vacancy_name)
        session.add(point)
        await session.commit()


async def get_vac_points():
    async with Sessionmaker() as session:
        stmt = select(Profession)
        result = await session.execute(stmt)
        professions = result.scalars().all()
        result_dict = {}
        for profession in professions:
            stmt = select(VacancyStat).where(
                VacancyStat.profession_name == profession.name
            )
            result = await session.execute(stmt)
            points = result.scalars().all()
            point_sum = 0
            for point in points:
                point_sum += point.quantity
            result_dict[profession.name] = point_sum

        result_dict["\n🌞-----За последние сутки-----🌚"] = 0
        for profession in professions:
            stmt = select(VacancyStat).where(
                VacancyStat.profession_name == profession.name,
                VacancyStat.created_at > (datetime.now(MOSCOW_TZ) - timedelta(days=1)),
            )
            result = await session.execute(stmt)
            points = result.scalars().all()
            point_sum = 0
            for point in points:
                point_sum += point.quantity
            result_dict[f"{profession.name} (24ч)"] = point_sum

        await session.commit()
        return result_dict


async def get_payment_text() -> str:
    async with Sessionmaker() as session:
        stmt = select(PricingPlan).where(PricingPlan.name == "text")
        result = await session.execute(stmt)
        payment_text = (result.scalars().one_or_none()).offer_code
        await session.commit()
        return payment_text
    
    
async def get_all_user_info(telegram_id) -> dict:
    async with Sessionmaker() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalars().one_or_none()
    
        data = {}

        data["Имя"] = user.first_name
        data["Фамилия"] = user.last_name
        data["Почта"] = user.mail
        data["Активный промокод"] = user.active_promo
        data["Заблокирован"] = user.is_banned
        data["Подписка до"] = user.subscription_until
        data["Режим доставки"] = user.delivery_mode
        data["Дата регистрации"] = user.created_at
        data["Первое предложение (код)"] = user.first_price_offer_code
        data["Первое предложение (ID)"] = user.first_price_offer_id
        data["Оплачивал ли?"] = user.is_pay_status
        data["Дата окончания подписки"] = user.cancelled_subscription_date
        data["Автоплатёж?"] = user.is_autopay
        data["Приглашён пользователем с ID"] = user.from_user_id
        
        return data


async def get_all_support_users(session: AsyncSession):
    stmt = select(User).where(User.delivery_mode == "support")
    result = await session.execute(stmt)
    users = result.scalars().all()

    if users:
        data = []  # создаём список один раз до цикла
        for user in users:
            text = f"""
Имя: {user.first_name}
ID: <code>{user.telegram_id}</code>

"""
            data.append(text)
        await session.commit()
        return data
    else:
        await session.commit()
        return "Нет пользователей в режиме поддержки"