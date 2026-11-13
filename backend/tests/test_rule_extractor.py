"""算法 A（条件抽取）单测：正常句式 + 边界（全角/中文数字/否定/无法解析）+ 确定性。"""
from __future__ import annotations

from src.constants.enums import CONFIDENCE_REVIEW_THRESHOLD
from src.services.rule_extractor import extract_rules, parse_number, parse_percent


def _first(text: str) -> dict:
    rules = extract_rules(text)["rules"]
    assert rules, f"未抽取到条件：{text}"
    return rules[0]


def test_revenue_upper_bound():
    rule = _first("上年度营业收入不超过 20000 万元。")
    assert rule["field"] == "revenue_wan"
    assert rule["op"] == "<="
    assert rule["value"] == "20000"
    assert rule["unit"] == "万元"
    assert rule["confidence"] == 0.9


def test_revenue_range_gives_two_rules():
    rules = extract_rules("上年度营业收入在 1000-5000 万元之间。")["rules"]
    assert [(item["op"], item["value"]) for item in rules] == [(">=", "1000"), ("<=", "5000")]


def test_fullwidth_percent_normalized():
    rule = _first("研发费用占销售收入比例不低于 ３％。")
    assert rule["field"] == "rd_ratio"
    assert rule["op"] == ">="
    assert rule["value"] == "3"
    assert rule["confidence"] == 0.85


def test_chinese_numeral_marks_low_confidence():
    rule = _first("研发投入强度不低于百分之三。")
    assert rule["value"] == "3"
    assert rule["confidence"] < CONFIDENCE_REVIEW_THRESHOLD


def test_region_and_industry_rules():
    result = extract_rules("支持属于装备制造、电子信息行业的企业。申报企业须在园区注册。")
    fields = {item["field"]: item for item in result["rules"]}
    assert fields["industry"]["value"] == "装备制造,电子信息"
    assert fields["industry"]["op"] == "in"
    assert fields["region"]["value"] == "园区"


def test_qualification_needs_hint_word():
    with_hint = extract_rules("已获得高新技术企业认定的企业可申报。")["rules"]
    assert with_hint[0]["field"] == "qualification"
    assert with_hint[0]["value"] == "高新技术企业"
    without_hint = extract_rules("本公司主要服务高新技术企业客户。")["rules"]
    assert without_hint == []


def test_negation_sentence_skipped():
    result = extract_rules("不含研发费用不超过 100 万元的贸易型企业。")
    assert result["rules"] == []
    assert len(result["negatives"]) == 1


def test_unparsed_condition_collected():
    result = extract_rules("申报企业须提供近三年审计报告。")
    assert result["rules"] == []
    assert len(result["unparsed"]) == 1


def test_deadline_rule_and_candidate():
    result = extract_rules("本批次受理截止日期为 2026-11-18。")
    rule = result["rules"][0]
    assert rule["field"] == "deadline"
    assert rule["value"] == "2026-11-18"
    assert result["deadline"] == "2026-11-18"


def test_number_parsing_helpers():
    assert parse_number("一千二百") == 1200
    assert parse_number("2.5") == 2.5
    assert parse_percent("百分之八") == 8
    assert parse_number("不是数字") is None


def test_same_input_same_output():
    text = "在园区注册且已获得专精特新中小企业认定的企业可申报。上年度营业收入不超过 10000 万元。"
    assert extract_rules(text) == extract_rules(text)
