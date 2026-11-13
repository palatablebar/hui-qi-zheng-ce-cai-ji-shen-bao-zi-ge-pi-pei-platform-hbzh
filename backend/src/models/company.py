"""企业画像：资格匹配的对照对象（客户台账）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base
from src.utils.timeutil import utcnow


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    industry: Mapped[str] = mapped_column(String(40), index=True)
    district: Mapped[str] = mapped_column(String(24), index=True)
    revenue_wan: Mapped[float] = mapped_column(Float, default=0.0)
    rd_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    employees: Mapped[int] = mapped_column(Integer, default=0)
    qualifications: Mapped[list] = mapped_column(JSON, default=list)
    contact: Mapped[str] = mapped_column(String(40), default="")
    owner: Mapped[str] = mapped_column(String(80), default="")
    seed_key: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
