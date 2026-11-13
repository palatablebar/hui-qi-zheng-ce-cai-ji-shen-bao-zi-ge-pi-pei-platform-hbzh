from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import COMPANY_WRITE_ROLES
from src.controllers import company_controller
from src.middlewares.rbac import READ_ROLES, require_roles
from src.schemas.company import CompanyIn, CompanyPatch
from src.utils.pagination import page_params

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("")
def list_companies(
    q: str | None = None,
    industry: str | None = None,
    district: str | None = None,
    qualification: str | None = None,
    limit: int = Query(20),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    page = page_params(limit, offset)
    return company_controller.list_companies(
        db,
        principal,
        q=q,
        industry=industry,
        district=district,
        qualification=qualification,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{company_id}")
def get_company(company_id: int, db: Session = Depends(get_db), principal: dict = Depends(require_roles(*READ_ROLES))) -> dict:
    return company_controller.get_company(db, company_id, principal)


@router.get("/{company_id}/corrections")
def get_company_corrections(
    company_id: int,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    return company_controller.get_company_corrections(db, company_id)


@router.post("", status_code=201)
def create_company(
    payload: CompanyIn,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*COMPANY_WRITE_ROLES)),
) -> dict:
    return company_controller.create_company(db, payload.model_dump(), principal, request)


@router.patch("/{company_id}")
def update_company(
    company_id: int,
    payload: CompanyPatch,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*COMPANY_WRITE_ROLES)),
) -> dict:
    return company_controller.update_company(
        db, company_id, payload.model_dump(exclude_unset=True), principal, request
    )
