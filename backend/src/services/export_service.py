"""导出服务：申报清单 CSV（按优先级/得分排序）与政策台账 CSV。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constants.enums import (
    CONFIDENCE_REVIEW_THRESHOLD,
    POLICY_STATUS_LABELS,
    PRIORITY_LABELS,
    REVIEW_STATUS_LABELS,
)
from src.models.company import Company
from src.models.match import Match
from src.models.match_run import MatchRun
from src.models.policy import Policy
from src.models.rule import Rule
from src.utils.csv_export import to_csv

PRIORITY_SORT = {"P0": 0, "P1": 1, "P2": 2}


def matches_csv(db: Session, run_id: int | None = None) -> tuple[bytes, int]:
    stmt = select(Match)
    if run_id:
        stmt = stmt.where(Match.run_id == run_id)
    matches = list(db.scalars(stmt).all())
    policies = {item.id: item for item in db.scalars(select(Policy)).all()}
    companies = {item.id: item for item in db.scalars(select(Company)).all()}
    runs = {item.id: item for item in db.scalars(select(MatchRun)).all()}
    matches.sort(key=lambda item: (PRIORITY_SORT.get(item.priority, 9), -(item.score or 0), item.id))
    headers = [
        "序号", "运行编号", "政策编号", "政策标题", "发文机关", "申报截止",
        "企业名称", "所属行业", "注册地", "营业收入(万元)", "研发占比(%)",
        "员工人数", "匹配得分", "优先级", "硬条件", "缺口提示", "复核状态", "复核人", "复核备注",
    ]
    rows = []
    for index, item in enumerate(matches, start=1):
        policy = policies.get(item.policy_id)
        company = companies.get(item.company_id)
        run = runs.get(item.run_id)
        rows.append(
            [
                index,
                run.run_no if run else "",
                policy.code if policy else "",
                policy.title if policy else "",
                policy.issuer if policy else "",
                policy.deadline.isoformat() if policy and policy.deadline else "",
                company.name if company else "",
                company.industry if company else "",
                company.district if company else "",
                f"{company.revenue_wan:g}" if company else "",
                f"{company.rd_ratio:g}" if company else "",
                company.employees if company else "",
                f"{item.score:.1f}",
                PRIORITY_LABELS.get(item.priority, item.priority),
                "通过" if item.hard_pass else "未通过",
                "；".join(item.gaps or []),
                REVIEW_STATUS_LABELS.get(item.status, item.status),
                item.reviewer or "",
                item.note or "",
            ]
        )
    return to_csv(headers, rows), len(matches)


def policies_csv(db: Session) -> tuple[bytes, int]:
    policies = list(db.scalars(select(Policy).order_by(Policy.id)).all())
    rule_counts = {
        policy_id: count
        for policy_id, count in db.execute(select(Rule.policy_id, func.count()).group_by(Rule.policy_id)).all()
    }
    low_counts = {
        policy_id: count
        for policy_id, count in db.execute(
            select(Rule.policy_id, func.count())
            .where(Rule.confidence < CONFIDENCE_REVIEW_THRESHOLD)
            .group_by(Rule.policy_id)
        ).all()
    }
    headers = [
        "政策编号", "标题", "发文机关", "文号", "采集渠道", "状态",
        "申报截止", "资助上限(万元)", "条件数", "低置信条件数", "原文长度",
    ]
    rows = [
        [
            item.code,
            item.title,
            item.issuer,
            item.doc_no,
            item.source_name,
            POLICY_STATUS_LABELS.get(item.status, item.status),
            item.deadline.isoformat() if item.deadline else "",
            item.fund_cap_wan if item.fund_cap_wan is not None else "",
            rule_counts.get(item.id, 0),
            low_counts.get(item.id, 0),
            len(item.original_text or ""),
        ]
        for item in policies
    ]
    return to_csv(headers, rows), len(policies)
