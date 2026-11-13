"""政策控制器：写操作记领域审计，抽取条件单独记一条。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.services import audit_service, policy_service


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def list_policies(db: Session, **filters) -> dict:
    return policy_service.list_policies(db, **filters)


def get_policy(db: Session, policy_id: int) -> dict:
    policy = policy_service.get_policy(db, policy_id)
    rules = policy_service.rules_of(db, policy.id)
    return policy_service.serialize(policy, rules)


def create_policy(db: Session, payload: dict, principal: dict, request: Request) -> dict:
    policy = policy_service.create_policy(db, payload)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="policy.create",
        entity="policy",
        entity_id=policy.id,
        detail={"code": policy.code, "title": policy.title},
        ip=_ip(request),
    )
    db.commit()
    return policy_service.serialize(policy, [])


def update_policy(db: Session, policy_id: int, payload: dict, principal: dict, request: Request) -> dict:
    policy = policy_service.get_policy(db, policy_id)
    policy_service.update_policy(db, policy, payload)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="policy.update",
        entity="policy",
        entity_id=policy.id,
        detail={"fields": list(payload.keys())},
        ip=_ip(request),
    )
    db.commit()
    return policy_service.serialize(policy, policy_service.rules_of(db, policy.id))


def extract_rules(db: Session, policy_id: int, principal: dict, request: Request) -> dict:
    policy = policy_service.get_policy(db, policy_id)
    result = policy_service.extract_and_store(db, policy)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="rule.extract",
        entity="rule",
        entity_id=policy.id,
        detail={
            "policy_code": policy.code,
            "created": result["created"],
            "updated": result["updated"],
            "removed": result["removed"],
            "low_confidence": len(result["low_confidence"]),
            "unparsed": len(result["unparsed"]),
        },
        ip=_ip(request),
    )
    db.commit()
    return result


def list_rules(db: Session, policy_id: int) -> dict:
    policy = policy_service.get_policy(db, policy_id)
    rules = policy_service.rules_of(db, policy.id)
    return {
        "policy_id": policy.id,
        "policy_code": policy.code,
        "items": [policy_service.serialize_rule(item) for item in rules],
        "total": len(rules),
    }
