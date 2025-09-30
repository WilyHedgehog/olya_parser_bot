from sqlalchemy import Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID
from sqlalchemy import text

from db import Base
from db.models.mixins import SentMixin


class VacancySent(SentMixin, Base):
    # Связка: какая вакансия была отправлена какому пользователю
    __tablename__ = "vacancy_sent"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    vacancy_id: Mapped[UUID] = mapped_column(ForeignKey("vacancies.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vacancy_text: Mapped[str | None] = mapped_column(nullable=True)
    
    __table_args__ = (
        UniqueConstraint("user_id", "vacancy_id", name="uq_user_vacancy"),
    )

    vacancy: Mapped["Vacancy"] = relationship(back_populates="sent_to_users")
    user: Mapped["User"] = relationship(back_populates="sent_vacancies")