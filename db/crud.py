# db/crud.py
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import update, select, delete
from db.models import ScheduledTask, AdminMailing, User, UserProfession, Profession, Vacancy, VacancyQueue, VacancySent, VacancyTwoHours
from db.database import Sessionmaker  # ваша фабрика сессий
from logging import getLogger

logger = getLogger(__name__)

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

async def create_scheduled_task(chat_id: int, message: str, run_at: datetime, type: str = "dunning"):
    async with Sessionmaker() as session:  # AsyncSession
        st = ScheduledTask(chat_id=chat_id, message=message, run_at=run_at, type=type)
        session.add(st)
        await session.commit()
        await session.refresh(st)
        return st  # объект с id

async def set_taskiq_id(scheduled_id: int, taskiq_id: str):
    async with Sessionmaker() as session:
        await session.execute(
            update(ScheduledTask).where(ScheduledTask.id == scheduled_id).values(taskiq_id=taskiq_id)
        )
        await session.commit()

async def cancel_user_tasks(chat_id: int, task_type: str):
    """Пометить будущие задачи пользователя cancelled=True"""
    async with Sessionmaker() as session:
        await session.execute(
            update(ScheduledTask)
            .where(
                (ScheduledTask.chat_id == chat_id)
                & (ScheduledTask.cancelled == False)
                & (ScheduledTask.executed == False)
                & (ScheduledTask.run_at > datetime.now(tz=MOSCOW_TZ))
                & (ScheduledTask.type == task_type)
            )
            .values(cancelled=True)
        )
        await session.commit()

async def get_scheduled_task(scheduled_id: int):
    async with Sessionmaker() as session:
        return await session.get(ScheduledTask, scheduled_id)

async def mark_executed(scheduled_id: int):
    async with Sessionmaker() as session:
        await session.execute(
            update(ScheduledTask).where(ScheduledTask.id == scheduled_id).values(executed=True)
        )
        await session.commit()
        
        
async def get_upcoming_mailings(limit: int = 10):
    async with Sessionmaker() as session:
        stmt = select(AdminMailing).where(
            (AdminMailing.run_at > datetime.now(tz=MOSCOW_TZ)) & (AdminMailing.cancelled == False) & (AdminMailing.executed == False)
        ).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    
async def create_admin_mailing(message: str, run_at: datetime, file_id: str = None, keyboard: str = None, segment: dict = None, task_name: str = None):
    async with Sessionmaker() as session:
        am = AdminMailing(
            message=message,
            run_at=run_at,
            file_id=file_id,
            keyboard=keyboard,
            segment=segment,
            task_name=task_name
        )
        session.add(am)
        await session.commit()
        await session.refresh(am)
        return am  # объект с id
    
    
async def set_admin_mailing_taskiq_id(mailing_id: int, taskiq_id: str):
    async with Sessionmaker() as session:
        await session.execute(
            update(AdminMailing).where(AdminMailing.id == mailing_id).values(taskiq_id=taskiq_id)
        )
        await session.commit()


async def get_admin_mailing(mailing_id: int):
    async with Sessionmaker() as session:
        return await session.get(AdminMailing, mailing_id)
    

async def mark_admin_mailing_executed(mailing_id: int):
    async with Sessionmaker() as session:
        await session.execute(
            update(AdminMailing).where(AdminMailing.id == mailing_id).values(executed=True)
        )
        await session.commit()  


async def cancel_admin_mailings(mailing_id: int):
    async with Sessionmaker() as session:
        try:
            await session.execute(
                update(AdminMailing).where(AdminMailing.id == mailing_id).values(cancelled=True)
            )
            await session.commit()
        except Exception as e:
            return False
    return True


async def get_all_users_in_segment(selected_segments: list[str]):
    """Возвращает список chat_id пользователей, подходящих под выбранные сегменты"""
    async with Sessionmaker() as session:
        users = set()

        # 1️⃣ Все пользователи
        if "Все пользователи" in selected_segments:
            stmt = select(User.telegram_id)
            result = await session.execute(stmt)
            return [row[0] for row in result.all()]  # возврат сразу — других не нужно искать

        # 2️⃣ Все с подпиской
        if "Все с подпиской" in selected_segments:
            stmt = select(User.telegram_id).where(User.subscription_until > datetime.now(MOSCOW_TZ))
            result = await session.execute(stmt)
            users.update([row[0] for row in result.all()])

        # 3️⃣ Все без подписки
        if "Все без подписки" in selected_segments:
            stmt = select(User.telegram_id).where(
                (User.subscription_until == None) | (User.subscription_until < datetime.now(MOSCOW_TZ))
            )
            result = await session.execute(stmt)
            users.update([row[0] for row in result.all()])

        # 4️⃣ У кого кончилась подписка
        if "У кого кончилась подписка" in selected_segments:
            stmt = select(User.telegram_id).where(
                (User.cancelled_subscription_date != None) &
                (User.subscription_until == None)
            )
            result = await session.execute(stmt)
            users.update([row[0] for row in result.all()])

        # 5️⃣ Профессии (если сегменты — это профессии)
        stmt = select(Profession.id).where(Profession.name.in_(selected_segments))
        result = await session.execute(stmt)
        profession_ids = [row[0] for row in result.all()]

        if profession_ids:
            stmt = select(User.telegram_id).join(UserProfession).where(
                UserProfession.profession_id.in_(profession_ids),
                UserProfession.is_selected == True
            ).distinct()
            result = await session.execute(stmt)
            users.update([row[0] for row in result.all()])

        return list(users)
    
    
async def delete_old_vacancie_list():
    async with Sessionmaker() as session:
        stmt = delete(Vacancy).where(Vacancy.created_at < datetime.now(MOSCOW_TZ) - timedelta(days=4))
        result = await session.execute(stmt)
        await session.commit()
        logger.info(f"Удалено {result.rowcount} вакансий (список)")
        
    
async def delete_old_vacancie_button():
    async with Sessionmaker() as session:
        stmt = delete(VacancyQueue).where(VacancyQueue.created_at < datetime.now(MOSCOW_TZ) - timedelta(days=2))
        result = await session.execute(stmt)
        await session.commit()
        logger.info(f"Удалено {result.rowcount} вакансий (очередь)")
    
async def delete_old_vacancie_two_hours():
    async with Sessionmaker() as session:
        stmt = delete(VacancyTwoHours).where(VacancyTwoHours.created_at < datetime.now(MOSCOW_TZ) - timedelta(days=2))
        result = await session.execute(stmt)
        await session.commit()
        logger.info(f"Удалено {result.rowcount} вакансий (2 часа)")
        
        
async def delete_old_vacancie_sent():
    async with Sessionmaker() as session:
        stmt = delete(VacancySent).where(VacancySent.sent_at < datetime.now(MOSCOW_TZ) - timedelta(days=4))
        result = await session.execute(stmt)
        await session.commit()
        logger.info(f"Удалено {result.rowcount} вакансий (отправленные)")