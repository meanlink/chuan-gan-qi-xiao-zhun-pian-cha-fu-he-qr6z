from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(150), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(20))
    password: Mapped[str] = mapped_column(String(300))
    # 平台管理员不归属任何实验室；业务角色必须归属一个实验室。
    lab_id: Mapped[int | None] = mapped_column(ForeignKey('labs.id'), nullable=True)
