import { api } from '../api.js';
import { ENUMS, can, priorityTone, reviewTone, runTone } from '../config.js';
import {
  drawer,
  emptyState,
  errorBox,
  errorMessage,
  esc,
  field,
  fmtTime,
  gapList,
  kv,
  scoreBar,
  table,
  toast,
} from '../ui.js';

const state = { runId: '', priority: '', status: '', q: '' };

function scoreParts(payload) {
  const parts = payload?.score_parts || {};
  const hard = payload?.hard || [];
  const soft = payload?.soft || [];
  const hardLines = hard
    .map(
      (item) => `<div class="rule-item">
        <span class="field">${esc(item.label)}</span>
        <span class="expr">${esc(item.op)}</span>
        <span class="expr">${esc(item.expected)}</span>
        <span class="${item.pass ? 'conf' : 'conf low'}">${item.pass ? '通过' : '不通过'}</span>
        <span class="ev">企业实际：${esc(item.actual)}</span>
      </div>`,
    )
    .join('');
  const softLines = soft
    .map(
      (item) => `<div class="rule-item">
        <span class="field">${esc(item.label)}</span>
        <span class="expr">${esc(item.op)}</span>
        <span class="expr">${esc(item.expected)}${item.field === 'revenue_wan' ? ' 万' : item.field === 'rd_ratio' ? '%' : item.field === 'employees' ? ' 人' : ''}</span>
        <span class="${item.pass ? 'conf' : 'conf low'}">余量 ${item.margin === null ? '—' : Number(item.margin).toFixed(3)}</span>
        <span class="ev">企业实际：${esc(item.actual)} · 单条得分 ${Number(item.score || 0).toFixed(2)}</span>
      </div>`,
    )
    .join('');
  return `<div class="meta-line" style="border-top-width:2px">
      <div class="cell"><span class="k">硬条件系数</span><span class="v">${Number(parts.hard_ratio ?? 0).toFixed(2)}</span></div>
      <div class="cell"><span class="k">软条件得分</span><span class="v">${Number(parts.soft_score ?? 0).toFixed(2)}</span></div>
      <div class="cell"><span class="k">截止分</span><span class="v">${Number(parts.deadline_score ?? 0).toFixed(1)}</span></div>
    </div>
    <h3 style="margin:12px 0 6px;font-size:0.96rem">硬条件（行业 / 注册地 / 资质 / 截止）</h3>
    <div class="rule-list">${hardLines || '<div class="rule-item">该政策没有硬条件</div>'}</div>
    <h3 style="margin:12px 0 6px;font-size:0.96rem">软条件（余量）</h3>
    <div class="rule-list">${softLines || '<div class="rule-item">该政策没有软条件</div>'}</div>`;
}

function openMatch(view, ctx, item) {
  const canReview = can(ctx.user.role, 'match:review');
  const payload = item.payload || {};
  const { root, close } = drawer({
    title: `${item.company_name} → ${item.policy_title}`,
    subtitle: `${item.policy_code} · 得分 ${Number(item.score).toFixed(1)} · ${item.priority_label}`,
    body: `${kv([
      ['匹配得分', scoreBar(item.score)],
      ['优先级', `<span class="badge ${priorityTone(item.priority)}">${esc(item.priority_label)}</span>`],
      ['硬条件', item.hard_pass ? '<span class="badge ok">全部通过</span>' : '<span class="badge danger">未通过</span>'],
      ['申报截止', esc(item.policy_deadline || '—')],
      ['企业行业/注册地', `${esc(item.company_industry)} / ${esc(item.company_district)}`],
      ['复核状态', `<span class="badge ${reviewTone(item.status)}">${esc(item.status_label)}</span>`],
      ['复核人', esc(item.reviewer || '—')],
      ['复核备注', esc(item.note || '—')],
      ['生成时间', fmtTime(item.created_at)],
    ])}
    <h3 style="margin:12px 0 6px;font-size:0.96rem">缺口提示</h3>
    ${gapList(item.gaps)}
    ${scoreParts(payload)}`,
    footer: canReview
      ? `<form id="review-form" style="display:grid;gap:10px">
          ${field({ label: '复核结论', name: 'status', value: item.status, options: Object.entries(ENUMS.review).map(([value, label]) => ({ value, label })) })}
          ${field({ label: '备注（写清判定依据）', name: 'note', value: item.note || '', placeholder: '例如：研发占比差 0.2pt，建议补强后再报' })}
          <button class="btn accent" type="submit">提交复核</button>
        </form>`
      : '<span class="mono muted">客户经理为只读角色，不能复核（后端返回 403）</span>',
  });
  root.querySelector('#review-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.target;
    try {
      await api.patch(`/api/matches/${item.id}/review`, {
        status: form.status.value,
        note: form.note.value.trim() || null,
      });
      toast('复核结果已入卷');
      close();
      await matchesPage.render(view, ctx);
    } catch (err) {
      toast(errorMessage(err), 'err');
    }
  });
}

