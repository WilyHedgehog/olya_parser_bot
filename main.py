import logging
import structlog
import asyncio
import asyncpg
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Dispatcher
from aiogram.types import Update
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile

from bot_setup import bot, dp
from config.config import Config, load_config
from bot.handlers import get_routers
from parser.parser_bot import main as parser_main

from db.database import Sessionmaker
from db.requests import set_new_days, update_user_is_pay_status

from find_job_process.find_job import load_professions

from bot.background_tasks.check_subscriptions import start_all_schedulers
from bot.background_tasks.send_two_hours_vacancy import start_scheduler_two_hours_vacancy_send
from bot.middlewares.middlewares import (
    DbSessionMiddleware,
    TrackAllUsersMiddleware,
    ShadowBanMiddleware,
    FreeThreeDaysMiddleware,
    UserProfessionsMiddleware,
)

from bot.lexicon.lexicon import LEXICON_SUBSCRIBE

logger = structlog.get_logger(__name__)
config: Config = load_config()
MOSCOW_TZ = ZoneInfo("Europe/Moscow")
WEBHOOK_PATH = "/webhook"
MONTHS = {
    "янв": 1, "фев": 2, "мар": 3, "апр": 4, "май": 5, "июн": 6,
    "июл": 7, "авг": 8, "сен": 9, "сент": 9, "окт": 10, "ноя": 11, "дек": 12
}


def dispatcher_factory() -> Dispatcher:
    dp.update.middleware(DbSessionMiddleware(Sessionmaker))
    dp.update.middleware(TrackAllUsersMiddleware())
    dp.update.middleware(ShadowBanMiddleware())
    dp.update.middleware(FreeThreeDaysMiddleware())
    dp.message.middleware(UserProfessionsMiddleware())
    dp.callback_query.middleware(UserProfessionsMiddleware())
    dp.include_routers(*get_routers())

    return dp


def create_app(config: Config) -> FastAPI:

    async def wait_for_postgres(url: str, retries: int = 10, delay: int = 2):
        for i in range(retries):
            try:
                conn = await asyncpg.connect(url)
                await conn.close()
                print("Postgres ready!")
                return
            except Exception:
                print(f"Waiting for Postgres... attempt {i+1}")
                await asyncio.sleep(delay)
        raise RuntimeError("Postgres did not start in time!")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # --- Startup ---
        logging.basicConfig(
            level=getattr(logging, config.log.level.upper(), logging.INFO),
            format=config.log.format,
        )

        # Ждем Postgres
        #await wait_for_postgres(config.database.url)

        dispatcher_factory()
        me = await bot.me()
        logger.info(f"Bot {me.first_name} starting with webhook: {WEBHOOK_PATH}")

        # Устанавливаем вебхук
        await bot.set_webhook(config.bot.webhook_url, drop_pending_updates=True)
        logger.info(f"Webhook set to {config.bot.webhook_url}")

        # Запускаем парсер
        asyncio.create_task(parser_main())
        logger.info("Parser started")

        # Загружаем профессии
        await load_professions()
        logger.info("Professions loaded")

        # Запускаем планировщик задач
        start_all_schedulers()
        logger.info("Scheduler started")
        
        #start_scheduler_two_hours_vacancy_send()
        logger.info("Two hours vacancy scheduler started")
        

        yield

        # --- Shutdown ---
        await bot.delete_webhook()
        await bot.session.close()
        logger.info("Bot stopped")

    app = FastAPI(title="Telegram Bot API", lifespan=lifespan)

    @app.post(WEBHOOK_PATH)
    async def telegram_webhook(request: Request):
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
        return {"ok": True}

    return app


# --- Загружаем конфиг и создаём приложение --
app = create_app(config)
# --- Запуск uvicorn через импорт строки для reload ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",  # важно: передаём как строку, чтобы работал reload
        host=config.app.host,
        port=config.app.port,
        reload=config.app.reload,
    )


