"""画像更正台账：每个字段每次更正一条不可变留痕。

设计口径（对应需求）：
  - 同一指标先后到达、可信度不同：每条更正独立留痕，不覆盖历史；
  - 保留来源 source、收到时间 received_at、确认状态 status；
  - 只有 status=verified（核验通过）的值才回写 companies 并进入下一次匹配；
  - pending / rejected 不影响当前画像；
  - verified_at / reviewer 记录核验动作，impact 缓存对匹配结果的前后影响。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base
from src.utils.timeutil import utcnow


class ProfileCorrection(Base):
    __tablename__ = "profile_corrections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    field: Mapped[str] = mapped_column(String(24), index=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual", index=True)
    source_ref: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    trust_level: Mapped[float] = mapped_column(Float, default=0.8)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    submitted_by: Mapped[str] = mapped_column(String(160), default="")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    verify_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 核验通过时计算：对历次匹配（快照口径）的影响摘要
    impact: Mapped[dict] = mapped_column(JSON, default=dict)
    seed_key: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
