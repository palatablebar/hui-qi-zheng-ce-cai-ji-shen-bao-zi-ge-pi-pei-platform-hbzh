"""画像更正服务单测：值规整、编码、字段映射、快照构建（不依赖数据库连接）。"""
from __future__ import annotations

import pytest

from src.constants.enums import PROFILE_FIELDS, RuleField
from src.models.company import Company
from src.services import correction_service
from src.utils.errors import AppError


def test_parse_numeric_values():
    assert correction_service._parse_new_value("revenue_wan", "9180") == 9180.0
    assert correction_service._parse_new_value("rd_ratio", 3.4) == 3.4
    assert correction_service._parse_new_value("employees", "240") == 240


def test_parse_qualification_accepts_string_and_list():
    assert correction_service._parse_new_value(
        "qualification", "高新技术企业、专精特新"
    ) == ["高新技术企业", "专精特新"]
    assert correction_service._parse_new_value(
        "qualification", ["软件企业", "企业技术中心"]
    ) == ["软件企业", "企业技术中心"]


def test_parse_rejects_empty_qualification_and_blank():
    with pytest.raises(AppError):
        correction_service._parse_new_value("qualification", "")
    with pytest.raises(AppError):
        correction_service._parse_new_value("rd_ratio", None)


def test_parse_text_field_trims():
    assert correction_service._parse_new_value("industry", "  软件信息 ") == "软件信息"


def test_encode_handles_none_and_list():
    assert correction_service._encode(None) is None
    assert correction_service._encode(["a", "b"]) == "a、b"
    assert correction_service._encode(3.4) == "3.4"


def test_field_to_column_covers_all_profile_fields():
    for field in PROFILE_FIELDS:
        assert field in correction_service.FIELD_TO_COLUMN
    assert correction_service.FIELD_TO_COLUMN[RuleField.REGION.value] == "district"


def test_build_snapshot_freezes_current_profile():
    company = Company(
        code="C0001",
        name="苏州锐驰精密机械有限公司",
        industry="装备制造",
        district="园区",
        revenue_wan=8600.0,
        rd_ratio=2.8,
        employees=240,
        qualifications=["高新技术企业"],
    )
    snapshot = correction_service.build_snapshot(company)
    assert snapshot == {
        "code": "C0001",
        "name": "苏州锐驰精密机械有限公司",
        "industry": "装备制造",
        "district": "园区",
        "revenue_wan": 8600.0,
        "rd_ratio": 2.8,
        "employees": 240,
        "qualifications": ["高新技术企业"],
    }
    # 快照是独立副本，后续修改原对象不影响已固化快照
    company.rd_ratio = 3.4
    company.qualifications.append("专精特新")
    assert snapshot["rd_ratio"] == 2.8
    assert snapshot["qualifications"] == ["高新技术企业"]
