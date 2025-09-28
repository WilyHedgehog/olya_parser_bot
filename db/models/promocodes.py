from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship


from db import Base

class PromoCode(Base):
    # Промокоды для пользователей
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    days: Mapped[int] = mapped_column(Integer, nullable=False)  # сколько дней даёт
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None = безлимит
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    offer_code: Mapped[String] = mapped_column(String, default='-')
    offer_id: Mapped[String] = mapped_column(String, default='-')
    
    users_used: Mapped[list["UserPromo"]] = relationship(
        back_populates="promo", cascade="all, delete-orphan"
    )