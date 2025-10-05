from dataclasses import dataclass
from environs import Env


@dataclass
class TgBot:
    token: str  # Токен для доступа к телеграм-боту
    webhook_url: str  # Полный URL вебхука (например https://domain.com/webhook)
    admin_ids: list[int] = (
        None  # Список ID администраторов бота (по умолчанию пустой список)
    )
    chat_id: int = None  # ID чата для отправки уведомлений
    wacancy_chat_id: int = None  # ID чата для отправки вакансий
    support_chat_id: int = None  # ID чата для поддержки


@dataclass
class AppSettings:
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True


@dataclass
class DatabaseSettings:
    url: str
    echo: bool = False


@dataclass
class LogSettings:
    level: str
    format: str


@dataclass
class ParserSettings:
    api_id: int
    api_hash: str
    phone_number: str
    delay_min: int
    delay_max: int


@dataclass
class GetcourseSettings:
    api_key: str
    product_id: str
    group_id: str
    gc_name: str


@dataclass
class NatsSettings:
    servers: list[str]


@dataclass
class Config:
    bot: TgBot
    app: AppSettings
    log: LogSettings
    parser: ParserSettings
    database: DatabaseSettings
    getcourse: GetcourseSettings
    nats: NatsSettings


def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path)
    return Config(
        bot=TgBot(
            token=env("BOT_TOKEN"),
            webhook_url=env("WEBHOOK_URL"),
            admin_ids=env.list("ADMIN_IDS"),
            chat_id=env.int("CHAT_ID"),
            wacancy_chat_id=env.int("WACANCY_CHAT_ID"),
            support_chat_id=env.int("SUPPORT_CHAT_ID"),
        ),
        app=AppSettings(
            host=env.str("HOST", "0.0.0.0"),
            port=env.int("PORT", 8000),
            reload=env.bool("RELOAD", True),
        ),
        log=LogSettings(
            level=env.str("LOG_LEVEL", "INFO"),
            format=env.str("LOG_FORMAT", "%(asctime)s - %(levelname)s - %(message)s"),
        ),
        parser=ParserSettings(
            api_id=env.int("API_ID"),
            api_hash=env("API_HASH"),
            phone_number=env("PHONE_NUMBER"),
            delay_min=env.int("DELAY_MIN"),
            delay_max=env.int("DELAY_MAX"),
        ),
        database=DatabaseSettings(
            url=env("DATABASE_URL"),
            echo=env.bool("DATABASE_ECHO", False),
        ),
        getcourse=GetcourseSettings(
            api_key=env("GETCOURSE_API_KEY"),
            product_id=env("PAY_PRODUCT_ID"),
            group_id=env("GETCOURSE_GROUP_ID"),
            gc_name=env("GETCOURSE_ACCOUNT"),
        ),
        nats=NatsSettings(
            servers=env.list("NATS_SERVERS"),
        )
    )