from sqlalchemy import Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column


from db import Base

class Admins(Base):
    # Список администраторов бота
    __tablename__ = "admins"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    is_admin : Mapped[bool] = mapped_column(default=False, nullable=False)
    is_superadmin : Mapped[bool] = mapped_column(default=False, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)