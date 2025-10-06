from sqlalchemy import Integer, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID
from sqlalchemy import text

from db import Base
from db.models.mixins import TimestampMixin


class Vacancy(TimestampMixin, Base):
    # Список вакансий, найденных парсером
    __tablename__ = "vacancies"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    profession_id: Mapped[UUID] = mapped_column(ForeignKey("professions.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=True)
    hash: Mapped[str] = mapped_column(Text, nullable=True, unique=True, index=True)
    vacancy_source: Mapped[str] = mapped_column(Text, nullable=True)
    forwarding_source: Mapped[str] = mapped_column(Text, nullable=True)

    profession: Mapped["Profession"] = relationship(back_populates="vacancies")
    sent_to_users: Mapped[list["VacancySent"]] = relationship(back_populates="vacancy", cascade="all, delete-orphan")
