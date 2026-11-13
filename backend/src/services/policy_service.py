"""政策服务：台账 CRUD、条件抽取与条件落库。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.constants.enums import (
    CHANNEL_KIND_LABELS,
    CONFIDENCE_REVIEW_THRESHOLD,
    POLICY_STATUS_LABELS,
    RULE_FIELD_LABELS,
    RULE_OP_LABELS,
)
from src.models.policy import Policy
from src.models.rule import Rule
from src.services import rule_extractor
from src.utils.errors import AppError, not_found
from src.utils.timeutil import iso_date, iso_utc, parse_date


def serialize_rules_summary(rules: list[Rule]) -> dict:
    low = [item for item in rules if item.confidence < CONFIDENCE_REVIEW_THRESHOLD]
    return {
        "rules_total": len(rules),
        "low_confidence_total": len(low),
    }


def serialize(policy: Policy, rules: list[Rule] | None = None, match_stats: dict | None = None) -> dict:
    rules = rules if rules is not None else []
    return {
        "id": policy.id,
        "code": policy.code,
        "title": policy.title,
        "issuer": policy.issuer,
        "doc_no": policy.doc_no,
        "source_kind": policy.source_kind,
        "source_kind_label": CHANNEL_KIND_LABELS.get(policy.source_kind, policy.source_kind),
        "source_name": policy.source_name,
        "published_on": iso_date(policy.published_on),
        "deadline": iso_date(policy.deadline),
        "fund_cap_wan": policy.fund_cap_wan,
        "original_text": policy.original_text,
        "status": policy.status,
        "status_label": POLICY_STATUS_LABELS.get(policy.status, policy.status),
        "created_at": iso_utc(policy.created_at),
        "rules": [serialize_rule(item) for item in rules],
        **serialize_rules_summary(rules),
        "match_stats": match_stats or {},
    }


def serialize_rule(rule: Rule) -> dict:
    return {
        "id": rule.id,
        "policy_id": rule.policy_id,
        "field": rule.field,
        "field_label": RULE_FIELD_LABELS.get(rule.field, rule.field),
        "op": rule.op,
        "op_label": RULE_OP_LABELS.get(rule.op, rule.op),
        "value": rule.value,
        "unit": rule.unit,
        "required": rule.required,
        "confidence": rule.confidence,
        "needs_review": rule.confidence < CONFIDENCE_REVIEW_THRESHOLD,
        "evidence_sentence": rule.evidence_sentence,
    }


def rules_of(db: Session, policy_id: int) -> list[Rule]:
    return list(db.scalars(select(Rule).where(Rule.policy_id == policy_id).order_by(Rule.id)).all())


def list_policies(
    db: Session,
    *,
    q: str | None = None,
    status: str | None = None,
    issuer: str | None = None,
    channel: str | None = None,
    deadline_within: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    stmt = select(Policy)
    count_stmt = select(func.count()).select_from(Policy)
    if q:
        like = f"%{q.strip()}%"
        clause = or_(Policy.title.ilike(like), Policy.code.ilike(like), Policy.doc_no.ilike(like))
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)
    if status:
        stmt = stmt.where(Policy.status == status)
        count_stmt = count_stmt.where(Policy.status == status)
    if issuer:
        stmt = stmt.where(Policy.issuer == issuer)
        count_stmt = count_stmt.where(Policy.issuer == issuer)
    if channel:
        stmt = stmt.where(Policy.source_kind == channel)
        count_stmt = count_stmt.where(Policy.source_kind == channel)
    total = db.scalar(count_stmt) or 0
    rows = list(db.scalars(stmt.order_by(Policy.deadline.is_(None), Policy.deadline, Policy.id).limit(limit).offset(offset)).all())
    rule_counts = {
        policy_id: count
        for policy_id, count in db.execute(
            select(Rule.policy_id, func.count()).group_by(Rule.policy_id)
        ).all()
    }
    low_counts = {
        policy_id: count
        for policy_id, count in db.execute(
            select(Rule.policy_id, func.count())
            .where(Rule.confidence < CONFIDENCE_REVIEW_THRESHOLD)
            .group_by(Rule.policy_id)
        ).all()
    }
    items = []
    for row in rows:
        item = serialize(row)
        item["rules_total"] = rule_counts.get(row.id, 0)
        item["low_confidence_total"] = low_counts.get(row.id, 0)
        items.append(item)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def get_policy(db: Session, policy_id: int) -> Policy:
    policy = db.get(Policy, policy_id)
    if policy is None:
        raise not_found("policy", policy_id)
    return policy


def create_policy(db: Session, payload: dict) -> Policy:
    exists = db.scalar(select(Policy).where(Policy.code == payload["code"]))
    if exists is not None:
        raise AppError("CONFLICT", 409, {"code": payload["code"]})
    policy = Policy(
        code=payload["code"],
        title=payload["title"],
        issuer=payload["issuer"],
        doc_no=payload.get("doc_no") or "",
        source_kind=payload.get("source_kind") or "website",
        source_name=payload.get("source_name") or "",
        published_on=parse_date(payload.get("published_on")),
        deadline=parse_date(payload.get("deadline")),
        fund_cap_wan=payload.get("fund_cap_wan"),
        original_text=payload.get("original_text") or "",
        status=payload.get("status") or "draft",
    )
    db.add(policy)
    db.flush()
    return policy


def update_policy(db: Session, policy: Policy, payload: dict) -> Policy:
    for field in ("title", "issuer", "doc_no", "source_kind", "source_name", "fund_cap_wan", "original_text", "status"):
        if field in payload and payload[field] is not None:
            setattr(policy, field, payload[field])
    for field in ("published_on", "deadline"):
        if field in payload:
            setattr(policy, field, parse_date(payload[field]))
    db.flush()
    return policy


def upsert_rules(db: Session, policy: Policy, rules: list[dict]) -> dict:
    """按自然键 (field, op, value) 幂等写入抽取结果。"""
    existing = {f"{item.field}|{item.op}|{item.value}": item for item in rules_of(db, policy.id)}
    created = updated = 0
    keep: set[str] = set()
    for item in rules:
        key = f"{item['field']}|{item['op']}|{item['value']}"
        keep.add(key)
        row = existing.get(key)
        if row is None:
            db.add(
                Rule(
                    policy_id=policy.id,
                    field=item["field"],
                    op=item["op"],
                    value=item["value"],
                    unit=item.get("unit") or "",
                    required=bool(item.get("required", True)),
                    confidence=float(item.get("confidence") or 0.0),
                    evidence_sentence=item.get("evidence") or "",
                )
            )
            created += 1
        else:
            row.unit = item.get("unit") or ""
            row.required = bool(item.get("required", True))
            row.confidence = float(item.get("confidence") or 0.0)
            row.evidence_sentence = item.get("evidence") or ""
            updated += 1
    removed = 0
    for key, row in existing.items():
        if key not in keep:
            db.delete(row)
            removed += 1
    db.flush()
    return {"created": created, "updated": updated, "removed": removed}


def extract_and_store(db: Session, policy: Policy) -> dict:
    extracted = rule_extractor.extract_rules(policy.original_text)
    counters = upsert_rules(db, policy, extracted["rules"])
    if policy.deadline is None and extracted.get("deadline"):
        policy.deadline = parse_date(extracted["deadline"])
    if policy.fund_cap_wan is None and extracted.get("fund_cap_wan"):
        policy.fund_cap_wan = int(extracted["fund_cap_wan"])
    db.flush()
    rules = rules_of(db, policy.id)
    return {
        "policy_id": policy.id,
        "policy_code": policy.code,
        "rules": [serialize_rule(item) for item in rules],
        "created": counters["created"],
        "updated": counters["updated"],
        "removed": counters["removed"],
        "unparsed": extracted["unparsed"],
        "negatives": extracted["negatives"],
        "deadline": extracted["deadline"],
        "fund_cap_wan": extracted["fund_cap_wan"],
        "stats": extracted["stats"],
        "low_confidence": [
            serialize_rule(item) for item in rules if item.confidence < CONFIDENCE_REVIEW_THRESHOLD
        ],
    }


def issuers(db: Session) -> list[str]:
    return [row for (row,) in db.execute(select(Policy.issuer).distinct().order_by(Policy.issuer)).all()]
