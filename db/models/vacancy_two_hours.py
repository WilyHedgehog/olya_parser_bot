from sqlalchemy import Integer, Float, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID
from sqlalchemy import text

from db.models.mixins import TimestampMixin
from db import Base


class VacancyTwoHours(TimestampMixin, Base):
    # Очередь вакансий для отложенной отправки пользователям
    __tablename__ = "vacancy_two_hours"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    profession_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="vacancy_two_hours")
