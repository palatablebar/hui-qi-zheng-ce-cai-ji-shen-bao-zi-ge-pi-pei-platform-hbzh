from __future__ import annotations

from pydantic import BaseModel, Field


class MatchRunIn(BaseModel):
    trigger: str = Field(default="manual", max_length=20)
    policy_codes: list[str] = Field(default_factory=list, max_length=20)
