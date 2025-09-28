from uuid import UUID
from sqlalchemy import Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from db import Base


class Profession(Base):
    # Профессии, по которым ищем вакансии
    __tablename__ = "professions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    desc: Mapped[str] = mapped_column(Text, nullable=True)
    
    # связь с таблицей user_professions
    user_professions: Mapped[list["UserProfession"]] = relationship(
        back_populates="profession"
    )
    # связь с ключевыми словами
    keywords: Mapped[list["Keyword"]] = relationship(
        back_populates="profession", cascade="all, delete-orphan"
    )
    vacancies: Mapped[list["Vacancy"]] = relationship(
        back_populates="profession", cascade="all, delete-orphan"
    )
