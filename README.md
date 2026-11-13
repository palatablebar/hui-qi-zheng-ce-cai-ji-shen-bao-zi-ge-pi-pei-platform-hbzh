# 惠企政策采集与申报资格匹配台（`policyfit`）

> 数据工程 · 小型多模块。原生 HTML/CSS/JS 前端 + Python FastAPI 后端 + Celery worker + PostgreSQL 16 + Redis，5 个容器一键起。

## 1. 场景

- **模拟客户**：苏州工业园区「企服通」政策服务组，6 人，服务 120 家中小制造 / 软件企业。
- **现有工作流**：每天从 12 个政府门户与公众号收通知，助理把申报条件抄进 Excel，再人工比对客户画像，电话通知。
- **三个痛点**：
  1. 政策散、靠人盯，漏通知；
  2. 条件口径不一（营收 / 研发占比 / 注册地 / 资质），不同人抄出不同版本；
  3. 截止日错过，客户抱怨「能报的没人告诉我」。
- **上下游**：政府门户 / 公众号 → 本系统（政策入库 → 条件抽取 → 企业匹配 → 申报清单 CSV）→ 客户经理外呼与材料准备。
- **一天的工作剧本**：
  1. 09:10 政策运营沈砚在「政策库」登记《2026 年度专精特新培育资助》，文号 `苏园经发〔2026〕18 号`；
  2. 粘贴原文后点「重新抽取申报条件」，系统抽出 4 条条件，其中「研发投入强度不低于百分之三」置信度 0.55，标红待人工确认；
  3. 10:00 专员顾清打开「企业画像」，确认 120 家客户的营收 / 研发占比 / 资质（客户经理只读且看不到电话）；
  4. 10:20 在「匹配工作台」选择「2026 年 11 月第二批申报窗口」发起匹配，840 个组合中 40 家进入清单，P0 6 条；
  5. 10:35 打开「苏州锐驰精密机械有限公司」，缺口显示「研发占比 2.8% < 3%（差 0.2pt）」，复核为 confirmed 并写备注；
  6. 10:50 在「申报清单」导出 CSV（40 行 + 表头，UTF-8 BOM，Excel 直接打开）；
  7. 11:00 组长在「审计日志」核对抽取 / 运行 / 复核 / 导出的操作人。

## 2. 角色与权限

| 角色 | 账号 | 权限 | 典型动作 |
|---|---|---|---|
| 政策运营 `admin` | `admin@policyfit.io` | 政策维护 + 条件抽取 + 企业维护 + 跑匹配 + 复核 + 导出 + 审计 | 登记政策、改截止日、导出申报清单、查审计 |
| 政策专员 `analyst` | `analyst@policyfit.io` | 条件抽取 + 企业维护 + 跑匹配 + 复核 + 导出 | 维护企业画像、复核匹配、导出清单 |
| 客户经理 `viewer` | `viewer@policyfit.io` | 只读政策 / 条件 / 企业 / 匹配结果 | 看政策与结果；**看不到联系人电话**，不能跑匹配或复核 |

密码统一：`Demo@2026`。低权角色调用高权接口返回 **403**（真实 HTTP 状态，不是前端隐藏），无 token 返回 **401**。

已实现 403 的接口：`POST /api/policies`、`POST /api/policies/{id}/extract-rules`、`POST /api/companies`、`PATCH /api/companies/{id}`、`POST /api/corrections/company/{id}`、`PATCH /api/corrections/{id}/verify`、`PATCH /api/corrections/{id}/reject`、`POST /api/match-runs`、`PATCH /api/matches/{id}/review`、`GET /api/audit`、`GET /api/exports/matches.csv`、`GET /api/exports/corrections.csv`。

## 3. 功能模块（可串成链路）

