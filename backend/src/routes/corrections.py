from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import COMPANY_WRITE_ROLES
from src.controllers import correction_controller
from src.middlewares.rbac import READ_ROLES, require_roles
from src.schemas.correction import CorrectionIn, CorrectionVerifyIn

router = APIRouter(prefix="/corrections", tags=["corrections"])


@router.get("")
def list_corrections(
    company_id: int | None = None,
    field: str | None = None,
    source: str | None = None,
    status: str | None = None,
    limit: int = Query(20),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    return correction_controller.list_corrections(
        db,
        principal,
        company_id=company_id,
        field=field,
        source=source,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/{correction_id}")
def get_correction(
    correction_id: int,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    return correction_controller.get_correction(db, correction_id)


@router.post("/company/{company_id}", status_code=201)
def submit_correction(
    company_id: int,
    payload: CorrectionIn,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*COMPANY_WRITE_ROLES)),
) -> dict:
    return correction_controller.submit(db, company_id, payload.model_dump(), principal, request)


@router.patch("/{correction_id}/verify")
def verify_correction(
    correction_id: int,
    payload: CorrectionVerifyIn,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*COMPANY_WRITE_ROLES)),
) -> dict:
    return correction_controller.verify(db, correction_id, payload.model_dump(), principal, request)


@router.patch("/{correction_id}/reject")
def reject_correction(
    correction_id: int,
    payload: CorrectionVerifyIn,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*COMPANY_WRITE_ROLES)),
) -> dict:
    return correction_controller.reject(db, correction_id, payload.model_dump(), principal, request)