function openRunForm(view, ctx, policies, latestRun) {
  const active = policies.filter((item) => item.status === 'active');
  const { root, close } = drawer({
    title: '发起一次资格匹配',
    subtitle: '算法在服务端执行：硬条件布尔 + 软条件余量 + 截止分',
    body: `<form id="match-run-form" style="display:grid;gap:11px">
      ${field({
        label: '政策范围',
        name: 'policy_code',
        options: [{ value: '', label: `全部申报中政策（${active.length} 条）` }, ...active.map((item) => ({ value: item.code, label: `${item.code} ${item.title}` }))],
      })}
      <p class="mono muted">当前企业池 120 家；只把硬条件全部通过的企业写入申报清单。</p>
      <div class="form-error" id="run-error"></div>
      <button class="btn accent" type="submit">开始匹配</button>
    </form>`,
  });
  root.querySelector('#match-run-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.target;
    const button = form.querySelector('button[type=submit]');
    button.disabled = true;
    button.textContent = '匹配中…';
    try {
      const run = await api.post('/api/match-runs', {
        trigger: 'manual',
        policy_codes: form.policy_code.value ? [form.policy_code.value] : [],
      });
      toast(`运行 ${run.run_no} 完成：进入清单 ${run.match_count} 条，P0 ${run.p0_count} 条`);
      close();
      state.runId = String(run.id);
      await matchesPage.render(view, ctx);
    } catch (err) {
      root.querySelector('#run-error').textContent = errorMessage(err);
      button.disabled = false;
      button.textContent = '开始匹配';
    }
  });
}

