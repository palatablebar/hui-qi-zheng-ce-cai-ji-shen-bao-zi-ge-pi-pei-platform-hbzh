"""角色 -> 权限点映射。README 与前端 site/js/config.js 同步。

角色键固定为 admin / analyst / viewer，各项目的展示名与职责不同。
本项目：平台运营（政策服务组组长）/ 政策专员 / 客户经理只读。
"""
from __future__ import annotations

from src.constants.enums import Role

ROLE_LABELS: dict[str, str] = {
    Role.ADMIN.value: "政策运营",
    Role.ANALYST.value: "政策专员",
    Role.VIEWER.value: "客户经理（只读）",
}

ROLE_DUTIES: dict[str, str] = {
    Role.ADMIN.value: "维护政策台账与企业画像、抽取条件、跑匹配、导出申报清单、查看审计",
    Role.ANALYST.value: "维护企业画像、抽取条件、跑匹配、复核匹配结果",
    Role.VIEWER.value: "只读政策与匹配结果，不显示企业联系人电话，不能跑匹配或复核",
}

PERMISSIONS: dict[str, set[str]] = {
    Role.ADMIN.value: {
        "policy:read", "policy:write",
        "company:read", "company:write", "company:contact",
        "rule:read", "rule:extract",
        "match:read", "match:run", "match:review",
        "export:read", "audit:read", "overview:read",
    },
    Role.ANALYST.value: {
        "policy:read",
        "company:read", "company:write", "company:contact",
        "rule:read", "rule:extract",
        "match:read", "match:run", "match:review",
        "export:read", "overview:read",
    },
    Role.VIEWER.value: {
        "policy:read", "company:read", "rule:read", "match:read", "overview:read",
    },
}

POLICY_WRITE_ROLES = (Role.ADMIN.value,)
COMPANY_WRITE_ROLES = (Role.ADMIN.value, Role.ANALYST.value)
EXTRACT_ROLES = (Role.ADMIN.value, Role.ANALYST.value)
RUN_CREATE_ROLES = (Role.ADMIN.value, Role.ANALYST.value)
REVIEW_ROLES = (Role.ADMIN.value, Role.ANALYST.value)
EXPORT_ROLES = (Role.ADMIN.value, Role.ANALYST.value)
AUDIT_ROLES = (Role.ADMIN.value,)
READ_ROLES = (Role.ADMIN.value, Role.ANALYST.value, Role.VIEWER.value)
CONTACT_ROLES = (Role.ADMIN.value, Role.ANALYST.value)


def has_permission(role: str, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())


def can_see_contact(role: str) -> bool:
    return role in CONTACT_ROLES
