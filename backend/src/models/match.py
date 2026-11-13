"""匹配结果：政策 × 企业 的一条资格匹配（算法 B 的产物）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base
from src.utils.timeutil import utcnow


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("run_id", "policy_id", "company_id", name="uq_matches_run_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("match_runs.id", ondelete="CASCADE"), index=True
    )
    policy_id: Mapped[int] = mapped_column(
        ForeignKey("policies.id", ondelete="CASCADE"), index=True
    )
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    score: Mapped[float] = mapped_column(Float, default=0.0)
    hard_pass: Mapped[bool] = mapped_column(Boolean, default=False)
    gaps: Mapped[list] = mapped_column(JSON, default=list)
    priority: Mapped[str] = mapped_column(String(4), default="P2", index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    reviewer: Mapped[str | None] = mapped_column(String(160), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    # 匹配运行当时固化的企业画像快照：画像后续更正不影响本条结果，保证申报依据可回看
    company_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
