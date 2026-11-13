"""企业画像控制器（viewer 掩码联系人电话）。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.constants.roles import can_see_contact
from src.services import audit_service, company_service


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def list_companies(db: Session, principal: dict, **filters) -> dict:
    page = company_service.list_companies(db, **filters)
    include_contact = can_see_contact(principal["role"])
    page["items"] = [company_service.serialize(item, include_contact=include_contact) for item in page["items"]]
    return page


def get_company(db: Session, company_id: int, principal: dict) -> dict:
    company = company_service.get_company(db, company_id)
    return company_service.serialize(company, include_contact=can_see_contact(principal["role"]))


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
    company_service.update_company(db, company, payload)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="company.update",
        entity="company",
        entity_id=company.id,
        detail={"fields": list(payload.keys())},
        ip=_ip(request),
    )
    db.commit()
    return company_service.serialize(company, include_contact=True)
