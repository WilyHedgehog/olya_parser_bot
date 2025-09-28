from sqlalchemy import Integer, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID
from sqlalchemy import text

from db import Base


class UserProfession(Base):
    # Связка: какой пользователь связан с какой профессией
    __tablename__ = "user_professions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    profession_id: Mapped[UUID] = mapped_column(ForeignKey("professions.id"))
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    __table_args__ = (
        UniqueConstraint("user_id", "profession_id", name="uq_user_profession"),
    )

    user: Mapped["User"] = relationship(back_populates="professions")
    profession: Mapped["Profession"] = relationship(back_populates="user_professions")