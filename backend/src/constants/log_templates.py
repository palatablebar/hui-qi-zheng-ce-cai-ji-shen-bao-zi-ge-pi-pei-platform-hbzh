"""审计动作 -> 中文标签。"""
from __future__ import annotations

ACTIONS: dict[str, str] = {
    "auth.login": "登录",
    "policy.create": "新建政策",
    "policy.update": "修改政策",
    "rule.extract": "抽取申报条件",
    "company.create": "登记企业画像",
    "company.update": "修改企业画像",
    "match.run": "发起资格匹配",
    "match.complete": "匹配完成",
    "match.review": "复核匹配结果",
    "export.matches": "导出申报清单",
    "export.policies": "导出政策台账",
    "http.mutation": "写请求",
}
