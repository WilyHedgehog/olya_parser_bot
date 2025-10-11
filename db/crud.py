# db/crud.py
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import update
from db.models import ScheduledTask
from db.database import Sessionmaker  # ваша фабрика сессий

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

async def cancel_user_tasks(chat_id: int):
    """Пометить будущие задачи пользователя cancelled=True"""
    async with Sessionmaker() as session:
        await session.execute(
            update(ScheduledTask)
            .where(
                (ScheduledTask.chat_id == chat_id)
                & (ScheduledTask.cancelled == False)
                & (ScheduledTask.executed == False)
                & (ScheduledTask.run_at > datetime.now(tz=MOSCOW_TZ))
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