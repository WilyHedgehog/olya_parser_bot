# bot/background_tasks/dunning.py
from datetime import datetime, timedelta
from .broker import broker, schedule_source
from db.crud import (
    create_scheduled_task,
    set_taskiq_id,
    get_scheduled_task,
    mark_executed,
    cancel_user_tasks,
)
from utils.bot_utils import send_message
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


@broker.task
async def send_followup(scheduled_task_id: int):
    print(f"send_followup called with scheduled_task_id={scheduled_task_id}")
    """
    Воркeром выполняется эта функция. Она получает id записи в БД,
    проверяет флаг cancelled и только потом шлёт сообщение.
    """
    scheduled = await get_scheduled_task(scheduled_task_id)
    if not scheduled:
        return  # нет записи — ничего делать
    if scheduled.cancelled:
        return  # пользователь отменил — выходим
    if scheduled.executed:
        return  # уже выполнено

    # выполнить рассылку
    await send_message(scheduled.chat_id, scheduled.message)

    # пометить как выполненное
    await mark_executed(scheduled_task_id)


async def schedule_dunning(chat_id: int):
    await broker.startup()
    """Создаёт цепочку дожимных задач — создаём записи в БД, ставим задачи в очередь"""
    delays = [
        (5 * 60, "Через 5 минут! 👋"),
        (60 * 60, "Прошел час, а вы не продолжили 😢"),
        (24 * 60 * 60, "Прошли сутки, возвращайтесь! 💬"),
    ]

    for delay_seconds, text in delays:
        run_at = datetime.now(MOSCOW_TZ) + timedelta(seconds=delay_seconds)

        # 1) создаём запись в БД до постановки в очередь
        scheduled = await create_scheduled_task(
            chat_id=chat_id, message=text, run_at=run_at, type="dunning", is_cron=False
            
        )

        # 2) ставим задачу в Taskiq, передаём scheduled.id как аргумент
        task = await send_followup.schedule_by_time(
            scheduled_task_id=scheduled.id, time=run_at, source=schedule_source
        )
        await set_taskiq_id(scheduled.id, task.schedule_id)
        
    await broker.shutdown()


async def cancel_dunning_tasks(chat_id: int):
    """Пометить будущие дожимные рассылки пользователя как cancelled"""
    await cancel_user_tasks(chat_id, "dunning")
