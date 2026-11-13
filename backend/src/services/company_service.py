"""企业画像服务：客户台账 CRUD（viewer 不下发联系人电话）。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.models.company import Company
from src.utils.errors import AppError, not_found
from src.utils.timeutil import iso_utc


def serialize(company: Company, *, include_contact: bool = True) -> dict:
    data = {
        "id": company.id,
        "code": company.code,
        "name": company.name,
        "industry": company.industry,
        "district": company.district,
        "revenue_wan": company.revenue_wan,
        "rd_ratio": company.rd_ratio,
        "employees": company.employees,
        "qualifications": company.qualifications or [],
        "owner": company.owner,
        "created_at": iso_utc(company.created_at),
    }
    data["contact"] = company.contact if include_contact else "***"
    data["contact_masked"] = not include_contact
    return data


def list_companies(
    db: Session,
    *,
    q: str | None = None,
    industry: str | None = None,
    district: str | None = None,
    qualification: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    stmt = select(Company)
    count_stmt = select(func.count()).select_from(Company)
    if q:
        like = f"%{q.strip()}%"
        clause = or_(Company.name.ilike(like), Company.code.ilike(like))
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)
    if industry:
        stmt = stmt.where(Company.industry == industry)
        count_stmt = count_stmt.where(Company.industry == industry)
    if district:
        stmt = stmt.where(Company.district == district)
        count_stmt = count_stmt.where(Company.district == district)
    total = db.scalar(count_stmt) or 0
    rows = list(db.scalars(stmt.order_by(Company.id).limit(limit).offset(offset)).all())
    if qualification:
        rows = [row for row in rows if qualification in (row.qualifications or [])]
    return {"items": rows, "total": total, "limit": limit, "offset": offset}


def get_company(db: Session, company_id: int) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise not_found("company", company_id)
    return company


def create_company(db: Session, payload: dict) -> Company:
    exists = db.scalar(select(Company).where(Company.code == payload["code"]))
    if exists is not None:
        raise AppError("CONFLICT", 409, {"code": payload["code"]})
    company = Company(
        code=payload["code"],
        name=payload["name"],
        industry=payload["industry"],
        district=payload["district"],
        revenue_wan=float(payload.get("revenue_wan") or 0),
        rd_ratio=float(payload.get("rd_ratio") or 0),
        employees=int(payload.get("employees") or 0),
        qualifications=list(payload.get("qualifications") or []),
        contact=payload.get("contact") or "",
        owner=payload.get("owner") or "",
    )
    db.add(company)
    db.flush()
    return company


def update_company(db: Session, company: Company, payload: dict) -> Company:
    for field in ("name", "industry", "district", "qualifications", "contact", "owner"):
        if field in payload and payload[field] is not None:
            setattr(company, field, payload[field])
    for field in ("revenue_wan", "rd_ratio"):
        if field in payload and payload[field] is not None:
            setattr(company, field, float(payload[field]))
    if "employees" in payload and payload["employees"] is not None:
        company.employees = int(payload["employees"])
    db.flush()
    return company


def industries(db: Session) -> list[str]:
    return [row for (row,) in db.execute(select(Company.industry).distinct().order_by(Company.industry)).all()]


def districts(db: Session) -> list[str]:
    return [row for (row,) in db.execute(select(Company.district).distinct().order_by(Company.district)).all()]
