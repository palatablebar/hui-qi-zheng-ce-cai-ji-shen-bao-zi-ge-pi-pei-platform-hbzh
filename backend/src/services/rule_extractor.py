"""算法 A｜申报条件抽取：政策原文 → 结构化申报条件。

纯函数模块：不访问数据库、不访问网络、不读取当前时间，同样输入必然同样输出。
支持句式：
  · 「上年度营业收入不超过 20000 万元」        → revenue_wan <= 20000
  · 「营业收入在 1000-5000 万元之间」          → revenue_wan >= 1000 且 <= 5000（两条）
  · 「研发费用占销售收入比例不低于 3%」        → rd_ratio >= 3
  · 「研发投入强度不低于百分之三」             → rd_ratio >= 3（中文数字，低置信度）
  · 「在园区注册」「注册地为苏州工业园区」      → region == 园区
  · 「属于装备制造、电子信息行业」             → industry in 装备制造,电子信息
  · 「已获得高新技术企业认定」                 → qualification in 高新技术企业
  · 「在职员工不少于 30 人」                   → employees >= 30
  · 「有效期至 2026-12-31」                    → deadline <= 2026-12-31
边界：全角数字/全角百分号（３％）、中文数字、否定句「不含…」（不产出条件，进入 negatives）、
      无数字的条件句（进入 unparsed）。
"""
from __future__ import annotations

import re
from datetime import date

from src.constants.enums import CONFIDENCE_REVIEW_THRESHOLD, RuleField, RuleOp

_FULLWIDTH = str.maketrans(
    {
        "０": "0", "１": "1", "２": "2", "３": "3", "４": "4",
        "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
        "％": "%", "．": ".", "－": "-", "～": "~", "，": ",",
    }
)

_CN_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}
_CN_UNITS = {"十": 10, "百": 100, "千": 1000}

# 数值 token：百分数写法必须排在中文数字之前，否则「百分之三」会被「百」抢先匹配
_NUM = r"(?:百分之[一二三四五六七八九十百点]+|\d+(?:\.\d+)?|[一二三四五六七八九十百千万两]+)"
_UNIT_AMOUNT = r"(亿元|万元|亿|万)"
# 比较符：用 lookbehind 排除「不超过」被 GE 的「超过」、「不低于」被 LE 的「低于」抢匹配
_OP_LE = r"(?:不超过|不高于|不得高于|≤|<=|(?<!不)低于|(?<!不)小于|(?<!不)少于)"
_OP_GE = r"(?:不低于|不少于|不得低于|达到|≥|>=|(?<![不得])高于|(?<![不得])超过)"
_OP_ANY = rf"(?:{_OP_LE}|{_OP_GE})"

