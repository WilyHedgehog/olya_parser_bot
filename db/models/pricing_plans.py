from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship


from db import Base

class PricingPlan(Base):
    # Ценовые планы для пользователей
    __tablename__ = "pricing_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    offer_code: Mapped[String] = mapped_column(String, default='-')
    offer_id: Mapped[String] = mapped_column(String, default='-')