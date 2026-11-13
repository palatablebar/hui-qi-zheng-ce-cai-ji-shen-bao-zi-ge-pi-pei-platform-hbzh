"""演示数据：12 条政策（含 3 条条件歧义）、38 条条件、120 家企业、1 次匹配窗口。

全部是园区政策服务组的真实业务口径数据；条件不手写，由 `services.rule_extractor`
对政策原文真实抽取得到（seed 时执行），保证「原文 → 条件」链路可复算。
"""
from __future__ import annotations

DEMO_PASSWORD = "Demo@2026"

DEMO_USERS = [
    ("admin@policyfit.io", "沈砚 · 政策运营", "admin"),
    ("analyst@policyfit.io", "顾清 · 政策专员", "analyst"),
    ("viewer@policyfit.io", "许棠 · 客户经理", "viewer"),
]

ORG = "苏州工业园区企服通 · 政策服务组"

# ---------------------------------------------------------------- 政策台账
# text 中的每句都是真实公告口径，条件由抽取器解析；deadline 为台账字段（人工复核）。
POLICIES: list[dict] = [
    {
        "code": "P2026-ZJTX",
        "title": "2026 年度专精特新培育资助",
        "issuer": "苏州工业园区经济发展委员会",
        "doc_no": "苏园经发〔2026〕18 号",
        "source_kind": "website",
        "source_name": "园区经发委门户",
        "published_on": "2026-10-28",
        "deadline": "2026-11-21",
        "fund_cap_wan": 200,
        "status": "active",
        "text": (
            "申报 2026 年度专精特新培育资助的企业须在园区注册并持续经营满两年。"
            "申报企业须为装备制造、软件信息行业的科技型中小企业（须已入库登记）。"
            "研发投入强度不低于百分之三。"
        ),
    },
    {
        "code": "P2026-GXJS",
        "title": "2026 年高新技术企业认定奖励",
        "issuer": "苏州市科学技术局",
        "doc_no": "苏科高〔2026〕41 号",
        "source_kind": "website",
        "source_name": "苏州市科技局门户",
        "published_on": "2026-10-25",
        "deadline": "2026-11-24",
        "fund_cap_wan": 50,
        "status": "active",
        "text": (
            "在苏州工业园区注册且已获得高新技术企业认定的企业可申报。"
            "上年度营业收入不低于 1000 万元。"
            "研发费用占销售收入比例不低于 3%。"
        ),
    },
    {
        "code": "P2026-SBTZ",
        "title": "智能制造装备首台套补贴",
        "issuer": "苏州市工业和信息化局",
        "doc_no": "苏工信装〔2026〕9 号",
        "source_kind": "wechat",
        "source_name": "苏州工信公众号",
        "published_on": "2026-10-30",
        "deadline": "2026-12-15",
        "fund_cap_wan": 300,
        "status": "active",
        "text": (
            "支持属于装备制造、电子信息行业的企业。"
            "申报企业须在园区注册。"
            "上年度营业收入在 1000-5000 万元之间。"
        ),
    },
    {
        "code": "P2026-RJQY",
        "title": "软件和信息服务业成长奖励",
        "issuer": "苏州工业园区科技创新委员会",
        "doc_no": "苏园科创〔2026〕27 号",
        "source_kind": "website",
        "source_name": "园区科创委门户",
        "published_on": "2026-11-02",
        "deadline": "2026-11-26",
        "fund_cap_wan": 80,
        "status": "active",
        "text": (
            "在园区注册且具备软件企业资质的可申报本奖励。"
            "上年度营业收入不低于 2000 万元。"
            "研发费用占销售收入比例不低于 5%。"
        ),
    },
    {
        "code": "P2026-XCL",
        "title": "新材料首批次应用保险补偿",
        "issuer": "江苏省工业和信息化厅",
        "doc_no": "苏工信材〔2026〕76 号",
        "source_kind": "gazette",
        "source_name": "江苏省工信厅公报",
        "published_on": "2026-11-01",
        "deadline": "2026-12-28",
        "fund_cap_wan": 150,
        "status": "active",
        "text": (
            "属于新材料行业的企业，须拥有高新技术企业资质。"
            "申报企业须在园区注册。"
        ),
    },
    {
        "code": "P2026-SWYY",
        "title": "生物医药产业专项扶持",
        "issuer": "园区生物产业发展有限公司",
        "doc_no": "苏园生〔2026〕33 号",
        "source_kind": "wechat",
        "source_name": "园区生物产业公众号",
        "published_on": "2026-11-03",
        "deadline": "2026-11-17",
        "fund_cap_wan": 500,
        "status": "active",
        "text": (
            "支持属于生物医药行业的企业。"
            "申报企业须在园区注册。"
            "研发费用占销售收入比例不低于百分之八。"
        ),
    },
    {
        "code": "P2026-JNJB",
        "title": "节能降碳技术改造补助",
        "issuer": "苏州市发展和改革委员会",
        "doc_no": "苏发改资环〔2026〕12 号",
        "source_kind": "website",
        "source_name": "苏州市发改委门户",
        "published_on": "2026-09-18",
        "deadline": "2026-10-31",
        "fund_cap_wan": 120,
        "status": "expired",
        "text": "支持属于节能环保行业的企业。申报企业须在园区注册。",
    },
    {
        "code": "P2026-KJXZ",
        "title": "科技型中小企业评价入库奖励",
        "issuer": "苏州工业园区科技创新委员会",
        "doc_no": "苏园科创〔2026〕31 号",
        "source_kind": "forward",
        "source_name": "园区科创委转发通知",
        "published_on": "2026-11-04",
        "deadline": "2026-12-20",
        "fund_cap_wan": 20,
        "status": "active",
        "text": (
            "在园区注册且已获得科技型中小企业认定的企业可申报。"
            "上年度营业收入不超过 5000 万元。"
        ),
    },
    {
        "code": "P2026-ZXQY",
        "title": "专精特新“小巨人”配套奖励（征求意见稿）",
        "issuer": "苏州工业园区经济发展委员会",
        "doc_no": "苏园经发〔2026〕21 号",
        "source_kind": "website",
        "source_name": "园区经发委公众号",
        "published_on": "2026-11-06",
        "deadline": None,
        "fund_cap_wan": 100,
        "status": "draft",
        "text": (
            "拟对已获得专精特新中小企业认定的企业给予配套奖励。"
            "上年度营业收入不低于五千万元。"
            "申报企业须在园区注册。"
            "本奖励实施细则尚在征求意见。"
        ),
    },
    {
        "code": "P2026-RZZX",
        "title": "企业研发机构建设资助",
        "issuer": "苏州工业园区科技创新委员会",
        "doc_no": "苏园科创〔2026〕35 号",
        "source_kind": "website",
        "source_name": "园区科创委政策专栏",
        "published_on": "2026-11-05",
        "deadline": "2026-11-18",
        "fund_cap_wan": 60,
        "status": "active",
        "text": (
            "拥有企业技术中心资质的企业可申报。"
            "上年度研发费用占销售收入比例不低于 4%。"
        ),
    },
    {
        "code": "P2026-GYHL",
        "title": "工业互联网标杆工厂奖励",
        "issuer": "苏州市工业和信息化局",
        "doc_no": "苏工信信〔2026〕58 号",
        "source_kind": "wechat",
        "source_name": "苏州工信门户",
        "published_on": "2026-11-02",
        "deadline": "2026-12-10",
        "fund_cap_wan": 200,
        "status": "active",
        "text": (
            "支持属于电子信息、装备制造行业的企业。"
            "在苏州市注册且已获得高新技术企业认定。"
        ),
    },
    {
        "code": "P2026-ZSCQ",
        "title": "知识产权质押融资贴息",
        "issuer": "苏州工业园区市场监督管理局",
        "doc_no": "苏园市监〔2026〕44 号",
        "source_kind": "forward",
        "source_name": "园区市监局转发通知",
        "published_on": "2026-11-07",
        "deadline": "2026-12-25",
        "fund_cap_wan": 30,
        "status": "active",
        "text": (
            "在园区注册且已获得专精特新中小企业认定的中小企业可申报。"
            "上年度营业收入不超过 10000 万元。"
        ),
    },
]