REVENUE_RANGE = re.compile(
    rf"(?:营业收入|销售收入|营业总收入|营收)[^。；;\n不低高超≥≤]{{0,16}}?"
    rf"(?P<low>{_NUM})\s*(?:万元|万)?\s*(?:-|~|至|到)\s*(?P<high>{_NUM})\s*(?P<unit>{_UNIT_AMOUNT})"
)
REVENUE_LE = re.compile(
    rf"(?:营业收入|销售收入|营业总收入|营收)[^。；;\n]{{0,10}}?(?P<op>{_OP_LE})\s*(?P<num>{_NUM})\s*(?P<unit>{_UNIT_AMOUNT[1:-1]})"
)
REVENUE_GE = re.compile(
    rf"(?:营业收入|销售收入|营业总收入|营收)[^。；;\n]{{0,10}}?(?P<op>{_OP_GE})\s*(?P<num>{_NUM})\s*(?P<unit>{_UNIT_AMOUNT[1:-1]})"
)
RD_RATIO = re.compile(
    rf"研发[^。；;\n，,]{{0,14}}?(?P<op>{_OP_ANY})\s*(?P<num>{_NUM})\s*(?P<pct>[%％])?"
)
EMPLOYEES = re.compile(
    rf"(?:从业人员|职工人数|员工人数|在职员工)[^。；;\n，,]{{0,8}}?(?P<op>{_OP_ANY})\s*(?P<num>{_NUM})\s*人"
)
REGION = re.compile(
    r"(?:在|注册在|注册于|落户在)\s*(?P<place>苏州工业园区|园区|苏州市|姑苏区|吴中区|相城区|昆山市|吴江区|本市)\s*(?:注册|登记|成立|落户)"
)
REGION_ALT = re.compile(
    r"(?:注册地|工商注册地|纳税地)(?:须)?(?:为|在|是)?\s*(?P<place>苏州工业园区|园区|苏州市|姑苏区|吴中区|相城区|昆山市|吴江区|本市)"
)
DEADLINE = re.compile(
    r"(?:有效期至|有效期到|申报截止(?:日期|时间)?(?:为|至)?|受理截止(?:日期)?(?:为|至)?|截止(?:日期|时间)(?:为|至)?)"
    r"\s*(?P<y>\d{4})\s*[-年/.]\s*(?P<m>\d{1,2})\s*[-月/.]\s*(?P<d>\d{1,2})"
)
FUND_CAP = re.compile(
    r"(?:最高|资助|补助|奖励|扶持|补贴)[^。；;\n]{0,12}?(?:不超过|最高|上限|可达|为)\s*(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>亿元|万元|亿|万)"
)
INDUSTRY_HINT = re.compile(r"属于|行业|产业|领域|重点支持")
INDUSTRY_ALIASES: dict[str, tuple[str, ...]] = {
    "装备制造": ("装备制造", "高端装备"),
    "软件信息": ("软件信息", "软件和信息技术服务", "软件与信息服务"),
    "新材料": ("新材料",),
    "生物医药": ("生物医药",),
    "电子信息": ("电子信息",),
    "节能环保": ("节能环保", "节能降碳"),
}
QUALIFICATION_ALIASES: dict[str, tuple[str, ...]] = {
    "专精特新": ("专精特新中小企业", "专精特新“小巨人”企业", "专精特新小巨人企业", "专精特新"),
    "高新技术企业": ("高新技术企业",),
    "软件企业": ("软件和信息服务企业", "软件企业"),
    "科技型中小企业": ("科技型中小企业",),
    "创新型中小企业": ("创新型中小企业",),
    "企业技术中心": ("省级企业技术中心", "企业技术中心"),
}
QUALIFICATION_HINT = re.compile(r"具备|拥有|获得|取得|认定|资质|须为|应为|已是|评为|入库|纳入")
VAGUE_WORDS = ("原则上", "左右", "一般", "大约", "暂定", "参照")
NEGATION_WORDS = ("不含", "不包括", "除外", "不适用", "不纳入")
CONDITION_WORDS = (
    "申报", "条件", "须", "应", "要求", "不低于", "不超过", "以上", "以下",
    "注册", "资质", "认定", "万元", "人",
)
REGION_CANON = {
    "苏州工业园区": "园区",
    "园区": "园区",
    "苏州市": "苏州",
    "本市": "苏州",
}


def normalize_text(text: str) -> str:
    """全角数字 / 全角百分号 / 全角标点 → 半角，便于正则统一处理。"""
    return (text or "").translate(_FULLWIDTH)


def cn_to_number(token: str) -> float | None:
    """中文数字 → 数值（支持 十/百/千/万/亿 与「点」小数）。无法解析返回 None。"""
    token = (token or "").strip()
    if not token:
        return None
    int_part, _, dec_part = token.partition("点")
    if not int_part:
        return None
    total = 0.0
    section = 0.0
    number = 0.0
    seen = False
    for ch in int_part:
        if ch in _CN_DIGITS:
            number = float(_CN_DIGITS[ch])
            seen = True
        elif ch in _CN_UNITS:
            unit = _CN_UNITS[ch]
            section += (number or 1.0) * unit
            number = 0.0
            seen = True
        elif ch == "万":
            section = (section + number) * 10000
            total += section
            section = 0.0
            number = 0.0
            seen = True
        elif ch == "亿":
            section = (section + number) * 100000000
            total += section
            section = 0.0
            number = 0.0
            seen = True
        else:
            return None
    if not seen:
        return None
    value = total + section + number
    if dec_part:
        digits = ""
        for ch in dec_part:
            if ch not in _CN_DIGITS or ch == "两":
                return None
            digits += str(_CN_DIGITS[ch])
        if digits:
            return float(f"{int(value)}.{digits}")
    return float(value)


def parse_number(token: str) -> float | None:
    """ASCII 数字或中文数字 → 数值。"""
    text = normalize_text(str(token or "")).strip().replace(",", "")
    if not text:
        return None
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return float(text)
    return cn_to_number(text)


def parse_percent(token: str) -> float | None:
    """「3」「3%」「３％」「百分之三」 → 3.0。"""
    text = normalize_text(str(token or "")).strip()
    text = text.replace("%", "").replace("百分之", "").strip()
    return parse_number(text)


def parse_amount(token: str, unit: str) -> float | None:
    """金额 → 万元。亿元按 1 亿 = 10000 万元换算。"""
    value = parse_number(token)
    if value is None:
        return None
    if unit in ("亿元", "亿"):
        value *= 10000
    return round(value, 4)


def format_number(value: float) -> str:
    """数值 → 稳定字符串（整数不带小数点）。"""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[。；;\n]", text or "") if part.strip()]


