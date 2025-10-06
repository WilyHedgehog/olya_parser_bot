from uuid import UUID
from sqlalchemy import ForeignKey, Text, UniqueConstraint, Float, text, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from db import Base

class Keyword(Base):
    # Ключевые слова для поиска вакансий по профессиям
    __tablename__ = "keywords"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    profession_id: Mapped[int] = mapped_column(ForeignKey("professions.id", ondelete="CASCADE"))
    profession_name: Mapped[str] = mapped_column(String, nullable=False)
    word: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    
    __table_args__ = (
        UniqueConstraint("profession_id", "word", name="uq_profession_word"),
    )

    profession: Mapped["Profession"] = relationship(back_populates="keywords", cascade="all, delete-orphan")