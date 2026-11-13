from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import EXTRACT_ROLES, POLICY_WRITE_ROLES
from src.controllers import policy_controller
from src.middlewares.rbac import READ_ROLES, require_roles
from src.schemas.policy import PolicyIn, PolicyPatch
from src.utils.pagination import page_params

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("")
def list_policies(
    q: str | None = None,
    status: str | None = None,
    issuer: str | None = None,
    channel: str | None = None,
    deadline_within: int | None = Query(default=None, ge=0, le=365),
    limit: int = Query(20),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    page = page_params(limit, offset)
    return policy_controller.list_policies(
        db,
        q=q,
        status=status,
        issuer=issuer,
        channel=channel,
        deadline_within=deadline_within,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{policy_id}")
def get_policy(policy_id: int, db: Session = Depends(get_db), principal: dict = Depends(require_roles(*READ_ROLES))) -> dict:
    return policy_controller.get_policy(db, policy_id)


@router.get("/{policy_id}/rules")
def list_rules(policy_id: int, db: Session = Depends(get_db), principal: dict = Depends(require_roles(*READ_ROLES))) -> dict:
    return policy_controller.list_rules(db, policy_id)


@router.post("", status_code=201)
def create_policy(
    payload: PolicyIn,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*POLICY_WRITE_ROLES)),
) -> dict:
    return policy_controller.create_policy(db, payload.model_dump(), principal, request)


@router.patch("/{policy_id}")
def update_policy(
    policy_id: int,
    payload: PolicyPatch,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*POLICY_WRITE_ROLES)),
) -> dict:
    return policy_controller.update_policy(db, policy_id, payload.model_dump(exclude_unset=True), principal, request)


@router.post("/{policy_id}/extract-rules")
def extract_rules(
    policy_id: int,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*EXTRACT_ROLES)),
) -> dict:
    return policy_controller.extract_rules(db, policy_id, principal, request)
