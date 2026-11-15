from sqlalchemy import String, Double, JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class Audit(Base):
    __tablename__ = 'audits'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(150))
    action: Mapped[str] = mapped_column(String(80))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    at: Mapped[float] = mapped_column(Double)
    lab_id: Mapped[int | None] = mapped_column(ForeignKey('labs.id'), nullable=True)
class LabClaim(Base):
    """平台管理员对旧数据整链（批次→分析→计划→归档）的认领记录。"""
    __tablename__ = 'lab_claims'
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey('datasets.id'))
    lab_id: Mapped[int | None] = mapped_column(ForeignKey('labs.id'), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    actor: Mapped[str] = mapped_column(String(150), default='')
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    conflict_reason: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[float] = mapped_column(Double)
    updated_at: Mapped[float] = mapped_column(Double)
