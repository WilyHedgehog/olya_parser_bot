from sqlalchemy import Integer, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID
from sqlalchemy import text

from db import Base
from db.models.mixins import TimestampMixin


class VacancyStat(TimestampMixin, Base):
    # Список вакансий, найденных парсером
    __tablename__ = "vacancy_stats"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    profession_name: Mapped[str] = mapped_column(Text, nullable=False)
