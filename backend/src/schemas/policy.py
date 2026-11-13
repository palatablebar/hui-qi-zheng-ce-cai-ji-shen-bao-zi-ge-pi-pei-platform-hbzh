from __future__ import annotations

from pydantic import BaseModel, Field

from src.constants.enums import PolicyStatus


class PolicyIn(BaseModel):
    code: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    title: str = Field(min_length=2, max_length=200)
    issuer: str = Field(min_length=2, max_length=120)
    doc_no: str | None = Field(default=None, max_length=80)
    source_kind: str = Field(default="website", max_length=20)
    source_name: str | None = Field(default=None, max_length=120)
    published_on: str | None = Field(default=None, max_length=10)
    deadline: str | None = Field(default=None, max_length=10)
    fund_cap_wan: int | None = Field(default=None, ge=0, le=1000000)
    original_text: str = Field(default="", max_length=20000)
    status: str = Field(default=PolicyStatus.DRAFT.value, max_length=12)


class PolicyPatch(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    issuer: str | None = Field(default=None, min_length=2, max_length=120)
    doc_no: str | None = Field(default=None, max_length=80)
    source_kind: str | None = Field(default=None, max_length=20)
    source_name: str | None = Field(default=None, max_length=120)
    published_on: str | None = Field(default=None, max_length=10)
    deadline: str | None = Field(default=None, max_length=10)
    fund_cap_wan: int | None = Field(default=None, ge=0, le=1000000)
    original_text: str | None = Field(default=None, max_length=20000)
    status: str | None = Field(default=None, max_length=12)