def _is_negative(clause: str) -> bool:
    return any(word in clause for word in NEGATION_WORDS)


def _looks_like_condition(clause: str) -> bool:
    return any(word in clause for word in CONDITION_WORDS)


def _confidence(
    *,
    chinese_numeral: bool = False,
    vague: bool = False,
    fullwidth: bool = False,
    converted: bool = False,
    secondary: bool = False,
    base: float = 0.90,
) -> float:
    value = base
    if fullwidth:
        value -= 0.05
    if converted:
        value -= 0.05
    if chinese_numeral:
        value -= 0.35
    if vague:
        value -= 0.15
    if secondary:
        value -= 0.05
    return round(max(0.35, min(0.96, value)), 2)


def _is_chinese_numeral(token: str) -> bool:
    return bool(re.search(r"[一二三四五六七八九十百千万两]", token or ""))


def _op_canonical(op: str) -> str:
    if op in {">", "≥", ">=", "不低于", "不少于", "不得低于", "高于", "超过", "达到"}:
        return RuleOp.GE.value
    if op in {"<", "≤", "<=", "不超过", "不高于", "不得高于", "低于", "小于", "少于"}:
        return RuleOp.LE.value
    if op in {"属于", "包括", "in"}:
        return RuleOp.IN.value
    return RuleOp.EQ.value


def _rule(
    field: str,
    op: str,
    value: str,
    unit: str,
    confidence: float,
    evidence: str,
    required: bool = True,
) -> dict:
    return {
        "field": field,
        "op": op,
        "value": value,
        "unit": unit,
        "required": required,
        "confidence": confidence,
        "evidence": evidence[:240],
    }


def _clause_confidence_flags(clause: str, raw_token: str, evidence: str = "") -> dict:
    return {
        "chinese_numeral": _is_chinese_numeral(raw_token),
        "vague": any(word in clause for word in VAGUE_WORDS),
        # 全角检测必须看原始句（clause 已归一化为半角）
        "fullwidth": bool(re.search(r"[０-９％]", evidence or clause)),
        "converted": False,
    }


def _extract_revenue(clause: str, evidence: str) -> list[dict]:
    rules: list[dict] = []
    range_match = REVENUE_RANGE.search(clause)
    if range_match:
        low_token, high_token, unit = range_match.group("low"), range_match.group("high"), range_match.group("unit")
        low, high = parse_amount(low_token, unit), parse_amount(high_token, unit)
        if low is not None and high is not None:
            if low > high:
                low, high = high, low
            flags = _clause_confidence_flags(clause, f"{low_token}{high_token}", evidence)
            flags["converted"] = unit in ("亿元", "亿")
            conf = _confidence(**flags, secondary=True)
            rules.append(_rule(RuleField.REVENUE_WAN, RuleOp.GE.value, format_number(low), "万元", conf, evidence))
            rules.append(_rule(RuleField.REVENUE_WAN, RuleOp.LE.value, format_number(high), "万元", conf, evidence))
            return rules
    for pattern in (REVENUE_LE, REVENUE_GE):
        match = pattern.search(clause)
        if not match:
            continue
        token, unit = match.group("num"), match.group("unit")
        amount = parse_amount(token, unit)
        if amount is None:
            continue
        flags = _clause_confidence_flags(clause, token, evidence)
        flags["converted"] = unit in ("亿元", "亿")
        rules.append(
            _rule(
                RuleField.REVENUE_WAN,
                _op_canonical(match.group("op")),
                format_number(amount),
                "万元",
                _confidence(**flags),
                evidence,
            )
        )
        break
    return rules


def _extract_rd_ratio(clause: str, evidence: str) -> list[dict]:
    match = RD_RATIO.search(clause)
    if not match:
        return []
    token = match.group("num")
    has_percent = bool(match.group("pct")) or "%" in token or "百分之" in token
    if not has_percent:
        return []
    value = parse_percent(token)
    if value is None:
        return []
    flags = _clause_confidence_flags(clause, token, evidence)
    return [
        _rule(
            RuleField.RD_RATIO,
            _op_canonical(match.group("op")),
            format_number(value),
            "%",
            _confidence(**flags),
            evidence,
        )
    ]


def _extract_employees(clause: str, evidence: str) -> list[dict]:
    match = EMPLOYEES.search(clause)
    if not match:
        return []
    token = match.group("num")
    value = parse_number(token)
    if value is None:
        return []
    flags = _clause_confidence_flags(clause, token, evidence)
    return [
        _rule(
            RuleField.EMPLOYEES,
            _op_canonical(match.group("op")),
            format_number(value),
            "人",
            _confidence(**flags),
            evidence,
        )
    ]


