"""总览：政策台账 / 待办匹配 / 截止周历 / 采集渠道 / 后台任务。"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants.enums import (
    CHANNEL_KIND_LABELS,
    CONFIDENCE_REVIEW_THRESHOLD,
    POLICY_STATUS_LABELS,
    PRIORITY_LABELS,
    PRIORITY_ORDER,
    REVIEW_STATUS_LABELS,
)
from src.models.company import Company
from src.models.match import Match
from src.models.match_run import MatchRun
from src.models.policy import Policy
from src.models.rule import Rule
from src.utils.timeutil import iso_date, iso_utc, local_now


def worker_alive() -> bool:
    try:
        import redis
        import time

        client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
        value = client.get(f"{settings.app_name}:worker:heartbeat")
        return bool(value) and (time.time() - float(value)) < 120
    except Exception:
        return False


def _deadline_calendar(db: Session, today) -> list[dict]:
    horizon = today + timedelta(days=6)
    rows = list(
        db.scalars(
            select(Policy)
            .where(Policy.status == "active", Policy.deadline.is_not(None), Policy.deadline <= horizon)
            .order_by(Policy.deadline)
        ).all()
    )
    days: list[dict] = []
    for offset in range(7):
        day = today + timedelta(days=offset)
        day_policies = [item for item in rows if item.deadline == day]
        days.append(
            {
                "date": day.isoformat(),
                "label": f"{day.month}/{day.day}",
                "count": len(day_policies),
                "codes": [item.code for item in day_policies],
                "titles": [item.title for item in day_policies],
            }
        )
    return days


def overview(db: Session) -> dict:
    today = local_now().date()
    policies_total = db.scalar(select(func.count()).select_from(Policy)) or 0
    active_total = db.scalar(select(func.count()).select_from(Policy).where(Policy.status == "active")) or 0
    companies_total = db.scalar(select(func.count()).select_from(Company)) or 0
    matches_total = db.scalar(select(func.count()).select_from(Match)) or 0
    pending_total = db.scalar(select(func.count()).select_from(Match).where(Match.status == "pending")) or 0
    rules_total = db.scalar(select(func.count()).select_from(Rule)) or 0
    low_rules = (
        db.scalar(select(func.count()).select_from(Rule).where(Rule.confidence < CONFIDENCE_REVIEW_THRESHOLD)) or 0
    )
    latest_run = db.scalar(select(MatchRun).order_by(MatchRun.id.desc()).limit(1))
    latest_match = db.scalar(select(Match).order_by(Match.id.desc()).limit(1))

    priority_rows = db.execute(select(Match.priority, func.count()).group_by(Match.priority)).all()
    priority_map = {key: count for key, count in priority_rows}
    review_rows = db.execute(select(Match.status, func.count()).group_by(Match.status)).all()
    review_map = {key: count for key, count in review_rows}
    channel_rows = db.execute(select(Policy.source_kind, func.count()).group_by(Policy.source_kind)).all()
    status_rows = db.execute(select(Policy.status, func.count()).group_by(Policy.status)).all()

    upcoming = list(
        db.scalars(
            select(Policy)
            .where(Policy.status == "active", Policy.deadline.is_not(None))
            .order_by(Policy.deadline)
            .limit(6)
        ).all()
    )

    pending_matches = list(
        db.scalars(select(Match).where(Match.status == "pending").order_by(Match.score.desc(), Match.id).limit(6)).all()
    )
    company_names = {
        row.id: row.name for row in db.scalars(select(Company)).all()
    }
    policy_titles = {
        row.id: (row.code, row.title) for row in db.scalars(select(Policy)).all()
    }

    high_match_companies = (
        db.scalar(
            select(func.count(func.distinct(Match.company_id))).where(Match.priority.in_(["P0", "P1"]))
        )
        or 0
    )

    return {
        "policies_total": policies_total,
        "active_total": active_total,
        "companies_total": companies_total,
        "matches_total": matches_total,
        "pending_total": pending_total,
        "rules_total": rules_total,
        "low_confidence_rules": low_rules,
        "high_match_companies": high_match_companies,
        "p0_total": priority_map.get("P0", 0),
        "worker_alive": worker_alive(),
        "today": today.isoformat(),
        "latest_run": {
            "id": latest_run.id,
            "run_no": latest_run.run_no,
            "status": latest_run.status,
            "match_count": latest_run.match_count,
            "p0_count": latest_run.p0_count,
            "started_at": iso_utc(latest_run.started_at),
        }
        if latest_run
        else None,
        "latest_match_score": latest_match.score if latest_match else None,
        "priority": [
            {"key": key, "label": PRIORITY_LABELS.get(key, key), "count": priority_map.get(key, 0)}
            for key in PRIORITY_ORDER
        ],
        "review": [
            {"key": key, "label": REVIEW_STATUS_LABELS.get(key, key), "count": review_map.get(key, 0)}
            for key in ("pending", "confirmed", "dismissed")
        ],
        "channels": [
            {"key": key, "label": CHANNEL_KIND_LABELS.get(key, key), "count": count}
            for key, count in sorted(channel_rows, key=lambda item: -item[1])
        ],
        "status_mix": [
            {"key": key, "label": POLICY_STATUS_LABELS.get(key, key), "count": count}
            for key, count in sorted(status_rows)
        ],
        "deadline_calendar": _deadline_calendar(db, today),
        "upcoming": [
            {
                "id": item.id,
                "code": item.code,
                "title": item.title,
                "issuer": item.issuer,
                "deadline": iso_date(item.deadline),
                "fund_cap_wan": item.fund_cap_wan,
            }
            for item in upcoming
        ],
        "pending_matches": [
            {
                "id": item.id,
                "policy_code": policy_titles.get(item.policy_id, ("", ""))[0],
                "policy_title": policy_titles.get(item.policy_id, ("", ""))[1],
                "company_name": company_names.get(item.company_id, ""),
                "score": item.score,
                "priority": item.priority,
                "gaps": item.gaps or [],
            }
            for item in pending_matches
        ],
    }