@app.get(f"{WEBHOOK_PATH}/user_promo")
async def process_getcourse_promocode(
    gc_date: str = "",
    mail: str = "",
):
    date = await parse_date(gc_date)
    date = date + timedelta(hours=12)
    text = ''
    user_id, new_text = await set_new_days(mail=mail, days=date)
    text += new_text    
    print(f"Получен платёж: email {mail}")

    if user_id:
        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode=ParseMode.HTML,
        )

    return JSONResponse(content={"status": "ok"})

# https://2ba392152584.ngrok-free.app/webhook/subscribe?gc_date={object.finish_at}&mail={object.user.email}&offer_id={object.user.id}

# https://capybara.olgaproonline.ru/webhook/subscribe?gc_date={object.finish_at}&mail={object.user.email}   платная подписка
# https://capybara.olgaproonline.ru/webhook/prolong?gc_date={object.finish_at}&mail={object.user.email}  продление подписки
# https://capybara.olgaproonline.ru/webhook/promocode?gc_date={object.finish_at}&mail={object.user.email}    промокод

@app.get(f"{WEBHOOK_PATH}/subscribe")
async def process_getcourse_sub(
    gc_date: str = "",
    mail: str = "",
):
    date = await parse_date(gc_date)
    date = date + timedelta(hours=12)
    user_id, new_text = await set_new_days(mail=mail, days=date)
    photo = FSInputFile("bot/assets/Подписка активна-1.png")
    print(f"Получен платёж: email {mail}")

    if user_id:
        await bot.send_photo(
            chat_id=user_id,
            photo=photo,
            caption=LEXICON_SUBSCRIBE["after_subscribe_text"].format(date=date.strftime("%d.%m.%Y")),
            parse_mode=ParseMode.HTML,
        )

    await update_user_is_pay_status(telegram_id=user_id, is_pay_status=True)
    return JSONResponse(content={"status": "ok"})


@app.get(f"{WEBHOOK_PATH}/promocode")
async def process_getcourse_update(
    gc_date: str = "",
    mail: str = "",
):
    date = await parse_date(gc_date)
    logger.info(f"Parsed date: {date}")
    date = date + timedelta(hours=12)
    user_id, new_text = await set_new_days(mail=mail, days=date)
    photo = FSInputFile("bot/assets/Подписка активна-1.png")
    print(f"Получен платёж: email {mail}")

    if user_id:
        await bot.send_photo(
            chat_id=user_id,
            photo=photo,
            caption=LEXICON_SUBSCRIBE["after_promocode_text"].format(date=date.strftime("%d.%m.%Y")),
            parse_mode=ParseMode.HTML,
        )

    await update_user_is_pay_status(telegram_id=user_id, is_pay_status=True)
    return JSONResponse(content={"status": "ok"})



@app.get(f"{WEBHOOK_PATH}/prolong")
async def process_getcourse_extension(
    gc_date: str = "",
    mail: str = "",
):
    date = await parse_date(gc_date)
    date = date + timedelta(hours=12)
    user_id, new_text = await set_new_days(mail=mail, days=date)
    photo = FSInputFile("bot/assets/Подписка активна-1.png")
    print(f"Получен платёж: email {mail}")

    if user_id:
        await bot.send_photo(
            chat_id=user_id,
            photo=photo,
            caption=LEXICON_SUBSCRIBE["after_prolong_text"].format(date=date.strftime("%d.%m.%Y")),
            parse_mode=ParseMode.HTML,
        )

    return JSONResponse(content={"status": "ok"})




async def parse_date(date_str: str) -> datetime:
    parts = date_str.strip().split()
    if len(parts) != 3:
        logger.error(f"Неверный формат даты: {date_str}")
        #raise ValueError(f"Неверный формат даты: {date_str}")

    day, month_str, year = parts
    month = MONTHS[month_str.lower()[:3]]  # первые 3 буквы для универсальности
    dt = datetime(int(year), month, int(day), tzinfo=MOSCOW_TZ)
    return dt