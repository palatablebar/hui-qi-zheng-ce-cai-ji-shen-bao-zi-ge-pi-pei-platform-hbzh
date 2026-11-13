/** 无框架 UI 组件：表格 / 徽标 / 抽屉 / 空态 / 统计条 / 图表 / toast。 */

export function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
}

export function fmtTime(iso) {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return esc(iso);
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export function badge(tone, text) {
  return `<span class="badge ${esc(tone)}">${esc(text)}</span>`;
}

export function statStrip(items) {
  return `<div class="stat-strip">${items
    .map(
      (item) => `<div class="stat">
        <span class="k">${esc(item.label)}</span>
        <span class="v">${esc(item.value)}</span>
        <span class="hint">${esc(item.hint || '')}</span>
      </div>`,
    )
    .join('')}</div>`;
}

export function emptyState({ title, hint, actionText, actionId }) {
  return `<div class="empty" data-testid="empty-state">
    <div class="mark">${esc(title)}</div>
    <p>${esc(hint || '')}</p>
    ${actionText ? `<button class="btn ghost" id="${esc(actionId || 'empty-action')}">${esc(actionText)}</button>` : ''}
  </div>`;
}

export function errorBox(message, retryId = 'retry-btn') {
  return `<div class="error-box"><span>${esc(message)}</span><button class="btn sm ghost" id="${esc(retryId)}">重试</button></div>`;
}

export function table({ columns, rows, rowId, empty }) {
  if (!rows || rows.length === 0) return emptyState(empty || { title: '暂无记录', hint: '调整筛选条件或先发起一次运行。' });
  const head = columns.map((col) => `<th>${esc(col.label)}</th>`).join('');
  const body = rows
    .map(
      (row) => `<tr data-id="${esc(row.id)}" ${rowId ? `id="${esc(rowId(row))}"` : ''}>
        ${columns.map((col) => `<td class="${esc(col.className || '')}">${col.render ? col.render(row) : esc(row[col.key])}</td>`).join('')}
      </tr>`,
    )
    .join('');
  return `<div class="table-wrap"><table class="data"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

export function drawer({ title, subtitle, body, footer }) {
  const backdrop = document.createElement('div');
  backdrop.className = 'drawer-backdrop';
  backdrop.innerHTML = `<aside class="drawer" role="dialog" aria-modal="true">
    <div class="drawer-head">
      <div>
        <h2>${esc(title)}</h2>
        <div class="mono muted">${esc(subtitle || '')}</div>
      </div>
      <button class="btn sm ghost" data-close>关闭</button>
    </div>
    <div class="drawer-body">${body}</div>
    ${footer ? `<div class="drawer-foot">${footer}</div>` : ''}
  </aside>`;
  const close = () => {
    backdrop.remove();
    document.removeEventListener('keydown', onKey);
  };
  const onKey = (event) => {
    if (event.key === 'Escape') close();
  };
  backdrop.addEventListener('click', (event) => {
    if (event.target === backdrop || event.target.closest('[data-close]')) close();
  });
  document.addEventListener('keydown', onKey);
  document.body.appendChild(backdrop);
  return { root: backdrop, close };
}

export function kv(items) {
  return `<dl class="kv">${items
    .map(([key, value]) => `<dt>${esc(key)}</dt><dd>${value === undefined || value === null ? '—' : value}</dd>`)
    .join('')}</dl>`;
}

export function barList(items, tone = '') {
  const max = Math.max(1, ...items.map((item) => item.count));
  return `<div class="bars">${items
    .map(
      (item) => `<div class="bar-row">
        <span>${esc(item.label)}</span>
        <div class="bar-track"><div class="bar-fill ${esc(tone)}" style="width:${Math.round((item.count / max) * 100)}%"></div></div>
        <span class="mono">${esc(item.count)}</span>
      </div>`,
    )
    .join('')}</div>`;
}

export function trendChart(points) {
  const max = Math.max(1, ...points.map((point) => point.runs));
  return `<div class="trend">${points
    .map(
      (point) => `<div class="col" title="${esc(point.date)} · ${esc(point.runs)} 次">
        <div class="stem" style="height:${Math.max(2, Math.round((point.runs / max) * 68))}px"></div>
        <span class="lbl">${esc(point.date.slice(5))}</span>
      </div>`,
    )
    .join('')}</div>`;
}

export function field({ label, name, type = 'text', value = '', placeholder = '', options = null, attrs = '' }) {
  const control = options
    ? `<select name="${esc(name)}" id="${esc(name)}" ${attrs}>${options
        .map((opt) => `<option value="${esc(opt.value)}" ${String(opt.value) === String(value) ? 'selected' : ''}>${esc(opt.label)}</option>`)
        .join('')}</select>`
    : `<input name="${esc(name)}" id="${esc(name)}" type="${esc(type)}" value="${esc(value)}" placeholder="${esc(placeholder)}" ${attrs} />`;
  return `<div class="field"><label for="${esc(name)}">${esc(label)}</label>${control}</div>`;
}

export function toast(message, tone = '') {
  const stack = document.getElementById('toast-stack');
  const node = document.createElement('div');
  node.className = `toast ${tone}`;
  node.textContent = message;
  stack.appendChild(node);
  setTimeout(() => node.remove(), 3600);
}

export function errorMessage(err) {
  if (!err) return '未知错误';
  if (err.code === 'FORBIDDEN') return '当前角色没有这个操作的权限';
  return err.message || '请求失败';
}

/* ---------- 政务档案版块组件（总览/政策库/导出共用） ---------- */

export function seal(text, small = false) {
  const lines = String(text || '').split('\n').map((line) => esc(line));
  return `<div class="seal ${small ? 'sm' : ''}" aria-hidden="true"><span>${lines.join('<br />')}</span></div>`;
}

export function redhead({ org, doc, left = false }) {
  return `<div class="redhead ${left ? 'left' : ''}">
    <span class="org">${esc(org)}</span>
    <span class="doc">${esc(doc)}</span>
  </div>`;
}

export function metaLine(items) {
  return `<div class="meta-line">${items
    .map(
      (item) => `<div class="cell">
        <span class="k">${esc(item.label)}</span>
        <span class="v">${esc(item.value)}${item.unit ? `<small>${esc(item.unit)}</small>` : ''}</span>
        <span class="hint">${esc(item.hint || '')}</span>
      </div>`,
    )
    .join('')}</div>`;
}

export function calendarStrip(days, today) {
  return `<div class="calendar">${days
    .map(
      (day) => `<div class="day ${day.count ? 'has' : ''} ${day.date === today ? 'today' : ''}" title="${esc(
        (day.titles || []).join(' / '),
      )}">
        <span class="d">${esc(day.label)}</span>
        <span class="n">${esc(day.count)}</span>
        ${day.count ? `<span class="tag">${esc((day.codes || []).slice(0, 2).join(' '))}</span>` : ''}
      </div>`,
    )
    .join('')}</div>`;
}

export function ruleList(rules) {
  if (!rules || !rules.length) return emptyState({ title: '尚未抽取条件', hint: '在政策详情里点「抽取申报条件」。' });
  return `<div class="rule-list">${rules
    .map(
      (rule) => `<div class="rule-item" data-rule="${esc(rule.id)}">
        <span class="field">${esc(rule.field_label)}</span>
        <span class="expr">${esc(rule.op)}</span>
        <span class="expr"><b>${esc(rule.value)}</b>${rule.unit ? ` ${esc(rule.unit)}` : ''}</span>
        <span class="${rule.confidence < 0.6 ? 'conf low' : 'conf'}">${Number(rule.confidence).toFixed(2)}</span>
        <span class="ev">${esc(rule.evidence_sentence || '')}</span>
      </div>`,
    )
    .join('')}</div>`;
}

export function gapList(gaps) {
  if (!gaps || !gaps.length) return '<ul class="gap-list"><li class="none">硬条件与软条件全部满足，无缺口</li></ul>';
  return `<ul class="gap-list">${gaps.map((gap) => `<li>${esc(gap)}</li>`).join('')}</ul>`;
}

export function scoreBar(score) {
  const value = Math.max(0, Math.min(100, Number(score) || 0));
  return `<div style="display:grid;gap:3px;min-width:96px">
    <span class="score">${value.toFixed(1)}</span>
    <span class="score-bar"><i style="width:${value}%"></i></span>
  </div>`;
}

export function chipRow(items) {
  return `<div class="chip-row">${items
    .map((item) => `<span class="chip">${esc(item.label)} <b>${esc(item.count)}</b></span>`)
    .join('')}</div>`;
}
