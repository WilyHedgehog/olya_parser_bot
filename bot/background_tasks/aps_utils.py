import asyncio
from bot.background_tasks.broker import schedule_source
from logging import getLogger
logger = getLogger(__name__)

async def clear():
    schedules = await schedule_source.get_schedules()
    for s in schedules:
        await schedule_source.delete_schedule(s.schedule_id)
        
        
async def cancel_mailing_by_id(scheduled_id: int):
    try:
        await schedule_source.delete_schedule(scheduled_id)
    except Exception as e:
        logger.error(f"Ошибка при отмене задачи с id {scheduled_id}: {e}")
        return False
    return True