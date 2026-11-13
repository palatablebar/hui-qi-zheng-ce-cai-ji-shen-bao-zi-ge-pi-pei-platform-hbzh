"""申报条件：由政策原文抽取出的结构化条件（算法 A 的产物）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base
from src.utils.timeutil import utcnow


class Rule(Base):
    __tablename__ = "rules"
    __table_args__ = (
        UniqueConstraint("policy_id", "field", "op", "value", name="uq_rules_policy_condition"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    policy_id: Mapped[int] = mapped_column(
        ForeignKey("policies.id", ondelete="CASCADE"), index=True
    )
    field: Mapped[str] = mapped_column(String(24), index=True)
    op: Mapped[str] = mapped_column(String(8))
    value: Mapped[str] = mapped_column(String(64))
    unit: Mapped[str] = mapped_column(String(16), default="")
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.9)
    evidence_sentence: Mapped[str] = mapped_column(Text, default="")
    seed_key: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