export const matchesPage = {
  async render(view, ctx) {
    let runs;
    let policies;
    try {
      [runs, policies] = await Promise.all([
        api.get('/api/match-runs', { limit: 10 }),
        api.get('/api/policies', { limit: 50 }),
      ]);
    } catch (err) {
      view.innerHTML = errorBox(errorMessage(err));
      view.querySelector('#retry-btn')?.addEventListener('click', () => matchesPage.render(view, ctx));
      return;
    }
    const latest = runs.items[0];
    if (!state.runId && latest) state.runId = String(latest.id);
    let data;
    try {
      data = await api.get('/api/matches', {
        run_id: state.runId,
        priority: state.priority,
        status: state.status,
        q: state.q,
        limit: 60,
      });
    } catch (err) {
      view.innerHTML = errorBox(errorMessage(err));
      view.querySelector('#retry-btn')?.addEventListener('click', () => matchesPage.render(view, ctx));
      return;
    }
    const current = runs.items.find((item) => String(item.id) === String(state.runId)) || latest;
    view.innerHTML = `
      <section class="panel">
        <div class="panel-head">
          <h2>匹配工作台</h2>
          <div style="display:flex;gap:8px;align-items:center">
            <span class="meta">${data.total} 条结果</span>
            ${can(ctx.user.role, 'match:run') ? '<button class="btn sm accent" id="new-match-run">发起匹配</button>' : ''}
          </div>
        </div>
        <div class="panel-body">
          <div class="meta-line" style="border-top-width:2px">
            <div class="cell"><span class="k">运行号</span><span class="v" style="font-size:0.95rem">${esc(current ? current.run_no : '—')}</span><span class="hint">${current ? esc(ENUMS.trigger[current.trigger] || current.trigger) : ''}</span></div>
            <div class="cell"><span class="k">政策 × 企业</span><span class="v">${current ? `${current.policy_count} × ${current.company_count}` : '—'}</span></div>
            <div class="cell"><span class="k">进入清单</span><span class="v">${current ? current.match_count : 0}<small>条</small></span><span class="hint">硬条件全过</span></div>
            <div class="cell"><span class="k">P0</span><span class="v">${current ? current.p0_count : 0}<small>条</small></span><span class="hint">7 天内截止</span></div>
            <div class="cell"><span class="k">平均分</span><span class="v">${current && current.metrics ? Number(current.metrics.avg_score || 0).toFixed(1) : '—'}</span></div>
          </div>
          <div class="filter-bar" id="match-filters" style="margin-top:12px">
            ${field({ label: '运行', name: 'run_id', value: state.runId, options: runs.items.map((item) => ({ value: item.id, label: `${item.run_no} · ${item.match_count} 条` })) })}
            ${field({ label: '优先级', name: 'priority', value: state.priority, options: [{ value: '', label: '全部' }, ...Object.entries(ENUMS.priority).map(([value, label]) => ({ value, label }))] })}
            ${field({ label: '复核状态', name: 'status', value: state.status, options: [{ value: '', label: '全部' }, ...Object.entries(ENUMS.review).map(([value, label]) => ({ value, label }))] })}
            ${field({ label: '搜索', name: 'q', value: state.q, placeholder: '企业 / 政策' })}
          </div>
        </div>
        ${table({
          rows: data.items,
          empty: { title: '这次运行没有进入清单的企业', hint: '换一个政策范围，或检查企业画像是否补齐。' },
          columns: [
            { key: 'company_name', label: '企业', render: (row) => `<b>${esc(row.company_name)}</b><div class="mono muted">${esc(row.company_industry)} / ${esc(row.company_district)}</div>` },
            { key: 'policy_code', label: '政策', render: (row) => `<span class="mono">${esc(row.policy_code)}</span><div class="muted">${esc(row.policy_title)}</div>` },
            { key: 'score', label: '得分', render: (row) => scoreBar(row.score) },
            { key: 'priority', label: '优先级', render: (row) => `<span class="badge ${priorityTone(row.priority)}">${esc(row.priority_label)}</span>` },
            { key: 'gaps', label: '缺口', render: (row) => (row.gaps.length ? `<span style="color:var(--danger)">${esc(row.gaps[0])}</span>` : '<span class="badge ok">满足</span>') },
            { key: 'status', label: '复核', render: (row) => `<span class="badge ${reviewTone(row.status)}">${esc(row.status_label)}</span>` },
            { key: 'policy_deadline', label: '截止', className: 'mono', render: (row) => esc(row.policy_deadline || '—') },
          ],
        })}
      </section>`;
    const filters = view.querySelector('#match-filters');
    filters?.addEventListener('change', () => {
      state.runId = filters.querySelector('[name=run_id]').value;
      state.priority = filters.querySelector('[name=priority]').value;
      state.status = filters.querySelector('[name=status]').value;
      state.q = filters.querySelector('[name=q]').value.trim();
      matchesPage.render(view, ctx);
    });
    view.querySelectorAll('table.data tbody tr').forEach((row) => {
      row.addEventListener('click', () => {
        const item = data.items.find((entry) => String(entry.id) === row.dataset.id);
        if (item) openMatch(view, ctx, item);
      });
    });
    view.querySelector('#new-match-run')?.addEventListener('click', () => openRunForm(view, ctx, policies.items, current));

    if (ctx.query.match_id) {
      try {
        const detail = await api.get(`/api/matches/${ctx.query.match_id}`);
        openMatch(view, ctx, detail);
      } catch {
        /* 忽略打开失败 */
      }
    }
  },
};

export default matchesPage;
