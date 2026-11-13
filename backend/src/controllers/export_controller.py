"""导出控制器：CSV 响应 + 审计。"""
from __future__ import annotations

from fastapi import Request, Response
from sqlalchemy.orm import Session

from src.services import audit_service, export_service
from src.utils.csv_export import csv_response_headers


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def matches_csv(db: Session, run_id: int | None, principal: dict, request: Request) -> Response:
    content, count = export_service.matches_csv(db, run_id)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="export.matches",
        entity="match",
        entity_id=run_id,
        detail={"rows": count, "bytes": len(content)},
        ip=_ip(request),
    )
    db.commit()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers=csv_response_headers("policyfit-matches.csv"),
    )


def policies_csv(db: Session, principal: dict, request: Request) -> Response:
    content, count = export_service.policies_csv(db)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="export.policies",
        entity="policy",
        entity_id=None,
        detail={"rows": count, "bytes": len(content)},
        ip=_ip(request),
    )
    db.commit()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers=csv_response_headers("policyfit-policies.csv"),
    )


def corrections_csv(
    db: Session, company_id: int | None, principal: dict, request: Request
) -> Response:
    content, count = export_service.corrections_csv(db, company_id)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="export.corrections",
        entity="profile_correction",
        entity_id=company_id,
        detail={"rows": count, "bytes": len(content)},
        ip=_ip(request),
    )
    db.commit()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers=csv_response_headers("policyfit-corrections.csv"),
    )
