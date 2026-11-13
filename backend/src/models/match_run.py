"""一次资格匹配运行：输入窗口、口径参数、产出统计、日志。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base
from src.utils.timeutil import utcnow


class MatchRun(Base):
    __tablename__ = "match_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    trigger: Mapped[str] = mapped_column(String(20), default="manual")
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    operator_email: Mapped[str] = mapped_column(String(160), default="system")
    policy_count: Mapped[int] = mapped_column(Integer, default=0)
    company_count: Mapped[int] = mapped_column(Integer, default=0)
    match_count: Mapped[int] = mapped_column(Integer, default=0)
    p0_count: Mapped[int] = mapped_column(Integer, default=0)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    log_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    seed_key: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
