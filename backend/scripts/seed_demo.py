"""幂等 seed：3 账号 / 12 条政策 / 38 条条件 / 120 家企业 / 1 次匹配运行（40 条结果）。

自然键 upsert：
  users.email
  policies.code
  rules (policy_id, field, op, value)
  companies.code
  match_runs.seed_key
  matches (run_id, policy_id, company_id)
  audit_logs.seed_key

重复执行不新增、不覆盖用户改过的复核状态；SEED_SUMMARY 逐字一致。
"""
from __future__ import annotations

from sqlalchemy import func, select

from src.config.database import session_scope
from src.models.audit import AuditLog
from src.models.company import Company
from src.models.match import Match
from src.models.match_run import MatchRun
from src.models.policy import Policy
from src.models.rule import Rule
from src.models.user import User
from src.services import match_service, policy_service
from src.utils.security import hash_password
from src.utils.timeutil import parse_date

from scripts.demo_config import (
    COMPANIES,
    DEMO_PASSWORD,
    DEMO_USERS,
    ORG,
    POLICIES,
    SEED_RUN,
)


def ensure_users(db) -> int:
    for email, display_name, role in DEMO_USERS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            db.add(
                User(
                    email=email,
                    password_hash=hash_password(DEMO_PASSWORD),
                    display_name=display_name,
                    role=role,
                    org=ORG,
                )
            )
    db.flush()
    return db.scalar(select(func.count()).select_from(User)) or 0


def ensure_policies(db) -> list[Policy]:
    """自然键 code upsert：只同步台账主数据，不覆盖用户改过的 status。"""
    for spec in POLICIES:
        policy = db.scalar(select(Policy).where(Policy.code == spec["code"]))
        if policy is not None:
            policy.title = spec["title"]
            policy.issuer = spec["issuer"]
            policy.doc_no = spec["doc_no"]
            policy.source_kind = spec["source_kind"]
            policy.source_name = spec["source_name"]
            policy.published_on = parse_date(spec["published_on"])
            policy.deadline = parse_date(spec["deadline"])
            policy.fund_cap_wan = spec["fund_cap_wan"]
            policy.original_text = spec["text"]
            continue
        db.add(
            Policy(
                code=spec["code"],
                title=spec["title"],
                issuer=spec["issuer"],
                doc_no=spec["doc_no"],
                source_kind=spec["source_kind"],
                source_name=spec["source_name"],
                published_on=parse_date(spec["published_on"]),
                deadline=parse_date(spec["deadline"]),
                fund_cap_wan=spec["fund_cap_wan"],
                original_text=spec["text"],
                status=spec["status"],
            )
        )
    db.flush()
    return list(db.scalars(select(Policy).order_by(Policy.id)).all())


def ensure_rules(db, policies: list[Policy]) -> int:
    by_code = {item.code: item for item in policies}
    for spec in POLICIES:
        policy = by_code.get(spec["code"])
        if policy is None:
            continue
        policy_service.extract_and_store(db, policy)
    db.flush()
    return db.scalar(select(func.count()).select_from(Rule)) or 0


def ensure_companies(db) -> int:
    for index, spec in enumerate(COMPANIES, start=1):
        code = f"C{index:04d}"
        company = db.scalar(select(Company).where(Company.code == code))
        if company is not None:
            continue
        db.add(
            Company(
                code=code,
                name=spec["name"],
                industry=spec["industry"],
                district=spec["district"],
                revenue_wan=float(spec["revenue_wan"]),
                rd_ratio=float(spec["rd_ratio"]),
                employees=int(spec["employees"]),
                qualifications=list(spec["qualifications"]),
                contact=spec["contact"],
                owner=spec["owner"],
            )
        )
    db.flush()
    return db.scalar(select(func.count()).select_from(Company)) or 0


def ensure_match_run(db) -> MatchRun:
    return match_service.run_matching(
        db,
        operator_email=SEED_RUN["operator_email"],
        trigger=SEED_RUN["trigger"],
        policy_codes=SEED_RUN["policy_codes"],
        seed_key=SEED_RUN["seed_key"],
    )


def ensure_audit(db) -> None:
    seeds = [
        ("seed-audit-1", "admin@policyfit.io", "admin", "policy.create", "policy", {"code": "P2026-ZJTX"}),
        ("seed-audit-2", "analyst@policyfit.io", "analyst", "match.run", "match_run", {"label": SEED_RUN["label"]}),
    ]
    for seed_key, email, role, action, entity, detail in seeds:
        exists = db.scalar(select(AuditLog).where(AuditLog.seed_key == seed_key))
        if exists is None:
            db.add(
                AuditLog(
                    actor_email=email,
                    actor_role=role,
                    action=action,
                    entity=entity,
                    detail=detail,
                    layer="seed",
                    seed_key=seed_key,
                )
            )
    db.flush()


def seed_all() -> dict:
    with session_scope() as db:
        users = ensure_users(db)
        policies = ensure_policies(db)
        ensure_rules(db, policies)
        ensure_companies(db)
        ensure_match_run(db)
        ensure_audit(db)

        policy_count = db.scalar(select(func.count()).select_from(Policy)) or 0
        channels = db.scalar(select(func.count(func.distinct(Policy.source_name)))) or 0
        runs = db.scalar(select(func.count()).select_from(MatchRun)) or 0
        matches = db.scalar(select(func.count()).select_from(Match)) or 0
        pending = db.scalar(select(func.count()).select_from(Match).where(Match.status == "pending")) or 0
        rules = db.scalar(select(func.count()).select_from(Rule)) or 0
        companies = db.scalar(select(func.count()).select_from(Company)) or 0
        summary = (
            f"SEED_SUMMARY brand=policyfit users={users} sources={channels} "
            f"runs={runs} findings={matches} pending={pending}"
        )
        print(summary, flush=True)
        print(
            f"SEED_DETAIL policies={policy_count} rules={rules} companies={companies} "
            f"p0={db.scalar(select(func.count()).select_from(Match).where(Match.priority == 'P0')) or 0}",
            flush=True,
        )
        return {
            "users": users,
            "sources": channels,
            "runs": runs,
            "findings": matches,
            "pending": pending,
            "policies": policy_count,
            "rules": rules,
            "companies": companies,
        }


if __name__ == "__main__":
    seed_all()
