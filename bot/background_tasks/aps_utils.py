import asyncio
from bot.background_tasks.broker import schedule_source

async def clear():
    schedules = await schedule_source.get_schedules()
    for s in schedules:
        await schedule_source.delete_schedule(s.schedule_id)