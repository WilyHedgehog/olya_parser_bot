from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from config.config import load_config

config = load_config()
engine = create_async_engine(
    url=config.database.url,
    echo=config.database.echo,
)

Sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
