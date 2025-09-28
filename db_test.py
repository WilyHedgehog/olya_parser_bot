import asyncio
from datetime import datetime
from uuid import UUID
from sqlalchemy import ForeignKey
from sqlalchemy import BigInteger, Integer, DateTime, Text, func, Uuid, text, Float
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import select
from sqlalchemy.orm import selectinload


from sqlalchemy import ForeignKey, BigInteger, Integer, Boolean, Text, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime


class Base(DeclarativeBase):
    pass


async def main():
    engine = create_async_engine(
        # Строка подключения при использовании Docker-образов из репозитория
        # В противном случае подставьте свои значения
        url="postgresql+psycopg://superuser:superpassword@127.0.0.1:5433/data",
        echo=False,
    )

    # Удаление предыдущей версии базы
    # и создание таблиц заново
    async with engine.begin() as connection:
        await connection.execute(text("DROP TABLE IF EXISTS user_professions CASCADE"))
        await connection.execute(text("DROP TABLE IF EXISTS keywords CASCADE"))
        await connection.execute(text("DROP TABLE IF EXISTS professions CASCADE"))
        await connection.execute(text("DROP TABLE IF EXISTS users CASCADE"))
        await connection.execute(text("DROP TABLE IF EXISTS vacancies CASCADE"))
        await connection.execute(text("DROP TABLE IF EXISTS vacancy_sent CASCADE"))
        await connection.execute(text("DROP TABLE IF EXISTS user_promos CASCADE"))
        await connection.execute(text("DROP TABLE IF EXISTS promo_codes CASCADE"))
        


# Точка входа
if __name__ == "__main__":
    asyncio.run(main())
