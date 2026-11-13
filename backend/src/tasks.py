"""Celery 任务：心跳、每日对全部申报中政策重跑一次资格匹配。"""
from __future__ import annotations

import time

from sqlalchemy import select

from src.config.celery_app import TASK_DAILY, TASK_HEARTBEAT, celery_app
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("tasks")


def _redis():
    import redis

    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


@celery_app.task(name=TASK_HEARTBEAT)
def heartbeat() -> str:
    try:
        _redis().set(f"{settings.app_name}:worker:heartbeat", time.time())
        return "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning("heartbeat failed: %s", exc)
        return "error"


@celery_app.task(name=TASK_DAILY)
def daily_match() -> dict:
    from src.config.database import session_scope
    from src.services import audit_service, match_service

    with session_scope() as db:
        run = match_service.run_matching(
            db,
            operator_email=f"scheduler@{settings.app_name}.io",
            trigger="schedule",
        )
        audit_service.record(
            db,
            actor_email=f"scheduler@{settings.app_name}.io",
            actor_role="admin",
            action="match.run",
            entity="match_run",
            entity_id=run.id,
            detail={"trigger": "schedule", "run_no": run.run_no, "matches": run.match_count},
            layer="worker",
        )
    logger.info("daily match finished: %s matches", run.match_count)
    return {"run_no": run.run_no, "matches": run.match_count}
