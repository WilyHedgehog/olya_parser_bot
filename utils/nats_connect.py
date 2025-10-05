import nats
from nats.aio.client import Client
from nats.js import JetStreamContext
from nats.js.api import StreamConfig
from logging import getLogger
from config.config import load_config
config = load_config()

logger = getLogger(__name__)


async def connect_to_nats(servers=config.nats.servers) -> tuple[Client, JetStreamContext]:
    
    nc: Client = await nats.connect(servers)
    js: JetStreamContext = nc.jetstream()

    return nc, js


async def setup_vacancy_stream(js):
    # Проверим, существует ли уже поток
    streams = await js.streams_info()
    if any(stream.config.name == "VACANCY_TASKS" for stream in streams):
        logger.info("✅ Stream VACANCY_TASKS уже существует")
        return

    await js.add_stream(
        StreamConfig(
            name="VACANCY_TASKS",
            subjects=["vacancy.queue"],
            retention="workq",
        )
    )
    logger.info("🚀 Stream VACANCY_TASKS создан")