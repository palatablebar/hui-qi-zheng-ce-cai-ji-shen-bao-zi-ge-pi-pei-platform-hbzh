"""企业画像服务：客户台账 CRUD（viewer 不下发联系人电话）。

画像字段的直接写入已改为「更正留痕」流程（见 correction_service）：
本模块 update_company 仅保留给登记主数据（名称/联系人/客户经理等非指标字段），
指标字段的变更统一走 /corrections，核验通过才回写。
"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.models.company import Company
from src.models.profile_correction import ProfileCorrection
from src.utils.errors import AppError, not_found
from src.utils.timeutil import iso_utc


def serialize(
    company: Company,
    *,
    include_contact: bool = True,
    pending_count: int = 0,
) -> dict:
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
        "pending_corrections": pending_count,
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


def update_company(db: Session, company: Company, payload: dict, *, actor_email: str = "") -> dict:
    """更新企业画像。

    指标字段（industry/district/revenue_wan/rd_ratio/employees/qualifications）
    不再直接覆盖，而是转成「待核验」更正留痕；只有核验通过才回写画像并参与匹配。
    名称 / 联系人 / 客户经理等台账主数据仍直接更新。
    返回 {"company": ..., "corrections": [...待核验更正]}。
    """
    from src.constants.enums import PROFILE_FIELDS, RuleField
    from src.services import correction_service

    indicator_columns = {
        "industry": RuleField.INDUSTRY.value,
        "district": RuleField.REGION.value,
        "revenue_wan": RuleField.REVENUE_WAN.value,
        "rd_ratio": RuleField.RD_RATIO.value,
        "employees": RuleField.EMPLOYEES.value,
        "qualifications": RuleField.QUALIFICATION.value,
    }
    corrections = []
    direct_payload = dict(payload)
    for column, profile_field in indicator_columns.items():
        if column not in payload or payload[column] is None:
            continue
        direct_payload.pop(column, None)
        if profile_field not in PROFILE_FIELDS:
            continue
        try:
            correction = correction_service.submit_correction(
                db,
                company,
                {
                    "field": profile_field,
                    "new_value": payload[column],
                    "source": "manual",
                    "source_ref": "画像编辑表单",
                    "note": "由企业画像编辑提交，待核验",
                },
                submitted_by=actor_email or "system",
            )
        except AppError as exc:
            # 与当前画像一致等冲突场景：忽略该字段，其余字段照常处理
            if exc.code == "CONFLICT":
                continue
            raise
        corrections.append(correction)

    for field in ("name", "contact", "owner"):
        if field in direct_payload and direct_payload[field] is not None:
            setattr(company, field, direct_payload[field])
    db.flush()
    return {"company": company, "corrections": corrections}


def company_corrections(db: Session, company_id: int, *, limit: int = 50) -> list[ProfileCorrection]:
    return list(
        db.scalars(
            select(ProfileCorrection)
            .where(ProfileCorrection.company_id == company_id)
            .order_by(ProfileCorrection.received_at.desc(), ProfileCorrection.id.desc())
            .limit(limit)
        ).all()
    )


def industries(db: Session) -> list[str]:
    return [row for (row,) in db.execute(select(Company.industry).distinct().order_by(Company.industry)).all()]


def districts(db: Session) -> list[str]:
    return [row for (row,) in db.execute(select(Company.district).distinct().order_by(Company.district)).all()]
