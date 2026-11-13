"""算法 B｜申报资格匹配：企业画像 × 政策条件 → 得分 / 缺口 / 优先级。

纯函数模块：不访问数据库、不访问网络；当前日期由调用方传入，保证可复现。

口径（README §10 同步）：
  硬条件：industry / region / qualification / deadline 为布尔判定，全部通过才 hard_pass。
  软条件：revenue_wan / rd_ratio / employees 按余量 margin=(actual-threshold)/threshold（满足取正）。
          单条软条件得分：满足 → 0.6+0.4*min(1, margin)；不满足 → max(0, 0.6*(1+margin))。
  总分：score = 60*hard_ratio + 30*soft_score + 10*deadline_score（0-100）。
  截止分：已过期 0；≤7 天 1.0；≤15 天 0.8；≤30 天 0.6；≤60 天 0.4；其余 0.2；无截止日 0.2。
  优先级：P0 = 得分 ≥70 且硬条件全过且 0 ≤ 距截止 ≤7 天；P1 = 得分 ≥50 且硬条件全过；其余 P2。
  缺失字段：缺口写「缺数据」，不计通过（硬条件缺失 → hard_pass=False）。
"""
from __future__ import annotations

from datetime import date

from src.constants.enums import (
    HARD_FIELDS,
    P0_DEADLINE_DAYS,
    P0_SCORE_THRESHOLD,
    Priority,
    RuleField,
)

SUZHOU_DISTRICTS = ("园区", "吴中区", "姑苏区", "相城区", "昆山市", "吴江区")

SHORT_LABELS: dict[str, str] = {
    RuleField.REVENUE_WAN.value: "营业收入",
    RuleField.RD_RATIO.value: "研发占比",
    RuleField.EMPLOYEES.value: "员工人数",
    RuleField.INDUSTRY.value: "所属行业",
    RuleField.REGION.value: "注册地",
    RuleField.QUALIFICATION.value: "企业资质",
    RuleField.DEADLINE.value: "申报截止",
}

UNIT_TEXT: dict[str, str] = {
    RuleField.REVENUE_WAN.value: "万元",
    RuleField.RD_RATIO.value: "%",
    RuleField.EMPLOYEES.value: "人",
}


def as_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def days_left(deadline: object, today: date) -> int | None:
    parsed = as_date(deadline)
    if parsed is None:
        return None
    return (parsed - today).days


def deadline_component(days: int | None) -> float:
    if days is None:
        return 0.2
    if days < 0:
        return 0.0
    if days <= 7:
        return 1.0
    if days <= 15:
        return 0.8
    if days <= 30:
        return 0.6
    if days <= 60:
        return 0.4
    return 0.2


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}"


def _gap_text(item: dict) -> str:
    field = item["field"]
    label = SHORT_LABELS.get(field, field)
    unit = UNIT_TEXT.get(field, "")
    actual = item.get("actual")
    expected = item.get("expected")
    if item.get("missing") or actual is None:
        return f"{label}：缺数据"
    if field == RuleField.DEADLINE.value:
        return f"申报截止 {expected} 已过期 {abs(int(item.get('days') or 0))} 天"
    if field == RuleField.REGION.value:
        return f"注册地「{actual}」≠「{expected}」"
    if field == RuleField.INDUSTRY.value:
        return f"所属行业「{actual}」不在支持范围（{expected}）"
    if field == RuleField.QUALIFICATION.value:
        return f"缺少资质「{expected}」"
    try:
        actual_value = float(actual)
        expected_value = float(expected)
    except (TypeError, ValueError):
        return f"{label} 不满足（实际 {actual} / 要求 {expected}）"
    symbol = "<" if actual_value < expected_value else ">"
    diff = abs(actual_value - expected_value)
    suffix = "pt" if field == RuleField.RD_RATIO.value else unit
    return (
        f"{label} {_format_number(actual_value)}{unit} {symbol} "
        f"{_format_number(expected_value)}{unit}（差 {_format_number(diff)}{suffix}）"
    )


def _numeric_result(company: dict, rule: dict) -> dict:
    field = rule["field"]
    op = rule.get("op") or ">="
    expected = float(rule["value"])
    actual = company.get(field)
    item: dict = {
        "field": field,
        "label": SHORT_LABELS.get(field, field),
        "op": op,
        "expected": rule["value"],
        "script": rule.get("evidence_sentence") or rule.get("evidence") or "",
        "required": bool(rule.get("required", True)),
        "actual": actual,
        "missing": actual is None,
        "hard": False,
        "pass": None,
        "score": 0.0,
        "margin": None,
    }
    if actual is None:
        return item
    actual_value = float(actual)
    if op == "<=":
        satisfied = actual_value <= expected
        margin = (expected - actual_value) / expected if expected else 0.0
    else:
        satisfied = actual_value >= expected
        margin = (actual_value - expected) / expected if expected else 0.0
    if satisfied:
        per_rule = 0.6 + 0.4 * min(1.0, margin)
    else:
        per_rule = max(0.0, 0.6 * (1.0 + margin))
    item.update(
        {
            "pass": satisfied,
            "margin": round(margin, 4),
            "score": round(per_rule, 4),
        }
    )
    return item


