from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.middlewares.rbac import READ_ROLES, require_roles
from src.services import company_service, policy_service

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("/options")
def options(db: Session = Depends(get_db), principal: dict = Depends(require_roles(*READ_ROLES))) -> dict:
    """筛选下拉的可选值（来自台账真实数据，不写死在前端）。"""
    return {
        "issuers": policy_service.issuers(db),
        "industries": company_service.industries(db),
        "districts": company_service.districts(db),
        "qualifications": ["高新技术企业", "专精特新", "软件企业", "科技型中小企业", "企业技术中心"],
    }
