"""企业画像控制器（viewer 掩码联系人电话）。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.constants.roles import can_see_contact
from src.services import audit_service, company_service, correction_service


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def list_companies(db: Session, principal: dict, **filters) -> dict:
    page = company_service.list_companies(db, **filters)
    include_contact = can_see_contact(principal["role"])
    pending_map = correction_service.pending_counts(db)
    page["items"] = [
        company_service.serialize(
            item,
            include_contact=include_contact,
            pending_count=pending_map.get(item.id, 0),
        )
        for item in page["items"]
    ]
    page["pending_total"] = sum(pending_map.values())
    return page


def get_company(db: Session, company_id: int, principal: dict) -> dict:
    company = company_service.get_company(db, company_id)
    pending_map = correction_service.pending_counts(db)
    data = company_service.serialize(
        company,
        include_contact=can_see_contact(principal["role"]),
        pending_count=pending_map.get(company.id, 0),
    )
    return data


def get_company_corrections(db: Session, company_id: int) -> dict:
    company = company_service.get_company(db, company_id)
    rows = company_service.company_corrections(db, company.id)
    return {
        "company_id": company.id,
        "company_name": company.name,
        "items": [correction_service.serialize(row, company=company) for row in rows],
        "total": len(rows),
    }


def create_company(db: Session, payload: dict, principal: dict, request: Request) -> dict:
    company = company_service.create_company(db, payload)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="company.create",
        entity="company",
        entity_id=company.id,
        detail={"code": company.code, "name": company.name},
        ip=_ip(request),
    )
    db.commit()
    return company_service.serialize(company, include_contact=True)


def update_company(db: Session, company_id: int, payload: dict, principal: dict, request: Request) -> dict:
    company = company_service.get_company(db, company_id)
    result = company_service.update_company(db, company, payload, actor_email=principal["email"])
    updated = result["company"]
    queued = result["corrections"]
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="company.update",
        entity="company",
        entity_id=updated.id,
        detail={
            "direct_fields": [key for key in payload if key in ("name", "contact", "owner")],
            "queued_corrections": [
                {"id": item.id, "field": item.field, "source": item.source} for item in queued
            ],
        },
        ip=_ip(request),
    )
    for item in queued:
        audit_service.record(
            db,
            actor_email=principal["email"],
            actor_role=principal["role"],
            action="correction.submit",
            entity="profile_correction",
            entity_id=item.id,
            detail={"company_id": updated.id, "field": item.field, "source": item.source},
            ip=_ip(request),
        )
    db.commit()
    pending_map = correction_service.pending_counts(db)
    return company_service.serialize(
        updated, include_contact=True, pending_count=pending_map.get(updated.id, 0)
    )
