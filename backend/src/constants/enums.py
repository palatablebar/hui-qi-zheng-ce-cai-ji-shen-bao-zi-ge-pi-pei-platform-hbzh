"""共享枚举（后端唯一定义处）。前端副本见 frontend/site/js/config.js。

README「共享枚举出现位置」一节列出全部出现点，改动需两侧同步。
"""
from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class PolicyStatus(StrEnum):
    """政策台账状态：草稿 / 申报中 / 已过期。"""

    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"


POLICY_STATUS_LABELS: dict[str, str] = {
    PolicyStatus.DRAFT.value: "草稿",
    PolicyStatus.ACTIVE.value: "申报中",
    PolicyStatus.EXPIRED.value: "已过期",
}

POLICY_STATUS_ORDER: list[str] = [
    PolicyStatus.ACTIVE.value,
    PolicyStatus.DRAFT.value,
    PolicyStatus.EXPIRED.value,
]


class ChannelKind(StrEnum):
    """采集渠道类型：政府门户 / 公众号 / 公报 / 转发通知。"""

    WEBSITE = "website"
    WECHAT = "wechat"
    GAZETTE = "gazette"
    FORWARD = "forward"


CHANNEL_KIND_LABELS: dict[str, str] = {
    ChannelKind.WEBSITE.value: "政府门户",
    ChannelKind.WECHAT.value: "公众号",
    ChannelKind.GAZETTE.value: "政策公报",
    ChannelKind.FORWARD.value: "转发通知",
}


class RuleField(StrEnum):
    """申报条件字段口径。"""

    INDUSTRY = "industry"
    REGION = "region"
    REVENUE_WAN = "revenue_wan"
    RD_RATIO = "rd_ratio"
    EMPLOYEES = "employees"
    QUALIFICATION = "qualification"
    DEADLINE = "deadline"


RULE_FIELD_LABELS: dict[str, str] = {
    RuleField.INDUSTRY.value: "所属行业",
    RuleField.REGION.value: "注册地",
    RuleField.REVENUE_WAN.value: "营业收入(万元)",
    RuleField.RD_RATIO.value: "研发占比(%)",
    RuleField.EMPLOYEES.value: "员工人数(人)",
    RuleField.QUALIFICATION.value: "企业资质",
    RuleField.DEADLINE.value: "申报截止",
}

RULE_FIELD_ORDER: list[str] = [
    RuleField.INDUSTRY.value,
    RuleField.REGION.value,
    RuleField.REVENUE_WAN.value,
    RuleField.RD_RATIO.value,
    RuleField.EMPLOYEES.value,
    RuleField.QUALIFICATION.value,
    RuleField.DEADLINE.value,
]

HARD_FIELDS: tuple[str, ...] = (
    RuleField.INDUSTRY.value,
    RuleField.REGION.value,
    RuleField.QUALIFICATION.value,
    RuleField.DEADLINE.value,
)

SOFT_FIELDS: tuple[str, ...] = (
    RuleField.REVENUE_WAN.value,
    RuleField.RD_RATIO.value,
    RuleField.EMPLOYEES.value,
)


class RuleOp(StrEnum):
    LE = "<="
    GE = ">="
    EQ = "=="
    IN = "in"


RULE_OP_LABELS: dict[str, str] = {
    RuleOp.LE.value: "不超过",
    RuleOp.GE.value: "不低于",
    RuleOp.EQ.value: "等于",
    RuleOp.IN.value: "属于",
}


class Priority(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


PRIORITY_LABELS: dict[str, str] = {
    Priority.P0.value: "P0 优先",
    Priority.P1.value: "P1 跟进",
    Priority.P2.value: "P2 观察",
}

PRIORITY_ORDER: list[str] = [Priority.P0.value, Priority.P1.value, Priority.P2.value]


class ReviewStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"


REVIEW_STATUS_LABELS: dict[str, str] = {
    ReviewStatus.PENDING.value: "待复核",
    ReviewStatus.CONFIRMED.value: "已确认",
    ReviewStatus.DISMISSED.value: "已驳回",
}

REVIEW_STATUS_ORDER: list[str] = [
    ReviewStatus.PENDING.value,
    ReviewStatus.CONFIRMED.value,
    ReviewStatus.DISMISSED.value,
]


class MatchRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


MATCH_RUN_STATUS_LABELS: dict[str, str] = {
    MatchRunStatus.QUEUED.value: "排队中",
    MatchRunStatus.RUNNING.value: "执行中",
    MatchRunStatus.SUCCESS.value: "成功",
    MatchRunStatus.PARTIAL.value: "部分成功",
    MatchRunStatus.FAILED.value: "失败",
}


class TriggerKind(StrEnum):
    MANUAL = "manual"
    SCHEDULE = "schedule"
    SEED = "seed"


TRIGGER_LABELS: dict[str, str] = {
    TriggerKind.MANUAL.value: "手动",
    TriggerKind.SCHEDULE.value: "定时",
    TriggerKind.SEED.value: "初始化",
}


class CorrectionSource(StrEnum):
    """画像更正来源：工商回传 / 客户补录 / 年报核对 / 人工修正。"""

    REGISTRY = "registry"
    CUSTOMER = "customer"
    ANNUAL = "annual"
    MANUAL = "manual"


CORRECTION_SOURCE_LABELS: dict[str, str] = {
    CorrectionSource.REGISTRY.value: "工商回传",
    CorrectionSource.CUSTOMER.value: "客户补录",
    CorrectionSource.ANNUAL.value: "年报核对",
    CorrectionSource.MANUAL.value: "人工修正",
}

CORRECTION_SOURCE_ORDER: list[str] = [
    CorrectionSource.REGISTRY.value,
    CorrectionSource.CUSTOMER.value,
    CorrectionSource.ANNUAL.value,
    CorrectionSource.MANUAL.value,
]

# 来源可信度权重（0-1）：决定待核验提示与默认排序，不替代人工核验
CORRECTION_SOURCE_TRUST: dict[str, float] = {
    CorrectionSource.REGISTRY.value: 0.95,
    CorrectionSource.ANNUAL.value: 0.9,
    CorrectionSource.CUSTOMER.value: 0.7,
    CorrectionSource.MANUAL.value: 0.8,
}


class CorrectionStatus(StrEnum):
    """更正核验状态：待核验 / 已核验（值已入画像）/ 已驳回（不入画像）。"""

    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


CORRECTION_STATUS_LABELS: dict[str, str] = {
    CorrectionStatus.PENDING.value: "待核验",
    CorrectionStatus.VERIFIED.value: "已核验",
    CorrectionStatus.REJECTED.value: "已驳回",
}

CORRECTION_STATUS_ORDER: list[str] = [
    CorrectionStatus.PENDING.value,
    CorrectionStatus.VERIFIED.value,
    CorrectionStatus.REJECTED.value,
]

# 可被更正留痕的画像字段（口径与 RULE_FIELD 对齐，仅画像自有指标）
PROFILE_FIELDS: tuple[str, ...] = (
    RuleField.INDUSTRY.value,
    RuleField.REGION.value,
    RuleField.REVENUE_WAN.value,
    RuleField.RD_RATIO.value,
    RuleField.EMPLOYEES.value,
    RuleField.QUALIFICATION.value,
)

# 置信度低于该值的条件进入「待人工确认」
CONFIDENCE_REVIEW_THRESHOLD = 0.6
# P0 判定：得分阈值 + 距截止日天数
P0_SCORE_THRESHOLD = 70
P0_DEADLINE_DAYS = 7
