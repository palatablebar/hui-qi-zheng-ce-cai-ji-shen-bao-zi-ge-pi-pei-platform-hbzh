"""画像更正服务：更正留痕、核验回写、匹配影响测算。

核心口径：
  - submit_correction：任何画像变更都先落一条 ProfileCorrection（pending 不回写画像）；
  - verify_correction：核验通过才把新值回写 companies，并测算对历史匹配的前后影响；
  - reject_correction：驳回不改画像，仅留痕；
  - 只有 verified 值参与下一次匹配；匹配引擎读取的 companies 即「已核验画像」。
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constants.enums import (
    CORRECTION_SOURCE_LABELS,
    CORRECTION_SOURCE_TRUST,
    CORRECTION_STATUS_LABELS,
    CorrectionSource,
    CorrectionStatus,
    PROFILE_FIELDS,
    RULE_FIELD_LABELS,
    RuleField,
)
from src.models.company import Company
from src.models.match import Match
from src.models.match_run import MatchRun
from src.models.policy import Policy
from src.models.profile_correction import ProfileCorrection
from src.services import match_engine
from src.utils.errors import AppError, not_found
from src.utils.timeutil import iso_utc, local_now, utcnow

# 画像快照字段（匹配引擎 company_ctx 的键 + 展示名）
SNAPSHOT_FIELDS: tuple[str, ...] = (
    "code",
    "name",
    "industry",
    "district",
    "revenue_wan",
    "rd_ratio",
    "employees",
    "qualifications",
)

# correction.field 与 company 属性名的映射（region 落在 district 列）
FIELD_TO_COLUMN: dict[str, str] = {
    RuleField.INDUSTRY.value: "industry",
    RuleField.REGION.value: "district",
    RuleField.REVENUE_WAN.value: "revenue_wan",
    RuleField.RD_RATIO.value: "rd_ratio",
    RuleField.EMPLOYEES.value: "employees",
    RuleField.QUALIFICATION.value: "qualifications",
}


def build_snapshot(company: Company) -> dict:
    """固化一家企业当前（已核验）画像，供匹配运行存档。"""
    return {
        "code": company.code,
        "name": company.name,
        "industry": company.industry,
        "district": company.district,
        "revenue_wan": company.revenue_wan,
        "rd_ratio": company.rd_ratio,
        "employees": company.employees,
        "qualifications": list(company.qualifications or []),
    }


def _encode(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return "、".join(str(item) for item in value)
    return str(value)


def _parse_new_value(field: str, raw: object) -> object:
    """按字段类型把入参规整为画像列可存储的 Python 值。"""
    if raw is None:
        raise AppError("VALIDATION", 422, {"field": field, "reason": "新值不能为空"})
    if field == RuleField.QUALIFICATION.value:
        if isinstance(raw, str):
            value = [part.strip() for part in raw.replace(",", "、").split("、") if part.strip()]
        elif isinstance(raw, list):
            value = [str(part).strip() for part in raw if str(part).strip()]
        else:
            value = []
        if not value:
            raise AppError("VALIDATION", 422, {"field": field, "reason": "资质至少保留一项"})
        return value
    if field in (RuleField.REVENUE_WAN.value, RuleField.RD_RATIO.value):
        try:
            return round(float(raw), 4)
        except (TypeError, ValueError) as exc:
            raise AppError("VALIDATION", 422, {"field": field, "reason": "必须是数值"}) from exc
    if field == RuleField.EMPLOYEES.value:
        try:
            return int(float(raw))
        except (TypeError, ValueError) as exc:
            raise AppError("VALIDATION", 422, {"field": field, "reason": "必须是整数"}) from exc
    return str(raw).strip()


def _current_value(company: Company, field: str) -> object:
    return getattr(company, FIELD_TO_COLUMN[field])


def _apply_value(company: Company, field: str, value: object) -> None:
    setattr(company, FIELD_TO_COLUMN[field], value)


def serialize(correction: ProfileCorrection, *, company: Company | None = None) -> dict:
    return {
        "id": correction.id,
        "company_id": correction.company_id,
        "company_name": company.name if company else None,
        "company_code": company.code if company else None,
        "field": correction.field,
        "field_label": RULE_FIELD_LABELS.get(correction.field, correction.field),
        "old_value": correction.old_value,
        "new_value": correction.new_value,
        "source": correction.source,
        "source_label": CORRECTION_SOURCE_LABELS.get(correction.source, correction.source),
        "source_ref": correction.source_ref,
        "status": correction.status,
        "status_label": CORRECTION_STATUS_LABELS.get(correction.status, correction.status),
        "note": correction.note,
        "trust_level": correction.trust_level,
        "received_at": iso_utc(correction.received_at),
        "submitted_by": correction.submitted_by,
        "verified_at": iso_utc(correction.verified_at),
        "verified_by": correction.verified_by,
        "verify_note": correction.verify_note,
        "impact": correction.impact or {},
        "created_at": iso_utc(correction.created_at),
    }


def get_correction(db: Session, correction_id: int) -> ProfileCorrection:
    correction = db.get(ProfileCorrection, correction_id)
    if correction is None:
        raise not_found("profile_correction", correction_id)
    return correction


def list_corrections(
    db: Session,
    *,
    company_id: int | None = None,
    field: str | None = None,
    source: str | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    stmt = select(ProfileCorrection)
    count_stmt = select(func.count()).select_from(ProfileCorrection)
    for column, value in (
        (ProfileCorrection.company_id, company_id),
        (ProfileCorrection.field, field),
        (ProfileCorrection.source, source),
        (ProfileCorrection.status, status),
    ):
        if value:
            stmt = stmt.where(column == value)
            count_stmt = count_stmt.where(column == value)
    total = db.scalar(count_stmt) or 0
    rows = list(
        db.scalars(
            stmt.order_by(ProfileCorrection.received_at.desc(), ProfileCorrection.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    company_ids = {row.company_id for row in rows}
    companies = (
        {row.id: row for row in db.scalars(select(Company).where(Company.id.in_(company_ids))).all()}
        if company_ids
        else {}
    )
    return {
        "items": [serialize(row, company=companies.get(row.company_id)) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def pending_counts(db: Session) -> dict:
    """按企业汇总待核验更正数，供企业列表标红提醒。"""
    rows = db.execute(
        select(ProfileCorrection.company_id, func.count())
        .where(ProfileCorrection.status == CorrectionStatus.PENDING.value)
        .group_by(ProfileCorrection.company_id)
    ).all()
    return {company_id: count for company_id, count in rows}


def submit_correction(
    db: Session,
    company: Company,
    payload: dict,
    *,
    submitted_by: str,
) -> ProfileCorrection:
    field = payload["field"]
    if field not in PROFILE_FIELDS:
        raise AppError("VALIDATION", 422, {"field": field, "reason": "不在可更正画像字段范围内"})
    source = payload.get("source") or CorrectionSource.MANUAL.value
    if source not in CORRECTION_SOURCE_LABELS:
        raise AppError("VALIDATION", 422, {"source": source})
    new_value = _parse_new_value(field, payload.get("new_value"))
    current = _current_value(company, field)
    if _encode(current) == _encode(new_value):
        raise AppError(
            "CONFLICT",
            409,
            {"field": field, "reason": "新值与当前已核验画像一致，无需更正"},
        )
    correction = ProfileCorrection(
        company_id=company.id,
        field=field,
        old_value=_encode(current),
        new_value=_encode(new_value),
        source=source,
        source_ref=(payload.get("source_ref") or "")[:160],
        status=CorrectionStatus.PENDING.value,
        note=payload.get("note"),
        trust_level=CORRECTION_SOURCE_TRUST.get(source, 0.8),
        received_at=utcnow(),
        submitted_by=submitted_by,
    )
    db.add(correction)
    db.flush()
    return correction


def _rule_dicts(db: Session, policy_id: int) -> list[dict]:
    from src.models.rule import Rule

    rules = list(
        db.scalars(select(Rule).where(Rule.policy_id == policy_id).order_by(Rule.id)).all()
    )
    return [
        {
            "field": item.field,
            "op": item.op,
            "value": item.value,
            "unit": item.unit,
            "required": item.required,
            "confidence": item.confidence,
            "evidence_sentence": item.evidence_sentence,
        }
        for item in rules
    ]


def _measure_impact(db: Session, company: Company, field: str, new_value: object) -> dict:
    """用「旧画像 vs 更正后画像」对该企业全部历史匹配重算，给出前后影响。

    历史 Match 本身保持不变（快照固化）；这里只产出影响摘要，供工作台回看。
    """
    history = list(
        db.scalars(select(Match).where(Match.company_id == company.id).order_by(Match.id)).all()
    )
    if not history:
        return {"matched_runs": 0, "affected_runs": 0, "items": [], "summary": "该企业暂无历史匹配，更正将作用于下一次匹配"}

    policies = {row.id: row for row in db.scalars(select(Policy)).all()}
    runs = {row.id: row for row in db.scalars(select(MatchRun)).all()}
    items: list[dict] = []
    affected = 0
    for match in history:
        policy = policies.get(match.policy_id)
        run = runs.get(match.run_id)
        if policy is None or run is None:
            continue
        reference = _run_today(run)
        rules = _rule_dicts(db, policy.id)
        policy_ctx = {
            "code": policy.code,
            "title": policy.title,
            "deadline": policy.deadline.isoformat() if policy.deadline else None,
        }
        before_ctx = dict(match.company_snapshot or build_snapshot(company))
        after_ctx = dict(before_ctx)
        after_ctx[field if field != RuleField.REGION.value else "district"] = new_value
        before = match_engine.evaluate(before_ctx, rules, policy_ctx, reference)
        after = match_engine.evaluate(after_ctx, rules, policy_ctx, reference)
        delta = round(after["score"] - before["score"], 1)
        changed = (
            delta != 0
            or before["hard_pass"] != after["hard_pass"]
            or before["priority"] != after["priority"]
        )
        if changed:
            affected += 1
        items.append(
            {
                "match_id": match.id,
                "run_id": run.id,
                "run_no": run.run_no,
                "policy_code": policy.code,
                "policy_title": policy.title,
                "score_before": before["score"],
                "score_after": after["score"],
                "score_delta": delta,
                "hard_pass_before": before["hard_pass"],
                "hard_pass_after": after["hard_pass"],
                "priority_before": before["priority"],
                "priority_after": after["priority"],
                "gaps_after": after["gaps"],
                "changed": changed,
            }
        )
    improved = sum(1 for item in items if item["changed"] and item["score_delta"] > 0)
    worsened = sum(1 for item in items if item["changed"] and item["score_delta"] < 0)
    summary = (
        f"影响 {affected} 次历史匹配口径（得分上升 {improved}、下降 {worsened}）；"
        "历史结果不重写，差异在下一次匹配生效"
    )
    return {"matched_runs": len(history), "affected_runs": affected, "items": items, "summary": summary}


def _run_today(run: MatchRun) -> date:
    params = run.params or {}
    today = params.get("today")
    if isinstance(today, str):
        try:
            return date.fromisoformat(today[:10])
        except ValueError:
            pass
    return local_now().date()


def verify_correction(
    db: Session,
    correction: ProfileCorrection,
    *,
    verifier: str,
    verify_note: str | None,
) -> ProfileCorrection:
    if correction.status != CorrectionStatus.PENDING.value:
        raise AppError(
            "CONFLICT",
            409,
            {"id": correction.id, "status": correction.status, "reason": "仅待核验更正可核验"},
        )
    company = db.get(Company, correction.company_id)
    if company is None:
        raise not_found("company", correction.company_id)
    new_value = _parse_new_value(correction.field, correction.new_value)
    impact = _measure_impact(db, company, correction.field, new_value)
    _apply_value(company, correction.field, new_value)
    correction.status = CorrectionStatus.VERIFIED.value
    correction.verified_at = utcnow()
    correction.verified_by = verifier
    correction.verify_note = verify_note
    correction.impact = impact
    db.flush()
    return correction


def reject_correction(
    db: Session,
    correction: ProfileCorrection,
    *,
    verifier: str,
    verify_note: str | None,
) -> ProfileCorrection:
    if correction.status != CorrectionStatus.PENDING.value:
        raise AppError(
            "CONFLICT",
            409,
            {"id": correction.id, "status": correction.status, "reason": "仅待核验更正可驳回"},
        )
    correction.status = CorrectionStatus.REJECTED.value
    correction.verified_at = utcnow()
    correction.verified_by = verifier
    correction.verify_note = verify_note
    correction.impact = {"summary": "已驳回，新值不进入画像与匹配"}
    db.flush()
    return correction


def field_options() -> list[dict]:
    return [
        {"value": field, "label": RULE_FIELD_LABELS[field]}
        for field in PROFILE_FIELDS
    ]


def source_options() -> list[dict]:
    return [
        {"value": source, "label": CORRECTION_SOURCE_LABELS[source]}
        for source in CorrectionSource
    ]