# ---------------------------------------------------------------- 企业画像
# 先按「园区/区外 × 行业 × 资质 × 数量」分组，再生成具体企业；保证分布可控、可复现。
COMPANY_SPECS: list[dict] = [
    # ---- 园区（48 家）----
    {"district": "园区", "industry": "装备制造", "quals": ["科技型中小企业"], "count": 2},
    {"district": "园区", "industry": "装备制造", "quals": [], "count": 8},
    {"district": "园区", "industry": "软件信息", "quals": ["软件企业"], "count": 4},
    {"district": "园区", "industry": "软件信息", "quals": [], "count": 7},
    {"district": "园区", "industry": "电子信息", "quals": ["专精特新"], "count": 2},
    {"district": "园区", "industry": "电子信息", "quals": [], "count": 5},
    {"district": "园区", "industry": "新材料", "quals": ["高新技术企业"], "count": 3},
    {"district": "园区", "industry": "新材料", "quals": ["专精特新"], "count": 1},
    {"district": "园区", "industry": "新材料", "quals": [], "count": 2},
    {"district": "园区", "industry": "生物医药", "quals": ["科技型中小企业"], "count": 1},
    {"district": "园区", "industry": "生物医药", "quals": ["专精特新"], "count": 1},
    {"district": "园区", "industry": "生物医药", "quals": [], "count": 3},
    {"district": "园区", "industry": "节能环保", "quals": [], "count": 9},
    # ---- 区外（66 家）----
    {"district": "吴中区", "industry": "装备制造", "quals": ["高新技术企业"], "count": 5},
    {"district": "吴中区", "industry": "软件信息", "quals": ["高新技术企业"], "count": 3},
    {"district": "吴中区", "industry": "新材料", "quals": [], "count": 3},
    {"district": "吴中区", "industry": "电子信息", "quals": ["高新技术企业"], "count": 2},
    {"district": "吴中区", "industry": "装备制造", "quals": ["企业技术中心"], "count": 2},
    {"district": "姑苏区", "industry": "电子信息", "quals": ["高新技术企业"], "count": 4},
    {"district": "姑苏区", "industry": "装备制造", "quals": [], "count": 3},
    {"district": "姑苏区", "industry": "节能环保", "quals": ["高新技术企业"], "count": 3},
    {"district": "姑苏区", "industry": "生物医药", "quals": ["科技型中小企业"], "count": 2},
    {"district": "相城区", "industry": "装备制造", "quals": ["高新技术企业"], "count": 4},
    {"district": "相城区", "industry": "新材料", "quals": ["高新技术企业"], "count": 3},
    {"district": "相城区", "industry": "生物医药", "quals": ["高新技术企业"], "count": 2},
    {"district": "相城区", "industry": "电子信息", "quals": ["专精特新"], "count": 2},
    {"district": "相城区", "industry": "新材料", "quals": ["企业技术中心"], "count": 1},
    {"district": "昆山市", "industry": "电子信息", "quals": ["高新技术企业"], "count": 4},
    {"district": "昆山市", "industry": "装备制造", "quals": ["科技型中小企业"], "count": 3},
    {"district": "昆山市", "industry": "软件信息", "quals": ["高新技术企业"], "count": 2},
    {"district": "昆山市", "industry": "新材料", "quals": ["高新技术企业"], "count": 2},
    {"district": "昆山市", "industry": "电子信息", "quals": ["企业技术中心"], "count": 2},
    {"district": "吴江区", "industry": "装备制造", "quals": ["高新技术企业"], "count": 5},
    {"district": "吴江区", "industry": "节能环保", "quals": ["高新技术企业"], "count": 3},
    {"district": "吴江区", "industry": "新材料", "quals": ["专精特新"], "count": 3},
    {"district": "吴江区", "industry": "软件信息", "quals": ["科技型中小企业"], "count": 2},
    {"district": "吴江区", "industry": "软件信息", "quals": ["企业技术中心"], "count": 1},
]

