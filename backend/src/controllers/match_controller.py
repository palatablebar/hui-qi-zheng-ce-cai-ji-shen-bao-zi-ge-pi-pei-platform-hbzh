"""匹配控制器：运行、结果查询、复核。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.constants.roles import can_see_contact
from src.services import audit_service, match_service


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def create_run(db: Session, payload: dict, principal: dict, request: Request) -> dict:
    run = match_service.run_matching(
        db,
        operator_email=principal["email"],
        trigger=payload.get("trigger") or "manual",
        policy_codes=payload.get("policy_codes") or None,
    )
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="match.run",
        entity="match_run",
        entity_id=run.id,
        detail={
            "run_no": run.run_no,
            "policies": run.policy_count,
            "companies": run.company_count,
            "matches": run.match_count,
            "p0": run.p0_count,
        },
        ip=_ip(request),
    )
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="match.complete",
        entity="match_run",
        entity_id=run.id,
        detail={"status": run.status, "match_count": run.match_count},
        ip=_ip(request),
    )
    db.commit()
    return match_service.serialize_run(run)


def list_runs(db: Session, **filters) -> dict:
    return match_service.list_runs(db, **filters)


def get_run(db: Session, run_id: int) -> dict:
    return match_service.serialize_run(match_service.get_run(db, run_id))


def list_matches(db: Session, principal: dict, **filters) -> dict:
    page = match_service.list_matches(db, **filters)
    if not can_see_contact(principal["role"]):
        for item in page["items"]:
            item["payload"] = {
                key: value
                for key, value in (item.get("payload") or {}).items()
                if key not in {"contact"}
            }
    return page


def get_match(db: Session, match_id: int, principal: dict) -> dict:
    data = match_service.detail(db, match_service.get_match(db, match_id))
    if not can_see_contact(principal["role"]) and data.get("company"):
        data["company"]["contact"] = "***"
    return data


def review(db: Session, match_id: int, payload: dict, principal: dict, request: Request) -> dict:
    match = match_service.get_match(db, match_id)
    match_service.review(
        db,
        match,
        status=payload["status"],
        note=payload.get("note"),
        reviewer=principal["email"],
    )
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="match.review",
        entity="match",
        entity_id=match.id,
        detail={"status": match.status, "score": match.score, "priority": match.priority},
        ip=_ip(request),
    )
    db.commit()
    return match_service.detail(db, match)
