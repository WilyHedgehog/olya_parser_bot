# db/models.py
from sqlalchemy import BigInteger, String, DateTime, Boolean, Text
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from .mixins import TimestampMixin

from ..base import Base

class AdminMailing(Base, TimestampMixin):
    __tablename__ = "admin_mailings"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    task_name: Mapped[str] = mapped_column(String, nullable=True)  # Task name
    taskiq_id: Mapped[str] = mapped_column(String, unique=True, nullable=True)   # Taskiq task_id
    message: Mapped[str] = mapped_column(Text, nullable=False) # Message text
    run_at: Mapped[datetime] = mapped_column(DateTime, nullable=False) # When to run the task
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False) # Has the user cancelled this task
    executed: Mapped[bool] = mapped_column(Boolean, default=False) # Has the task been executed
    file_id: Mapped[str] = mapped_column(String, nullable=True)  # Optional file_id for sending files/photos
    keyboard: Mapped[str] = mapped_column(String, nullable=True)  # Optional JSON-serialized keyboard
    segment: Mapped[dict] = mapped_column(JSONB, nullable=True)  # Optional JSON segment for targeted mailing