def _industry_result(company: dict, rule: dict) -> dict:
    expected_values = [part for part in str(rule["value"]).split(",") if part]
    actual = company.get("industry")
    passed = None if not actual else actual in expected_values
    return {
        "field": RuleField.INDUSTRY.value,
        "label": SHORT_LABELS[RuleField.INDUSTRY.value],
        "op": "in",
        "expected": ",".join(expected_values),
        "script": rule.get("evidence_sentence") or rule.get("evidence") or "",
        "required": bool(rule.get("required", True)),
        "actual": actual,
        "missing": not actual,
        "hard": True,
        "pass": passed,
        "score": 1.0 if passed else 0.0,
    }


def _region_result(company: dict, rule: dict) -> dict:
    expected = str(rule["value"])
    actual = company.get("district")
    if not actual:
        passed = None
    elif expected == "苏州":
        passed = actual in SUZHOU_DISTRICTS
    else:
        passed = actual == expected
    return {
        "field": RuleField.REGION.value,
        "label": SHORT_LABELS[RuleField.REGION.value],
        "op": "==",
        "expected": expected,
        "script": rule.get("evidence_sentence") or rule.get("evidence") or "",
        "required": bool(rule.get("required", True)),
        "actual": actual,
        "missing": not actual,
        "hard": True,
        "pass": passed,
        "score": 1.0 if passed else 0.0,
    }


def _qualification_result(company: dict, rule: dict) -> dict:
    expected = str(rule["value"])
    owned = company.get("qualifications") or []
    passed = expected in owned
    return {
        "field": RuleField.QUALIFICATION.value,
        "label": SHORT_LABELS[RuleField.QUALIFICATION.value],
        "op": "in",
        "expected": expected,
        "script": rule.get("evidence_sentence") or rule.get("evidence") or "",
        "required": bool(rule.get("required", True)),
        "actual": "、".join(owned),
        "missing": False,
        "hard": True,
        "pass": passed,
        "score": 1.0 if passed else 0.0,
    }


def _deadline_result(policy: dict, rule: dict, today: date) -> dict:
    expected = as_date(rule.get("value")) or as_date(policy.get("deadline"))
    remaining = (expected - today).days if expected else None
    passed = None if remaining is None else remaining >= 0
    return {
        "field": RuleField.DEADLINE.value,
        "label": SHORT_LABELS[RuleField.DEADLINE.value],
        "op": "<=",
        "expected": expected.isoformat() if expected else "",
        "script": rule.get("evidence_sentence") or rule.get("evidence") or "",
        "required": bool(rule.get("required", True)),
        "actual": remaining,
        "days": remaining,
        "missing": remaining is None,
        "hard": True,
        "pass": passed,
        "score": 1.0 if passed else 0.0,
    }


def evaluate(company: dict, rules: list[dict], policy: dict, today: date) -> dict:
    """评估一家企业对一个政策的匹配结果（确定性）。"""
    hard_items: list[dict] = []
    soft_items: list[dict] = []

    for rule in rules:
        field = rule.get("field")
        if field == RuleField.DEADLINE.value:
            hard_items.append(_deadline_result(policy, rule, today))
        elif field == RuleField.INDUSTRY.value:
            hard_items.append(_industry_result(company, rule))
        elif field == RuleField.REGION.value:
            hard_items.append(_region_result(company, rule))
        elif field == RuleField.QUALIFICATION.value:
            hard_items.append(_qualification_result(company, rule))
        elif field in UNIT_TEXT:
            soft_items.append(_numeric_result(company, rule))

    required_hard = [item for item in hard_items if item["required"]]
    passed_hard = [item for item in required_hard if item["pass"] is True]
    hard_ratio = (len(passed_hard) / len(required_hard)) if required_hard else 1.0
    hard_pass = all(item["pass"] is True for item in required_hard)

    required_soft = [item for item in soft_items if item["required"]]
    soft_score = (
        sum(float(item.get("score") or 0.0) for item in required_soft) / len(required_soft)
        if required_soft
        else 1.0
    )

    remaining = days_left(policy.get("deadline"), today)
    deadline_value = deadline_component(remaining)
    score = round(60.0 * hard_ratio + 30.0 * soft_score + 10.0 * deadline_value, 1)

    if (
        score >= P0_SCORE_THRESHOLD
        and hard_pass
        and remaining is not None
        and 0 <= remaining <= P0_DEADLINE_DAYS
    ):
        priority = Priority.P0.value
    elif score >= 50 and hard_pass:
        priority = Priority.P1.value
    else:
        priority = Priority.P2.value

    gaps: list[str] = []
    for item in hard_items + soft_items:
        if item["required"] and item["pass"] is not True:
            text = _gap_text(item)
            if text not in gaps:
                gaps.append(text)

    return {
        "score": score,
        "hard_pass": hard_pass,
        "hard_ratio": round(hard_ratio, 4),
        "soft_score": round(soft_score, 4),
        "deadline_score": deadline_value,
        "deadline_days": remaining,
        "priority": priority,
        "gaps": gaps,
        "payload": {
            "hard": hard_items,
            "soft": soft_items,
            "score_parts": {
                "hard_ratio": round(hard_ratio, 4),
                "soft_score": round(soft_score, 4),
                "deadline_score": deadline_value,
            },
            "policy_code": policy.get("code"),
            "company_code": company.get("code"),
        },
    }
