"""画像更正控制器：提交留痕、核验/驳回、查询（viewer 只读）。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.services import audit_service, correction_service
from src.utils.pagination import page_params


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def list_corrections(db: Session, principal: dict, **filters) -> dict:
    page = page_params(filters.pop("limit", 20), filters.pop("offset", 0))
    return correction_service.list_corrections(
        db,
        company_id=filters.get("company_id"),
        field=filters.get("field"),
        source=filters.get("source"),
        status=filters.get("status"),
        limit=page.limit,
        offset=page.offset,
    )


def get_correction(db: Session, correction_id: int) -> dict:
    correction = correction_service.get_correction(db, correction_id)
    from src.models.company import Company

    company = db.get(Company, correction.company_id)
    return correction_service.serialize(correction, company=company)


def submit(db: Session, company_id: int, payload: dict, principal: dict, request: Request) -> dict:
    from src.models.company import Company
    from src.utils.errors import not_found

    company = db.get(Company, company_id)
    if company is None:
        raise not_found("company", company_id)
    correction = correction_service.submit_correction(
        db, company, payload, submitted_by=principal["email"]
    )
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="correction.submit",
        entity="profile_correction",
        entity_id=correction.id,
        detail={
            "company_id": company.id,
            "field": correction.field,
            "source": correction.source,
            "old": correction.old_value,
            "new": correction.new_value,
        },
        ip=_ip(request),
    )
    db.commit()
    return correction_service.serialize(correction, company=company)


def verify(db: Session, correction_id: int, payload: dict, principal: dict, request: Request) -> dict:
    from src.models.company import Company

    correction = correction_service.get_correction(db, correction_id)
    correction_service.verify_correction(
        db, correction, verifier=principal["email"], verify_note=payload.get("note")
    )
    company = db.get(Company, correction.company_id)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="correction.verify",
        entity="profile_correction",
        entity_id=correction.id,
        detail={
            "company_id": correction.company_id,
            "field": correction.field,
            "new": correction.new_value,
            "impact": correction.impact.get("summary"),
        },
        ip=_ip(request),
    )
    db.commit()
    return correction_service.serialize(correction, company=company)


def reject(db: Session, correction_id: int, payload: dict, principal: dict, request: Request) -> dict:
    from src.models.company import Company

    correction = correction_service.get_correction(db, correction_id)
    correction_service.reject_correction(
        db, correction, verifier=principal["email"], verify_note=payload.get("note")
    )
    company = db.get(Company, correction.company_id)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="correction.reject",
        entity="profile_correction",
        entity_id=correction.id,
        detail={"company_id": correction.company_id, "field": correction.field},
        ip=_ip(request),
    )
    db.commit()
    return correction_service.serialize(correction, company=company)
