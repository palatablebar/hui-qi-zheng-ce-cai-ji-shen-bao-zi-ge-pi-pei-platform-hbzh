"""路由聚合：统一 /api 前缀（Nginx 反代时剥掉 /api）。"""
from fastapi import APIRouter

from src.routes.audit import router as audit_router
from src.routes.auth import router as auth_router
from src.routes.companies import router as companies_router
from src.routes.exports import router as exports_router
from src.routes.health import router as health_router
from src.routes.match_runs import router as match_runs_router
from src.routes.matches import router as matches_router
from src.routes.options import router as options_router
from src.routes.overview import router as overview_router
from src.routes.policies import router as policies_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(overview_router)
api_router.include_router(options_router)
api_router.include_router(policies_router)
api_router.include_router(companies_router)
api_router.include_router(match_runs_router)
api_router.include_router(matches_router)
api_router.include_router(exports_router)
api_router.include_router(audit_router)