1. **政策库**：政策台账（编号 / 标题 / 发文机关 / 文号 / 采集渠道 / 截止日 / 资助上限 / 原文）的登记、筛选、详情；详情页展示原文与抽取出的条件。
2. **条件抽取**：`POST /api/policies/{id}/extract-rules` 调算法 A，按自然键 `(policy_id, field, op, value)` 幂等落库；置信度 < 0.60 的条件标红待人工。
3. **企业画像**：120 家企业的行业 / 注册地 / 营收 / 研发占比 / 员工数 / 资质 / 联系人；`viewer` 联系人掩码为 `***`。画像指标不直接覆盖，统一走「更正留痕 → 核验」流程。
4. **画像更正台账**：工商回传 / 客户补录 / 年报核对 / 人工修正每一条都留痕，记录字段、更正前后值、来源、来源单号、可信度、收到时间、确认状态（待核验 / 已核验 / 已驳回）。**只有核验通过的值才回写画像并进入下一次匹配**；待核验、已驳回不影响当前画像。核验时自动测算对历次匹配的得分前后影响。
5. **匹配工作台**：`POST /api/match-runs` 调算法 B，只把硬条件全过的企业写入清单，输出得分 / 优先级 / 缺口；**每次运行固化当时企业画像快照（`matches.company_snapshot`）**，画像后续更正不改变旧结果，重跑只生成新运行、不覆盖旧结果；复核 `confirmed/dismissed` 留痕。详情可看得分依据、快照与当前画像差异、更正前后影响。
6. **申报清单导出**：`GET /api/exports/matches.csv`（按 P0→P1→P2、得分降序，指标取匹配时快照并附画像依据来源 / 快照时间）、`GET /api/exports/corrections.csv`（画像更正台账）与 `GET /api/exports/policies.csv`。
7. **审计**：登录、政策新建/修改、条件抽取、企业修改、更正提交/核验/驳回、匹配运行、复核、导出全部落 `audit_logs`（HTTP 层 + 领域层两条）。

## 4. 快速启动

```bash
cp .env.example .env
docker compose up -d --build     # 等 5/5 healthy
open http://localhost:18200
```

首次启动 backend 自动建表并 seed 一次（`SEED_DEMO=true`）。seed 幂等，可重复执行：

```bash
docker compose exec -T backend python -m scripts.seed_demo
# SEED_SUMMARY brand=policyfit users=3 sources=12 runs=1 findings=40 pending=40
```

数据口径：12 条政策（其中 3 条条件歧义）、38 条条件、120 家企业、1 次匹配运行（40 条结果，P0 6 条，pending 全部）、4 条画像更正演示（已核验 1 / 待核验 2 / 已驳回 1）。

## 5. 本地开发

```bash
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
cd frontend/site && python -m http.server 5173   # 静态站，/api 指到 8000
```

## 6. 访问地址

| 服务 | 地址 |
|---|---|
| 前端 | http://localhost:18200 |
| 后端 API 文档 | http://localhost:19200/docs |
| 健康检查 | http://localhost:19200/api/health |
| 数据库映射 | localhost:17700 |

## 7. 技术栈

| 层 | 选型 |
|---|---|
| 前端 | 原生 HTML5 + CSS（oklch 令牌 / 档案纸纹理）+ ES Modules；无框架、无打包 |
| 后端 | Python 3.11、FastAPI 0.115、SQLAlchemy 2.0、PyJWT、passlib(bcrypt) |
| 异步 | Celery 5.4 + Redis（10s 心跳、每日 07:40 对全部申报中政策重跑匹配） |
| 数据库 | PostgreSQL 16 |
| 部署 | Docker Compose，恰好 5 服务（frontend/backend/worker/db/redis） |

## 8. 目录

```text
backend/
  src/config      配置 / SQLAlchemy engine / Celery
  src/constants   enums（共享枚举唯一后端定义处）、roles、log_templates、limits
  src/models      policy / rule / company / profile_correction / match_run / match / user / audit
  src/schemas     policy / company / correction / match / match_run / auth / common
  src/services    rule_extractor(算法A) / match_engine(算法B) / correction_service(更正留痕/核验/影响)
                  / policy / company / match / overview / export / audit / auth
  src/controllers policy / company / correction / match / export / auth
  src/routes      policies / companies / corrections / match-runs / matches / exports / overview / audit / auth / health
  scripts         demo_config（12 政策 + 120 企业 + 4 更正）/ seed_demo / worker_healthcheck.sh
  tests           test_rule_extractor / test_match_engine / test_corrections / test_security
frontend/site/
  css/tokens.css  政务档案色板 + 双字体
  css/app.css     红头 / 登记簿 / 案卷目录 / 截止周历 / 条件清单 / 更正留痕 / 快照依据
  js/{config,api,store,ui,app}.js
  js/pages/{login,overview,policies,companies,matches,exports,audit}.js
```

## 9. 环境变量

见 `.env.example`：`COMPOSE_PROJECT_NAME`、`FRONTEND_PORT=18200`、`BACKEND_PORT=19200`、`DB_PORT=17700`、`DB_*`、`JWT_SECRET`、`REDIS_URL`、`SEED_DEMO`、`RATE_LIMIT_*`。端口由题目分配，未改动。

