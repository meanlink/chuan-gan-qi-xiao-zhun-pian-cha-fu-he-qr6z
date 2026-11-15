from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class Lab(Base):
    __tablename__ = 'labs'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    created_at: Mapped[float] = mapped_column(default=0.0)
