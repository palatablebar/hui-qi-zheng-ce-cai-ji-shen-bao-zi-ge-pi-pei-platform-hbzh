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
    # 该企业最近一次「已核验」更正来源，作为画像依据列（快照值本身来自历次已核验更正）
    latest_verified = _latest_verified_source(db)
    matches.sort(key=lambda item: (PRIORITY_SORT.get(item.priority, 9), -(item.score or 0), item.id))
    headers = [
        "序号", "运行编号", "政策编号", "政策标题", "发文机关", "申报截止",
        "企业名称", "所属行业", "注册地", "营业收入(万元)", "研发占比(%)",
        "员工人数", "匹配得分", "优先级", "硬条件", "缺口提示", "复核状态", "复核人", "复核备注",
        "画像口径", "画像依据来源", "快照时间",
    ]
    rows = []
    for index, item in enumerate(matches, start=1):
        policy = policies.get(item.policy_id)
        company = companies.get(item.company_id)
        run = runs.get(item.run_id)
        snapshot = item.company_snapshot or {}
        # 申报依据以匹配当时固化的快照为准，画像后续更正不改变本清单
        industry = snapshot.get("industry") or (company.industry if company else "")
        district = snapshot.get("district") or (company.district if company else "")
        revenue = snapshot.get("revenue_wan")
        rd_ratio = snapshot.get("rd_ratio")
        employees = snapshot.get("employees")
        source_label = latest_verified.get(item.company_id, "")
        rows.append(
            [
                index,
                run.run_no if run else "",
                policy.code if policy else "",
                policy.title if policy else "",
                policy.issuer if policy else "",
                policy.deadline.isoformat() if policy and policy.deadline else "",
                snapshot.get("name") or (company.name if company else ""),
                industry,
                district,
                f"{revenue:g}" if revenue is not None else "",
                f"{rd_ratio:g}" if rd_ratio is not None else "",
                employees if employees is not None else "",
                f"{item.score:.1f}",
                PRIORITY_LABELS.get(item.priority, item.priority),
                "通过" if item.hard_pass else "未通过",
                "；".join(item.gaps or []),
                REVIEW_STATUS_LABELS.get(item.status, item.status),
                item.reviewer or "",
                item.note or "",
                "匹配时快照（不受后续更正影响）" if snapshot else "当前画像",
                source_label,
                item.created_at.strftime("%Y-%m-%d %H:%M") if item.created_at else "",
            ]
        )
    return to_csv(headers, rows), len(matches)


def _latest_verified_source(db: Session) -> dict[int, str]:
    """每家企业最近一条已核验更正的来源标签。"""
    from src.constants.enums import CORRECTION_SOURCE_LABELS
    from src.models.profile_correction import ProfileCorrection

    rows = list(
        db.scalars(
            select(ProfileCorrection)
            .where(ProfileCorrection.status == "verified")
            .order_by(ProfileCorrection.verified_at.desc(), ProfileCorrection.id.desc())
        ).all()
    )
    result: dict[int, str] = {}
    for row in rows:
        if row.company_id not in result:
            result[row.company_id] = CORRECTION_SOURCE_LABELS.get(row.source, row.source)
    return result


def corrections_csv(db: Session, company_id: int | None = None) -> tuple[bytes, int]:
    from src.constants.enums import (
        CORRECTION_SOURCE_LABELS,
        CORRECTION_STATUS_LABELS,
        RULE_FIELD_LABELS,
    )
    from src.models.profile_correction import ProfileCorrection

    stmt = select(ProfileCorrection)
    if company_id:
        stmt = stmt.where(ProfileCorrection.company_id == company_id)
    rows_data = list(
        db.scalars(
            stmt.order_by(ProfileCorrection.received_at.desc(), ProfileCorrection.id.desc())
        ).all()
    )
    company_map = {item.id: item for item in db.scalars(select(Company)).all()}
    headers = [
        "序号", "企业编号", "企业名称", "更正字段", "更正前", "更正后",
        "来源", "来源单号", "可信度", "收到时间", "确认状态",
        "核验人", "核验时间", "核验备注", "影响摘要",
    ]
    rows = []
    for index, item in enumerate(rows_data, start=1):
        company = company_map.get(item.company_id)
        rows.append(
            [
                index,
                company.code if company else "",
                company.name if company else "",
                RULE_FIELD_LABELS.get(item.field, item.field),
                item.old_value or "",
                item.new_value or "",
                CORRECTION_SOURCE_LABELS.get(item.source, item.source),
                item.source_ref or "",
                f"{item.trust_level:.2f}",
                item.received_at.strftime("%Y-%m-%d %H:%M") if item.received_at else "",
                CORRECTION_STATUS_LABELS.get(item.status, item.status),
                item.verified_by or "",
                item.verified_at.strftime("%Y-%m-%d %H:%M") if item.verified_at else "",
                item.verify_note or "",
                (item.impact or {}).get("summary", ""),
            ]
        )
    return to_csv(headers, rows), len(rows_data)


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