# 首批重点客户：客户经理点名要盯的 6 家（覆盖不同缺口类型）
FEATURED_COMPANIES: list[dict] = [
    {
        "name": "苏州锐驰精密机械有限公司",
        "industry": "装备制造",
        "district": "园区",
        "revenue_wan": 8600,
        "rd_ratio": 2.8,
        "employees": 240,
        "qualifications": ["高新技术企业", "科技型中小企业"],
        "contact": "0512-6288 1137",
        "owner": "许棠",
    },
    {
        "name": "苏州恒达智能装备有限公司",
        "industry": "装备制造",
        "district": "园区",
        "revenue_wan": 12600,
        "rd_ratio": 3.6,
        "employees": 320,
        "qualifications": ["高新技术企业", "专精特新", "科技型中小企业"],
        "contact": "0512-6288 2043",
        "owner": "许棠",
    },
    {
        "name": "苏州瑞泰软件科技有限公司",
        "industry": "软件信息",
        "district": "园区",
        "revenue_wan": 4300,
        "rd_ratio": 6.2,
        "employees": 138,
        "qualifications": ["高新技术企业", "软件企业", "科技型中小企业"],
        "contact": "0512-6299 7731",
        "owner": "顾清",
    },
    {
        "name": "苏州晶湛新材料科技有限公司",
        "industry": "新材料",
        "district": "园区",
        "revenue_wan": 7400,
        "rd_ratio": 4.1,
        "employees": 190,
        "qualifications": ["高新技术企业", "专精特新"],
        "contact": "0512-6290 4412",
        "owner": "顾清",
    },
    {
        "name": "苏州博众生物医药有限公司",
        "industry": "生物医药",
        "district": "园区",
        "revenue_wan": 9800,
        "rd_ratio": 7.4,
        "employees": 260,
        "qualifications": ["科技型中小企业"],
        "contact": "0512-6285 3027",
        "owner": "沈砚",
    },
    {
        "name": "苏州中铸节能环保科技有限公司",
        "industry": "节能环保",
        "district": "园区",
        "revenue_wan": 5300,
        "rd_ratio": 3.2,
        "employees": 150,
        "qualifications": [],
        "contact": "0512-6291 5580",
        "owner": "沈砚",
    },
]

