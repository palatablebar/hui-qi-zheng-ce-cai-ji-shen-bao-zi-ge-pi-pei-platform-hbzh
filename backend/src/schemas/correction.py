from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ProfileFieldLiteral = Literal[
    "industry",
    "region",
    "revenue_wan",
    "rd_ratio",
    "employees",
    "qualification",
]


class CorrectionIn(BaseModel):
    field: ProfileFieldLiteral
    new_value: str | list[str] = Field(description="数值/文本传字符串；资质可传字符串数组")
    source: Literal["registry", "customer", "annual", "manual"] = "manual"
    source_ref: str | None = Field(default="", max_length=160)
    note: str | None = Field(default=None, max_length=1000)


class CorrectionVerifyIn(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


# ProfileFieldLiteral 的取值需与 constants.enums.PROFILE_FIELDS 保持一致：
# {"industry", "region", "revenue_wan", "rd_ratio", "employees", "qualification"}
