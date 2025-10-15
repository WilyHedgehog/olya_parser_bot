import logging
import structlog
import asyncio
import asyncpg
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from utils.nats_connect import (
    get_nats_connection,
    setup_vacancy_stream,
    setup_tasks_stream,
    setup_bot_send_message_stream,
)
from utils.bot_send_mes_queue import bot_send_messages_worker
from storage.nats_storage import NatsStorage

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Dispatcher
from aiogram.types import Update
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile

from bot_setup import bot, get_db
from config.config import Config, load_config
from bot.handlers import get_routers
from parser.parser_bot import main as parser_main

from db.database import Sessionmaker
from db.requests import set_new_days, update_user_is_pay_status, load_stopwords
from parser.worker import vacancy_worker

from find_job_process.find_job import load_professions

from bot.background_tasks.check_subscriptions import start_all_schedulers
from bot.background_tasks.broker import schedule_source
from bot.background_tasks.send_two_hours_vacancy import (
    start_scheduler_two_hours_vacancy_send,
)
from bot.background_tasks.broker import broker
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
    "янв": 1,
    "фев": 2,
    "мар": 3,
    "апр": 4,
    "май": 5,
    "июн": 6,
    "июл": 7,
    "авг": 8,
    "сен": 9,
    "сент": 9,
    "окт": 10,
    "ноя": 11,
    "дек": 12,
}


def dispatcher_factory(storage) -> Dispatcher:
    dp = get_db(storage)

    dp.update.middleware(DbSessionMiddleware(Sessionmaker))
    dp.update.middleware(TrackAllUsersMiddleware())
    dp.update.middleware(ShadowBanMiddleware())
    dp.update.middleware(FreeThreeDaysMiddleware())
    dp.message.middleware(UserProfessionsMiddleware())
    dp.callback_query.middleware(UserProfessionsMiddleware())
    dp.include_routers(*get_routers())

    return dp


def create_app(config: Config) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # --- Startup ---
        logging.basicConfig(
            level=getattr(logging, config.log.level.upper(), logging.INFO),
            format=config.log.format,
        )

        # Подключаем NATS и настраиваем хранилище
        nc, js = await get_nats_connection()
        storage: NatsStorage = await NatsStorage(nc=nc, js=js).create_storage()

        global dp
        dp = dispatcher_factory(storage)
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

        await load_stopwords()
        logger.info("Stopwords loaded")

        # Запускаем планировщик задач
        start_all_schedulers()
        logger.info("Scheduler started")

        # start_scheduler_two_hours_vacancy_send()
        logger.info("Two hours vacancy scheduler started")

        # Запускаем воркер для обработки вакансий
        await setup_vacancy_stream(js)
        await setup_tasks_stream(js)
        await setup_bot_send_message_stream(js)
        asyncio.create_task(vacancy_worker(js))
        asyncio.create_task(bot_send_messages_worker(js))
        logger.info("Vacancy worker started")
        await schedule_source.startup()
        logger.info("Taskiq broker started")
        
        logger.info("Taskiq schedule source started")

        yield

        # --- Shutdown ---
        await bot.delete_webhook()
        await bot.session.close()
        await nc.close()
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
    text = ""
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
    try:
        date = await parse_date(gc_date)
        logger.info(f"Parsed date: {date}")
        date = date + timedelta(hours=12)
        user_id, new_text = await set_new_days(mail=mail, days=date)
        print(f"Получен платёж: email {mail}")

        if user_id:
            try:
                photo = FSInputFile("bot/assets/Подписка активна-1.png")
                await bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption=LEXICON_SUBSCRIBE["after_subscribe_text"].format(
                        date=date.strftime("%d.%m.%Y")
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке фото пользователю {user_id}: {e}")

            await update_user_is_pay_status(telegram_id=user_id, is_pay_status=True)

        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(f"Ошибка в process_getcourse_sub: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)})


@app.get(f"{WEBHOOK_PATH}/promocode")
async def process_getcourse_update(gc_date: str = "", mail: str = ""):
    try:
        # парсим дату
        date = await parse_date(gc_date)
        logger.info(f"Parsed date: {date}")

        # добавляем 12 часов
        date = date + timedelta(hours=12)

        # обновляем подписку
        user_id, new_text = await set_new_days(mail=mail, days=date)
        logger.info(
            f"Получен промокод: email={mail}, user_id={user_id}, new_until={date}"
        )

        # отправка картинки пользователю
        if user_id:
            try:
                photo = FSInputFile("bot/assets/Подписка активна-1.png")
                await bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption=LEXICON_SUBSCRIBE["after_promocode_text"].format(
                        date=date.strftime("%d.%m.%Y")
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке фото пользователю {user_id}: {e}")

        return JSONResponse(content={"status": "ok", "user_id": user_id, "mail": mail})

    except Exception as e:
        logger.error(f"Ошибка в process_getcourse_update: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)})


@app.get(f"{WEBHOOK_PATH}/prolong")
async def process_getcourse_extension(
    gc_date: str = "",
    mail: str = "",
):
    try:
        date = await parse_date(gc_date)
        date = date + timedelta(hours=12)
        user_id, new_text = await set_new_days(mail=mail, days=date)
        print(f"Получен платёж: email {mail}")

        if user_id:
            try:
                photo = FSInputFile("bot/assets/Подписка активна-1.png")
                await bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption=LEXICON_SUBSCRIBE["after_prolong_text"].format(
                        date=date.strftime("%d.%m.%Y")
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке фото пользователю {user_id}: {e}")

        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(f"Ошибка в process_getcourse_extension: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)})


async def parse_date(date_str: str) -> datetime:
    parts = date_str.strip().split()
    if len(parts) != 3:
        logger.error(f"Неверный формат даты: {date_str}")
        # raise ValueError(f"Неверный формат даты: {date_str}")

    day, month_str, year = parts
    month = MONTHS[month_str.lower()[:3]]  # первые 3 буквы для универсальности
    dt = datetime(int(year), month, int(day), tzinfo=MOSCOW_TZ)
    return dt
