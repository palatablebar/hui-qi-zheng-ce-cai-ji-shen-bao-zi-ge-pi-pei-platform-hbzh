"""政策台账：一条政府发文 + 原文（条件抽取的输入）。"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base
from src.utils.timeutil import utcnow


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    issuer: Mapped[str] = mapped_column(String(120))
    doc_no: Mapped[str] = mapped_column(String(80), default="")
    source_kind: Mapped[str] = mapped_column(String(20), default="website")
    source_name: Mapped[str] = mapped_column(String(120), default="")
    published_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    fund_cap_wan: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="active", index=True)
    seed_key: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