## 10. 核心算法与口径

### 算法 A｜申报条件抽取（`backend/src/services/rule_extractor.py`，纯函数）

- **输入**：政策 `original_text`（按 `。；;换行` 切句）。
- **输出**：`{rules, unparsed, negatives, deadline, fund_cap_wan, stats}`，每条 rule 为 `{field, op, value, unit, required, confidence, evidence}`。
- **识别句式**（`field` 枚举）：营业收入（`revenue_wan`）、研发费用占销售收入比例（`rd_ratio`）、从业人员（`employees`）、注册地（`region`）、所属行业（`industry`）、企业资质（`qualification`）、申报截止（`deadline`）。
- **区间**：「营业收入在 1000-5000 万元之间」→ 两条条件 `>=1000` 与 `<=5000`；`confidence` 各降 0.05（派生条件）。
- **金额换算**：亿元 ×10000 折成万元，`confidence -0.05`。
- **边界**：
  - 全角数字 / 全角百分号（`３％`）先归一化，`confidence -0.05`；
  - 中文数字（「百分之三」「五千万」）可解析，`confidence -0.35`（低于 0.60 → 待人工）；
  - 模糊措辞（原则上 / 左右 / 一般…）`confidence -0.15`；
  - 否定句（不含 / 不包括 / 除外 / 不适用）**不产出条件**，记入 `negatives`；
  - 像条件但无可解析数字的句子进 `unparsed`，前端在抽取结果里展示。
- **置信度基准**：营收/研发 0.90、注册地 0.90、截止 0.92、资质 0.88、行业 0.85；上限 0.96，下限 0.35。

### 算法 B｜资格匹配（`backend/src/services/match_engine.py`，纯函数）

- **硬条件**（`industry` / `region` / `qualification` / `deadline`）：布尔判定，`hard_ratio = 通过数 / 需判定数`，全过才 `hard_pass=True`；缺失字段 → 缺口「缺数据」，不计通过。
- **软条件**（`revenue_wan` / `rd_ratio` / `employees`）：余量 `margin=(actual-threshold)/threshold`（满足取正）。
  - 满足：单条得分 `0.6 + 0.4*min(1, margin)`；
  - 不满足：单条得分 `max(0, 0.6*(1+margin))`；
  - `soft_score` = 各必需软条件得分均值。
- **总分**：`score = 60*hard_ratio + 30*soft_score + 10*deadline_score`（0-100，保留 1 位）。
- **截止分**：已过期 0；≤7 天 1.0；≤15 天 0.8；≤30 天 0.6；≤60 天 0.4；其余 0.2；无截止日 0.2。
- **优先级**：P0 = 得分 ≥70 且硬条件全过且 `0 ≤ 距截止 ≤7` 天；P1 = 得分 ≥50 且硬条件全过；其余 P2。
- **缺口文案**：`研发占比 2.8% < 3%（差 0.2pt）`、`营业收入 26000 万元 > 20000 万元（差 6000 万元）`、`缺少资质「专精特新」`、`注册地「吴中区」≠「园区」`、`申报截止 2026-10-31 已过期 13 天`、`员工人数：缺数据`。
- **可复现**：当前日期由调用方传入（运行记录 `params.today`），同输入两次结果逐字一致。
- **落库规则**：一次运行只把 `hard_pass=True` 的组合写入 `matches`；`(run_id, policy_id, company_id)` 唯一。

### 画像更正与匹配快照口径（申报依据可回看）

