from sqlalchemy import String, JSON, Double, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class Dataset(Base):
    __tablename__ = 'datasets'
    __table_args__ = (UniqueConstraint('lab_id','name',name='uq_datasets_lab_name'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    source: Mapped[str] = mapped_column(String(200), default='manual.json')
    records: Mapped[list] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[float] = mapped_column(Double)
    # 旧数据在平台管理员认领前 lab_id 为空，期间保持隔离，不允许执行与分发。
    lab_id: Mapped[int | None] = mapped_column(ForeignKey('labs.id'), nullable=True)