def _extract_qualification(clause: str, evidence: str) -> list[dict]:
    if not QUALIFICATION_HINT.search(clause):
        return []
    found: list[tuple[int, str]] = []
    for canonical, aliases in QUALIFICATION_ALIASES.items():
        for alias in aliases:
            position = clause.find(alias)
            if position >= 0:
                found.append((position, canonical))
                break
    if not found:
        return []
    found.sort()
    canonical = found[0][1]
    required = not any(word in clause for word in ("优先", "鼓励", "支持"))
    return [
        _rule(
            RuleField.QUALIFICATION,
            RuleOp.IN.value,
            canonical,
            "",
            _confidence(base=0.88, secondary=not required),
            evidence,
            required=required,
        )
    ]


def _extract_region(clause: str, evidence: str) -> list[dict]:
    for pattern in (REGION, REGION_ALT):
        match = pattern.search(clause)
        if not match:
            continue
        place = REGION_CANON.get(match.group("place"), match.group("place"))
        return [_rule(RuleField.REGION, RuleOp.EQ.value, place, "", _confidence(base=0.90), evidence)]
    return []


def _extract_industry(clause: str, evidence: str) -> list[dict]:
    if not INDUSTRY_HINT.search(clause):
        return []
    hits: list[str] = []
    for canonical, aliases in INDUSTRY_ALIASES.items():
        if any(alias in clause for alias in aliases):
            hits.append(canonical)
    if not hits:
        return []
    return [
        _rule(
            RuleField.INDUSTRY,
            RuleOp.IN.value,
            ",".join(hits),
            "",
            _confidence(base=0.85),
            evidence,
        )
    ]


def _extract_deadline(clause: str, evidence: str) -> list[dict]:
    match = DEADLINE.search(clause)
    if not match:
        return []
    try:
        value = date(int(match.group("y")), int(match.group("m")), int(match.group("d")))
    except ValueError:
        return []
    return [
        _rule(
            RuleField.DEADLINE,
            RuleOp.LE.value,
            value.isoformat(),
            "date",
            _confidence(base=0.92),
            evidence,
        )
    ]


def _extract_from_clause(clause: str, evidence: str) -> list[dict]:
    rules: list[dict] = []
    rules.extend(_extract_revenue(clause, evidence))
    rules.extend(_extract_rd_ratio(clause, evidence))
    rules.extend(_extract_employees(clause, evidence))
    rules.extend(_extract_qualification(clause, evidence))
    rules.extend(_extract_region(clause, evidence))
    rules.extend(_extract_industry(clause, evidence))
    rules.extend(_extract_deadline(clause, evidence))
    return rules


def _dedupe(rules: list[dict]) -> list[dict]:
    seen: set[tuple[str, str, str]] = set()
    ordered: list[dict] = []
    for rule in rules:
        key = (rule["field"], rule["op"], rule["value"])
        if key in seen:
            continue
        seen.add(key)
        ordered.append(rule)
    return ordered


def _extract_fund(normalized: str) -> int | None:
    match = FUND_CAP.search(normalized)
    if not match:
        return None
    amount = parse_amount(match.group("num"), match.group("unit"))
    if amount is None:
        return None
    return int(round(amount))


def extract_rules(text: str) -> dict:
    """政策原文 → {rules, unparsed, negatives, deadline, fund_cap_wan, stats}。"""
    raw = text or ""
    normalized = normalize_text(raw)
    raw_clauses = _split_sentences(raw)
    clauses = _split_sentences(normalized)
    if len(clauses) != len(raw_clauses):  # 归一化不应改变句子切分，异常时退回归一化文本
        raw_clauses = clauses

    rules: list[dict] = []
    unparsed: list[str] = []
    negatives: list[str] = []
    for index, clause in enumerate(clauses):
        evidence = (raw_clauses[index] if index < len(raw_clauses) else clause).strip()
        if not evidence:
            continue
        if _is_negative(evidence):
            negatives.append(evidence)
            continue
        found = _extract_from_clause(clause, evidence)
        if found:
            rules.extend(found)
        elif _looks_like_condition(evidence):
            unparsed.append(evidence)

    rules = _dedupe(rules)
    deadline = next((item["value"] for item in rules if item["field"] == RuleField.DEADLINE), None)
    low_confidence = [item for item in rules if item["confidence"] < CONFIDENCE_REVIEW_THRESHOLD]
    return {
        "rules": rules,
        "unparsed": unparsed,
        "negatives": negatives,
        "deadline": deadline,
        "fund_cap_wan": _extract_fund(normalized),
        "stats": {
            "clauses": len(clauses),
            "rules": len(rules),
            "low_confidence": len(low_confidence),
            "unparsed": len(unparsed),
            "negatives": len(negatives),
        },
    }
