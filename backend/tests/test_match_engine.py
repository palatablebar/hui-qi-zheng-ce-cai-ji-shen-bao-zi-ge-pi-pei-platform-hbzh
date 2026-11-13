"""算法 B（资格匹配）单测：硬条件、软条件余量、缺口文案、优先级、缺失数据、确定性。"""
from __future__ import annotations

from datetime import date

from src.services.match_engine import deadline_component, evaluate

TODAY = date(2026, 11, 13)

COMPANY = {
    "code": "C0001",
    "industry": "装备制造",
    "district": "园区",
    "revenue_wan": 8600.0,
    "rd_ratio": 2.8,
    "employees": 240,
    "qualifications": ["高新技术企业", "科技型中小企业"],
}

REGION = {"field": "region", "op": "==", "value": "园区", "required": True}
REVENUE = {"field": "revenue_wan", "op": "<=", "value": "20000", "required": True}
RD = {"field": "rd_ratio", "op": ">=", "value": "3", "required": True}
QUALI = {"field": "qualification", "op": "in", "value": "专精特新", "required": True}
INDUSTRY = {"field": "industry", "op": "in", "value": "装备制造,软件信息", "required": True}

POLICY = {"code": "P2026-ZJTX", "title": "专精特新培育资助", "deadline": "2026-11-21"}


def test_score_and_gap_on_soft_shortfall():
    result = evaluate(COMPANY, [REGION, REVENUE, RD], POLICY, TODAY)
    assert result["hard_pass"] is True
    assert result["score"] == 88.8
    assert result["gaps"] == ["研发占比 2.8% < 3%（差 0.2pt）"]
    assert result["priority"] == "P1"


def test_p0_requires_deadline_within_seven_days():
    near = {"code": "P2026-ZJTX", "title": "专精特新培育资助", "deadline": "2026-11-19"}
    result = evaluate(COMPANY, [REGION, REVENUE, RD], near, TODAY)
    assert result["priority"] == "P0"
    assert result["deadline_days"] == 6


def test_hard_fail_missing_qualification():
    result = evaluate(COMPANY, [REGION, QUALI], POLICY, TODAY)
    assert result["hard_pass"] is False
    assert "缺少资质「专精特新」" in result["gaps"]
    assert result["priority"] == "P2"


def test_hard_fail_industry_gap_text():
    company = dict(COMPANY, industry="新材料")
    result = evaluate(company, [INDUSTRY], POLICY, TODAY)
    assert result["hard_pass"] is False
    assert result["gaps"] == ["所属行业「新材料」不在支持范围（装备制造,软件信息）"]


def test_suzhou_region_covers_all_districts():
    company = dict(COMPANY, district="昆山市")
    result = evaluate(company, [{"field": "region", "op": "==", "value": "苏州", "required": True}], POLICY, TODAY)
    assert result["hard_pass"] is True


def test_missing_field_is_gap_not_pass():
    company = {key: value for key, value in COMPANY.items() if key != "revenue_wan"}
    result = evaluate(company, [REGION, REVENUE], POLICY, TODAY)
    assert "营业收入：缺数据" in result["gaps"]
    assert result["payload"]["soft"][0]["pass"] is None


def test_expired_deadline_fails_hard():
    expired = {"code": "P2026-JNJB", "title": "节能降碳", "deadline": "2026-11-12"}
    rule = {"field": "deadline", "op": "<=", "value": "2026-11-12", "required": True}
    result = evaluate(COMPANY, [REGION, rule], expired, TODAY)
    assert result["hard_pass"] is False
    assert result["gaps"] == ["申报截止 2026-11-12 已过期 1 天"]


def test_deadline_component_bands():
    assert deadline_component(None) == 0.2
    assert deadline_component(-1) == 0.0
    assert deadline_component(7) == 1.0
    assert deadline_component(8) == 0.8
    assert deadline_component(31) == 0.4
    assert deadline_component(120) == 0.2


def test_score_is_deterministic():
    first = evaluate(COMPANY, [REGION, REVENUE, RD], POLICY, TODAY)
    second = evaluate(COMPANY, [REGION, REVENUE, RD], POLICY, TODAY)
    assert first == second
