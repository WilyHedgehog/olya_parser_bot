from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID
from sqlalchemy import text


from db import Base

class StopWord(Base):
    # Список стоп-слов для фильтрации вакансий
    __tablename__ = "stop_words"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    word: Mapped[str] = mapped_column(String, unique=True, nullable=False)