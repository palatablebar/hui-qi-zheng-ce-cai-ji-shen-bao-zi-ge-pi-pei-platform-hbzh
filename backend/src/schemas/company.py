from __future__ import annotations

from pydantic import BaseModel, Field


class CompanyIn(BaseModel):
    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(min_length=2, max_length=160)
    industry: str = Field(min_length=2, max_length=40)
    district: str = Field(min_length=2, max_length=24)
    revenue_wan: float = Field(default=0.0, ge=0, le=10_000_000)
    rd_ratio: float = Field(default=0.0, ge=0, le=100)
    employees: int = Field(default=0, ge=0, le=1_000_000)
    qualifications: list[str] = Field(default_factory=list)
    contact: str | None = Field(default="", max_length=40)
    owner: str | None = Field(default="", max_length=80)


class CompanyPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    industry: str | None = Field(default=None, min_length=2, max_length=40)
    district: str | None = Field(default=None, min_length=2, max_length=24)
    revenue_wan: float | None = Field(default=None, ge=0, le=10_000_000)
    rd_ratio: float | None = Field(default=None, ge=0, le=100)
    employees: int | None = Field(default=None, ge=0, le=1_000_000)
    qualifications: list[str] | None = None
    contact: str | None = Field(default=None, max_length=40)
    owner: str | None = Field(default=None, max_length=80)
