from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship


from db import Base
from db.models.mixins import PromoMixin


class UserPromo(PromoMixin, Base):
    # Связка: какой промокод был использован каким пользователем
    __tablename__ = "user_promos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False
    )
    promo_id: Mapped[int] = mapped_column(
        ForeignKey("promo_codes.id", ondelete="CASCADE"),
        nullable=False
    )

    # связи для удобства
    user: Mapped["User"] = relationship("User", back_populates="promos_used")
    promo: Mapped["PromoCode"] = relationship("PromoCode", back_populates="users_used")