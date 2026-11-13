/**
 * 项目品牌、导航、角色权限与枚举文案（前端唯一定义处）。
 * 后端对应：backend/src/constants/{roles,enums}.py；README 列出全部出现位置。
 */
export const BRAND = {
  short: 'policyfit',
  title: '惠企政策采集与申报资格匹配台',
  org: '苏州工业园区企服通 · 政策服务组',
  edition: '政策服务 · 2026 年度',
  subtitle: '政策入库 → 条件抽取 → 企业匹配 → 申报清单',
  loginLead: '把 12 个政府门户与公众号的通知收进一本登记簿：条件可复核、匹配可追溯、截止日不再错过。',
  loginPoints: [
    ['01', '政策原文入库即编号登记，发文机关与文号可回查。'],
    ['02', '申报条件由原文抽出，置信度低于 0.6 的必须人工确认。'],
    ['03', '匹配得分、缺口与复核意见全部由后端算出并留痕。'],
  ],
};

export const NAV = [
  { to: '#/overview', no: '01', label: '总览目录', permission: 'overview:read' },
  { to: '#/policies', no: '02', label: '政策库', permission: 'policy:read' },
  { to: '#/companies', no: '03', label: '企业画像', permission: 'company:read' },
  { to: '#/matches', no: '04', label: '匹配工作台', permission: 'match:read' },
  { to: '#/exports', no: '05', label: '申报清单', permission: 'export:read' },
  { to: '#/audit', no: '06', label: '审计日志', permission: 'audit:read' },
];

export const ROLE_LABELS = {
  admin: '政策运营',
  analyst: '政策专员',
  viewer: '客户经理（只读）',
};

export const PERMISSIONS = {
  admin: [
    'overview:read', 'policy:read', 'policy:write', 'company:read', 'company:write',
    'correction:read', 'correction:write',
    'rule:read', 'rule:extract', 'match:read', 'match:run', 'match:review',
    'export:read', 'audit:read',
  ],
  analyst: [
    'overview:read', 'policy:read', 'company:read', 'company:write',
    'correction:read', 'correction:write',
    'rule:read', 'rule:extract', 'match:read', 'match:run', 'match:review', 'export:read',
  ],
  viewer: ['overview:read', 'policy:read', 'company:read', 'correction:read', 'rule:read', 'match:read'],
};

export const ENUMS = {
  policyStatus: { draft: '草稿', active: '申报中', expired: '已过期' },
  channel: { website: '政府门户', wechat: '公众号', gazette: '政策公报', forward: '转发通知' },
  priority: { P0: 'P0 优先', P1: 'P1 跟进', P2: 'P2 观察' },
  review: { pending: '待复核', confirmed: '已确认', dismissed: '已驳回' },
  runStatus: { queued: '排队中', running: '执行中', success: '成功', partial: '部分成功', failed: '失败' },
  trigger: { manual: '手动', schedule: '定时', seed: '初始化' },
  correctionSource: {
    registry: '工商回传',
    customer: '客户补录',
    annual: '年报核对',
    manual: '人工修正',
  },
  correctionStatus: { pending: '待核验', verified: '已核验', rejected: '已驳回' },
  ruleField: {
    industry: '所属行业',
    region: '注册地',
    revenue_wan: '营业收入',
    rd_ratio: '研发占比',
    employees: '员工人数',
    qualification: '企业资质',
    deadline: '申报截止',
  },
  ruleOp: { '<=': '不超过', '>=': '不低于', '==': '等于', in: '属于' },
};

export const CORRECTION_FIELD_OPTIONS = [
  { value: 'industry', label: '所属行业' },
  { value: 'region', label: '注册地' },
  { value: 'revenue_wan', label: '营业收入(万元)' },
  { value: 'rd_ratio', label: '研发占比(%)' },
  { value: 'employees', label: '员工人数' },
  { value: 'qualification', label: '企业资质' },
];

export function correctionStatusTone(status) {
  return { pending: 'warn', verified: 'ok', rejected: 'danger' }[status] || 'info';
}

export function correctionSourceTone(source) {
  return { registry: 'ok', annual: 'ok', customer: 'warn', manual: 'info' }[source] || 'info';
}

export function can(role, permission) {
  return (PERMISSIONS[role] || []).includes(permission);
}

export function priorityTone(priority) {
  return { P0: 'p0', P1: 'p1', P2: 'p2' }[priority] || 'p2';
}

export function reviewTone(status) {
  return { pending: 'pending warn', confirmed: 'ok', dismissed: 'danger' }[status] || 'info';
}

export function policyTone(status) {
  return { active: 'ok', draft: 'info', expired: 'danger' }[status] || 'info';
}

export function runTone(status) {
  return { success: 'ok', partial: 'warn', failed: 'danger', running: 'info' }[status] || 'info';
}

export function confidenceTone(confidence) {
  return confidence < 0.6 ? 'conf low' : 'conf';
}

export const CONFIDENCE_REVIEW_THRESHOLD = 0.6;
