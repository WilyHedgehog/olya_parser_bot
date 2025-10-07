from sqlalchemy import Integer, BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from db import Base
from .mixins import TimestampMixin


class SupportMessage(Base, TimestampMixin):
    __tablename__ = "support_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    admin_chat_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    admin_response: Mapped[str] = mapped_column(String, nullable=True)