- **更正留痕表 `profile_corrections`**：同一指标每次更正一条不可变记录，保存 `field / old_value / new_value / source / source_ref / trust_level / received_at / status / submitted_by / verified_at / verified_by / impact`。
- **三来源可信度**：工商回传 `registry`(0.95) > 年报核对 `annual`(0.90) > 人工修正 `manual`(0.80) > 客户补录 `customer`(0.70)；可信度仅用于提示与排序，不替代人工核验。
- **确认状态门禁**：提交即 `pending`，**不回写 `companies`、不参与匹配**；`PATCH /corrections/{id}/verify` 核验通过才回写画像（状态 `verified`），`reject` 驳回（状态 `rejected`）同样不改画像。匹配引擎只读 `companies`，因此天然只采用已核验值。
- **匹配快照固化**：每次 `run_matching` 对每家企业调用 `build_snapshot()` 固化当时画像，写入 `matches.company_snapshot`；引擎用该快照计算，结果与快照同生共死。画像之后再更正，历史 `matches` 的得分 / 缺口 / 快照都不变。
- **重跑不覆盖**：匹配运行以 `run_no` 追加，`(run_id, policy_id, company_id)` 唯一；重跑生成新运行与新快照，旧运行、旧结果、旧导出依据全部保留。
- **更正前后影响**：核验时 `_measure_impact()` 取该企业全部历史匹配，用「匹配时快照」与「套用更正值后的画像」分别重算（沿用运行 `params.today` 保证口径一致），输出每条匹配的 `score_before/after`、`score_delta`、优先级 / 硬条件变化与汇总；历史结果本身不重写，差异在下一次匹配生效。
- **工作台与导出**：匹配详情展示「匹配时快照 vs 当前画像」对照表（变更字段标红）与更正影响时间线；`matches.csv` 的企业指标取快照值并附「画像口径 / 画像依据来源 / 快照时间」，另提供 `corrections.csv` 导出完整更正台账。

## 11. 共享枚举出现位置

| 枚举 | 后端 | 前端 |
|---|---|---|
| 角色 `admin/analyst/viewer` | `backend/src/constants/{enums,roles}.py` | `frontend/site/js/config.js`（`ROLE_LABELS` / `PERMISSIONS`） |
| 政策状态 `draft/active/expired` | `backend/src/constants/enums.py` | `frontend/site/js/config.js`（`ENUMS.policyStatus`） |
| 采集渠道 `website/wechat/gazette/forward` | `backend/src/constants/enums.py` | `frontend/site/js/config.js`（`ENUMS.channel`） |
| 条件字段 `industry/region/revenue_wan/rd_ratio/employees/qualification/deadline` | `backend/src/constants/enums.py` | `frontend/site/js/config.js`（`ENUMS.ruleField`） |
| 条件运算符 `<= / >= / == / in` | `backend/src/constants/enums.py` | `frontend/site/js/config.js`（`ENUMS.ruleOp`） |
| 优先级 `P0/P1/P2` | `backend/src/constants/enums.py` | `frontend/site/js/config.js`（`ENUMS.priority`） |
| 复核状态 `pending/confirmed/dismissed` | `backend/src/constants/enums.py` | `frontend/site/js/config.js`（`ENUMS.review`） |
| 运行状态 / 触发方式 | `backend/src/constants/enums.py` | `frontend/site/js/config.js`（`ENUMS.runStatus` / `ENUMS.trigger`） |
| 更正来源 `registry/customer/annual/manual` | `backend/src/constants/enums.py`（`CorrectionSource`） | `frontend/site/js/config.js`（`ENUMS.correctionSource`） |
| 更正确认状态 `pending/verified/rejected` | `backend/src/constants/enums.py`（`CorrectionStatus`） | `frontend/site/js/config.js`（`ENUMS.correctionStatus`） |

## 12. Docker 说明

- 5 个服务：`frontend`(Nginx 静态站) / `backend`(uvicorn) / `worker`(Celery beat+worker) / `db`(PostgreSQL 16) / `redis`，全部带 healthcheck。
- 命名卷：`db_data`、`redis_data`；`backend` 等 `db`/`redis` healthy，`worker` 等 `backend` healthy，`frontend` 等 `backend` healthy。
- Nginx：`location /api/ { proxy_pass http://backend:8000/; }` + SPA 回落 `/index.html`。
- 收尾：`docker compose down -v --remove-orphans`。

## 13. 已知边界

- 条件抽取基于句式规则（非大模型），同一句子里出现多个数值时只取第一个匹配；复杂嵌套条款可能落入 `unparsed`，由人工在详情页确认。
- 匹配按「硬条件全过」入清单，因此 `gaps` 里可能出现软条件缺口（这正是提醒客户补强的地方）。
- 画像更正的影响测算是「重算口径对照」，用于回看前后差异；历史 `matches` 永不重写，已导出 CSV 也不回改，新口径只在下一次运行生效。
- 历史库若已存在 `matches` 表，启动时通过 `ADD COLUMN IF NOT EXISTS company_snapshot` 增量补列；更早运行产生的旧结果该字段为空，前端按「当前画像」兜底展示，新运行均带快照。
- 采集环节为模拟入库（seed 写入 12 条真实口径政策原文），不实际抓取政府网站。

## License

内部演示项目，仅用于评测与教学。