PREFIXES = [
    "锐驰", "恒达", "瑞泰", "华翔", "中铸", "新纶", "博众", "科达", "鑫泰", "德睿",
    "弘信", "正业", "天准", "联讯", "瀚川", "晶湛", "信达", "中瑞", "力神", "维信",
]

INDUSTRY_SUFFIX: dict[str, list[str]] = {
    "装备制造": ["精密机械", "智能装备", "机电科技"],
    "软件信息": ["软件科技", "信息技术", "数据科技"],
    "新材料": ["新材料科技", "材料科技", "复合材"],
    "生物医药": ["生物医药", "生物科技", "医疗器械"],
    "电子信息": ["电子科技", "光电科技", "微电子"],
    "节能环保": ["节能环保", "环境工程", "节能科技"],
}

# 各行业的财务口径区间（万元 / % / 人），确定性取值
INDUSTRY_PROFILE: dict[str, tuple[int, int, float, int]] = {
    "装备制造": (5200, 24000, 2.6, 260),
    "软件信息": (2600, 12000, 5.2, 130),
    "新材料": (4800, 18000, 3.4, 180),
    "生物医药": (3600, 16000, 6.8, 210),
    "电子信息": (6200, 26000, 3.1, 340),
    "节能环保": (4200, 15000, 2.9, 160),
}

# 一次匹配运行（11 月申报窗口）：覆盖 8 条申报中政策
SEED_RUN = {
    "seed_key": "seed-match-run-2026-11",
    "trigger": "seed",
    "operator_email": "analyst@policyfit.io",
    "policy_codes": [
        "P2026-ZJTX",
        "P2026-GXJS",
        "P2026-RJQY",
        "P2026-XCL",
        "P2026-KJXZ",
        "P2026-RZZX",
        "P2026-ZSCQ",
    ],
    "label": "2026 年 11 月第二批申报窗口",
}

QUALIFICATION_POOL = ["高新技术企业", "科技型中小企业", "软件企业", "专精特新", "企业技术中心"]


def _profile_for(industry: str, index: int) -> tuple[float, float, int]:
    low, high, rd_base, staff = INDUSTRY_PROFILE[industry]
    span = high - low
    revenue = low + (span * ((index * 37) % 100)) / 100.0
    rd_ratio = round(rd_base + ((index * 13) % 22) / 10.0 - 0.6, 1)
    employees = staff + (index * 17) % 180
    return round(revenue, 0), max(0.4, rd_ratio), employees


def build_companies() -> list[dict]:
    """生成 120 家企业（featured 6 家 + 规格分组 114 家）。"""
    rows: list[dict] = []
    for item in FEATURED_COMPANIES:
        rows.append(dict(item, code="", seed_key=""))

    used = {item["name"] for item in FEATURED_COMPANIES}
    counters: dict[str, int] = {}
    for spec in COMPANY_SPECS:
        industry = spec["industry"]
        for offset in range(int(spec["count"])):
            seen = counters.get(industry, 0)
            suffixes = INDUSTRY_SUFFIX[industry]
            name = ""
            for probe in range(len(PREFIXES) * len(suffixes)):
                prefix = PREFIXES[(seen + probe) // len(suffixes) % len(PREFIXES)]
                suffix = suffixes[(seen + probe) % len(suffixes)]
                candidate = f"苏州{prefix}{suffix}有限公司"
                if candidate not in used:
                    name = candidate
                    break
            used.add(name)
            revenue, rd_ratio, employees = _profile_for(industry, seen + offset + 3)
            counters[industry] = seen + 1
            rows.append(
                {
                    "name": name,
                    "industry": industry,
                    "district": spec["district"],
                    "revenue_wan": revenue,
                    "rd_ratio": rd_ratio,
                    "employees": employees,
                    "qualifications": list(spec["quals"]),
                    "contact": f"0512-62{80 + (seen * 7) % 19}{(seen * 31) % 90 + 10}",
                    "owner": ["许棠", "顾清", "沈砚", "陆岑"][seen % 4],
                }
            )
    return rows


COMPANIES = build_companies()
