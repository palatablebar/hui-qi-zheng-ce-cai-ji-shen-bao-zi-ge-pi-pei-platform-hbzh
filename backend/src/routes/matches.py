from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import REVIEW_ROLES
from src.controllers import match_controller
from src.middlewares.rbac import READ_ROLES, require_roles
from src.schemas.match import MatchReviewIn
from src.utils.pagination import page_params

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("")
def list_matches(
    run_id: int | None = None,
    policy_id: int | None = None,
    company_id: int | None = None,
    priority: str | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = Query(20),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    page = page_params(limit, offset)
    return match_controller.list_matches(
        db,
        principal,
        run_id=run_id,
        policy_id=policy_id,
        company_id=company_id,
        priority=priority,
        status=status,
        q=q,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{match_id}")
def get_match(match_id: int, db: Session = Depends(get_db), principal: dict = Depends(require_roles(*READ_ROLES))) -> dict:
    return match_controller.get_match(db, match_id, principal)


@router.patch("/{match_id}/review")
def review(
    match_id: int,
    payload: MatchReviewIn,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*REVIEW_ROLES)),
) -> dict:
    return match_controller.review(db, match_id, payload.model_dump(), principal, request)
