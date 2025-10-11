# db/models.py
from sqlalchemy import BigInteger, String, DateTime, Boolean, Text
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base

class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    taskiq_id: Mapped[str] = mapped_column(String, unique=True, nullable=True)   # Taskiq task_id, обновляется после .kiq()
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    run_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    type: Mapped[str] = mapped_column(String, default="dunning", nullable=False)  # "dunning" | "admin" | ...
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    executed: Mapped[bool] = mapped_column(Boolean, default=False)