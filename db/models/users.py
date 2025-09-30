from sqlalchemy import BigInteger, String, Text, Boolean, DateTime
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship


from db import Base
from db.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    # Информация о пользователях бота
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=True)
    mail: Mapped[str] = mapped_column(String, nullable=True)
    active_promo: Mapped[str | None] = mapped_column(String, nullable=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
        # created_at добавляется из миксина
    subscription_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivery_mode: Mapped[str] = mapped_column(
        Text,
        default="instant",
        nullable=False,
    )
    first_price_offer_code: Mapped[str | None] = mapped_column(nullable=True)
    first_price_offer_id: Mapped[str | None] = mapped_column(nullable=True)
    is_pay_status: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    three_days_free_active: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    cancelled_subscription_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_autopay: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    from_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    professions: Mapped[list["UserProfession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sent_vacancies: Mapped[list["VacancySent"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    promos_used: Mapped[list["UserPromo"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    vacancy_queue: Mapped[list["VacancyQueue"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    vacancy_two_hours: Mapped[list["VacancyTwoHours"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )