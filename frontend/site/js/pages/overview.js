import { api } from '../api.js';
import { ENUMS, priorityTone, reviewTone } from '../config.js';
import { barList, calendarStrip, chipRow, emptyState, errorBox, errorMessage, esc, metaLine } from '../ui.js';

const URGENT_DAYS = 7;

function daysBetween(dateText, today) {
  if (!dateText) return null;
  const target = new Date(`${dateText}T00:00:00+08:00`);
  const base = new Date(`${today}T00:00:00+08:00`);
  return Math.round((target - base) / 86400000);
}

function dossierRows(policies, today) {
  if (!policies.length) return emptyState({ title: '案卷空', hint: '先到「政策库」登记政策。' });
  return `<div class="dossier">${policies
    .map((policy, index) => {
      const left = daysBetween(policy.deadline, today);
      const urgent = left !== null && left >= 0 && left <= URGENT_DAYS;
      return `<div class="dossier-row ${urgent ? 'urgent' : ''}" data-policy="${policy.id}">
        <span class="no">${String(index + 1).padStart(2, '0')}</span>
        <span class="code">${esc(policy.code)}</span>
        <span class="title">${esc(policy.title)}<span class="muted mono"> · ${esc(policy.issuer)}</span></span>
        <span class="deadline">${esc(policy.deadline || '未定')}${left !== null && left >= 0 ? ` · 剩 ${left} 天` : ''}</span>
        <span class="tail">${
          policy.fund_cap_wan ? `<span class="badge info">上限 ${esc(policy.fund_cap_wan)} 万</span>` : ''
        }</span>
      </div>`;
    })
    .join('')}</div>`;
}

function windowReminders(days) {
  const busy = days.filter((day) => day.count > 0);
  if (!busy.length) return '<p class="muted mono">近 7 天没有截止的政策。</p>';
  const rows = [];
  busy.forEach((day) => {
    (day.titles || []).forEach((title, index) => {
      rows.push({ day: day.date.slice(5), title, code: (day.codes || [])[index] || '' });
    });
  });
  return `<div class="dossier">${rows
    .map(
      (row) => `<div class="dossier-row" style="grid-template-columns:70px minmax(0,1fr)">
        <span class="deadline" style="text-align:left">${esc(row.day)} 截止</span>
        <span class="title">${esc(row.title)} <span class="mono muted">${esc(row.code)}</span></span>
      </div>`,
    )
    .join('')}</div>`;
}

export const overviewPage = {
  async render(view, ctx) {
    view.innerHTML = '<div class="empty"><div class="mark">正在调阅案卷…</div></div>';
    try {
      const data = await api.get('/api/overview');
      const latest = data.latest_run;
      view.innerHTML = `
        ${metaLine([
          { label: '在册政策', value: data.policies_total, unit: '件', hint: `申报中 ${data.active_total} 件` },
          { label: '企业画像', value: data.companies_total, unit: '家', hint: `高匹配 ${data.high_match_companies} 家` },
          { label: '待办匹配', value: data.pending_total, unit: '条', hint: `P0 ${data.p0_total} 条` },
          { label: '抽取条件', value: data.rules_total, unit: '条', hint: `低置信 ${data.low_confidence_rules} 条待人工` },
          { label: '采集渠道', value: data.channels.length, unit: '类', hint: `${data.policies_total} 条政策在册` },
        ])}
        <div class="grid-2">
          <section class="panel">
            <div class="panel-head">
              <h2>申报窗口案卷目录</h2>
              <span class="meta">${esc(data.today)} · 截止最近 6 件</span>
            </div>
            <div class="panel-body" style="padding:0">
              ${dossierRows(data.upcoming, data.today)}
            </div>
          </section>
          <section class="panel">
            <div class="panel-head"><h2>截止周历</h2><span class="meta">近 7 天 · 申报中政策</span></div>
            <div class="panel-body">${calendarStrip(data.deadline_calendar, data.today)}
              <div style="margin-top:10px">${chipRow(data.channels.map((item) => ({ label: item.label, count: item.count })))}</div>
              <h3 style="margin:14px 0 6px;font-size:0.95rem">本周窗口提醒</h3>
              ${windowReminders(data.deadline_calendar)}
            </div>
          </section>
        </div>
        <div class="grid-2">
          <section class="panel">
            <div class="panel-head"><h2>待复核匹配（按得分）</h2><span class="meta">点击进入工作台</span></div>
            <div class="panel-body">
              ${
                data.pending_matches.length
                  ? `<div class="todo">${data.pending_matches
                      .map(
                        (item) => `<div class="todo-row" data-match="${item.id}">
                          <span class="p">${esc(item.priority)}</span>
                          <span class="t">${esc(item.company_name)} → ${esc(item.policy_code)} ${esc(item.gaps[0] || '条件满足')}</span>
                          <span class="s">${Number(item.score).toFixed(1)}</span>
                        </div>`,
                      )
                      .join('')}</div>`
                  : emptyState({ title: '没有待复核匹配', hint: '到匹配工作台发起一次运行。' })
              }
            </div>
          </section>
          <section class="panel">
            <div class="panel-head"><h2>优先级 / 复核进度</h2><span class="meta">match</span></div>
            <div class="panel-body">
              ${barList(data.priority)}
              <div style="height:10px"></div>
              ${barList(data.review, 'ok')}
              <p class="muted mono" style="margin:10px 0 0">最近运行：${
                latest ? `${esc(latest.run_no)} · ${esc(ENUMS.runStatus[latest.status] || latest.status)} · 产出 ${latest.match_count} 条（P0 ${latest.p0_count}）` : '尚无'
              }</p>
            </div>
          </section>
        </div>`;
      view.querySelectorAll('[data-policy]').forEach((row) => {
        row.addEventListener('click', () => {
          location.hash = `#/policies?policy_id=${row.dataset.policy}`;
        });
      });
      view.querySelectorAll('[data-match]').forEach((row) => {
        row.addEventListener('click', () => {
          location.hash = `#/matches?match_id=${row.dataset.match}`;
        });
      });
    } catch (err) {
      view.innerHTML = errorBox(errorMessage(err));
      view.querySelector('#retry-btn')?.addEventListener('click', () => overviewPage.render(view, ctx));
    }
  },
};

export default overviewPage;
