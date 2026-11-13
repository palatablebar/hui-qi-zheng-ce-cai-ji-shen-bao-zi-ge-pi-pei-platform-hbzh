import { api } from '../api.js';
import { ENUMS, can, policyTone } from '../config.js';
import {
  drawer,
  emptyState,
  errorBox,
  errorMessage,
  esc,
  field,
  fmtTime,
  kv,
  redhead,
  ruleList,
  table,
  toast,
} from '../ui.js';

const state = { q: '', status: '', channel: '' };

function openPolicy(view, ctx, policy) {
  const canExtract = can(ctx.user.role, 'rule:extract');
  const rules = policy.rules || [];
  const { root, close } = drawer({
    title: policy.title,
    subtitle: `${policy.code} · ${policy.doc_no}`,
    body: `${redhead({ org: policy.issuer, doc: `${policy.doc_no} · 收文渠道 ${policy.source_name}`, left: true })}
      ${kv([
        ['状态', `<span class="badge ${policyTone(policy.status)}">${esc(policy.status_label)}</span>`],
        ['发文机关', esc(policy.issuer)],
        ['发布日期', fmtTime(policy.published_on)],
        ['申报截止', `<b>${esc(policy.deadline || '未定')}</b>`],
        ['资助上限', policy.fund_cap_wan ? `${esc(policy.fund_cap_wan)} 万元` : '—'],
        ['条件 / 低置信', `${policy.rules_total ?? rules.length} 条 / <b style="color:var(--seal)">${policy.low_confidence_total ?? rules.filter((r) => r.confidence < 0.6).length} 条</b>`],
      ])}
      <h3 style="margin:14px 0 6px;font-size:0.98rem">政策原文</h3>
      <div class="doc-text">${esc(policy.original_text)}</div>
      <h3 style="margin:14px 0 6px;font-size:0.98rem">申报条件（置信度 &lt; 0.60 需人工确认）</h3>
      ${ruleList(rules)}`,
    footer: canExtract
      ? `<button class="btn accent" data-extract>重新抽取申报条件</button>`
      : '<span class="mono muted">只读角色可查看条件，不能抽取</span>',
  });
  root.querySelector('[data-extract]')?.addEventListener('click', async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    button.textContent = '抽取中…';
    try {
      const result = await api.post(`/api/policies/${policy.id}/extract-rules`, {});
      toast(`抽取完成：${result.rules.length} 条条件，低置信 ${result.low_confidence.length} 条，无法解析 ${result.unparsed.length} 句`);
      close();
      await policiesPage.render(view, ctx);
    } catch (err) {
      toast(errorMessage(err), 'err');
      button.disabled = false;
      button.textContent = '重新抽取申报条件';
    }
  });
}

function openCreate(view, ctx) {
  const { root, close } = drawer({
    title: '登记新政策',
    subtitle: '原文入库后可立即抽取申报条件',
    body: `<form id="policy-form" style="display:grid;gap:11px">
      ${field({ label: '政策编号（大写字母/数字）', name: 'code', placeholder: 'P2026-XXXX' })}
      ${field({ label: '标题', name: 'title', placeholder: '例如：2026 年度专精特新培育资助' })}
      ${field({ label: '发文机关', name: 'issuer', placeholder: '苏州工业园区经济发展委员会' })}
      ${field({ label: '文号', name: 'doc_no', placeholder: '苏园经发〔2026〕18 号' })}
      ${field({ label: '采集渠道', name: 'source_kind', value: 'website', options: Object.entries(ENUMS.channel).map(([value, label]) => ({ value, label })) })}
      ${field({ label: '申报截止', name: 'deadline', type: 'date' })}
      ${field({ label: '资助上限（万元）', name: 'fund_cap_wan', type: 'number' })}
      <div class="field"><label for="original_text">政策原文</label><textarea id="original_text" name="original_text" rows="5" placeholder="粘贴通知正文，抽取器会识别营业收入、研发占比、注册地、资质与截止日"></textarea></div>
      <div class="form-error" id="policy-error"></div>
      <button class="btn accent" type="submit">登记入库</button>
    </form>`,
  });
  root.querySelector('#policy-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.target;
    try {
      const created = await api.post('/api/policies', {
        code: form.code.value.trim(),
        title: form.title.value.trim(),
        issuer: form.issuer.value.trim(),
        doc_no: form.doc_no.value.trim() || null,
        source_kind: form.source_kind.value,
        deadline: form.deadline.value || null,
        fund_cap_wan: form.fund_cap_wan.value ? Number(form.fund_cap_wan.value) : null,
        original_text: form.original_text.value.trim(),
        status: 'active',
      });
      await api.post(`/api/policies/${created.id}/extract-rules`, {});
      toast('政策已登记并完成条件抽取');
      close();
      await policiesPage.render(view, ctx);
    } catch (err) {
      root.querySelector('#policy-error').textContent =
        err.code === 'CONFLICT' ? '政策编号已存在' : errorMessage(err);
    }
  });
}

export const policiesPage = {
  async render(view, ctx) {
    let data;
    try {
      data = await api.get('/api/policies', {
        q: state.q,
        status: state.status,
        channel: state.channel,
        limit: 50,
      });
    } catch (err) {
      view.innerHTML = errorBox(errorMessage(err));
      view.querySelector('#retry-btn')?.addEventListener('click', () => policiesPage.render(view, ctx));
      return;
    }
    view.innerHTML = `
      <section class="panel">
        <div class="panel-head">
          <h2>政策库</h2>
          <div style="display:flex;gap:8px;align-items:center">
            <span class="meta">${data.total} 件在册</span>
            ${can(ctx.user.role, 'policy:write') ? '<button class="btn sm accent" id="new-policy">登记政策</button>' : ''}
          </div>
        </div>
        <div class="panel-body">
          <div class="filter-bar" id="policy-filters">
            ${field({ label: '搜索', name: 'q', value: state.q, placeholder: '标题 / 编号 / 文号' })}
            ${field({ label: '状态', name: 'status', value: state.status, options: [{ value: '', label: '全部' }, ...Object.entries(ENUMS.policyStatus).map(([value, label]) => ({ value, label }))] })}
            ${field({ label: '采集渠道', name: 'channel', value: state.channel, options: [{ value: '', label: '全部' }, ...Object.entries(ENUMS.channel).map(([value, label]) => ({ value, label }))] })}
            <div class="spacer"></div>
          </div>
        </div>
        ${table({
          rows: data.items,
          empty: { title: '政策库为空', hint: '政策运营可以登记第一条政策。' },
          columns: [
            { key: 'code', label: '编号', className: 'mono' },
            {
              key: 'title',
              label: '政策标题',
              render: (row) => `<b>${esc(row.title)}</b><div class="mono muted">${esc(row.doc_no)}</div>`,
            },
            { key: 'issuer', label: '发文机关' },
            { key: 'source_name', label: '采集渠道' },
            { key: 'deadline', label: '申报截止', className: 'mono', render: (row) => esc(row.deadline || '未定') },
            {
              key: 'rules_total',
              label: '条件',
              className: 'num',
              render: (row) =>
                `${row.rules_total} 条${row.low_confidence_total ? `<span class="badge p0" style="margin-left:6px">低置信 ${row.low_confidence_total}</span>` : ''}`,
            },
            {
              key: 'status',
              label: '状态',
              render: (row) => `<span class="badge ${policyTone(row.status)}">${esc(row.status_label)}</span>`,
            },
          ],
        })}
      </section>`;

    const filters = view.querySelector('#policy-filters');
    filters?.addEventListener('change', () => {
      state.q = filters.querySelector('[name=q]').value.trim();
      state.status = filters.querySelector('[name=status]').value;
      state.channel = filters.querySelector('[name=channel]').value;
      policiesPage.render(view, ctx);
    });
    filters?.querySelector('[name=q]')?.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        state.q = event.target.value.trim();
        policiesPage.render(view, ctx);
      }
    });
    view.querySelectorAll('table.data tbody tr').forEach((row) => {
      row.addEventListener('click', async () => {
        const item = data.items.find((entry) => String(entry.id) === row.dataset.id);
        if (!item) return;
        try {
          const detail = await api.get(`/api/policies/${item.id}`);
          openPolicy(view, ctx, detail);
        } catch (err) {
          toast(errorMessage(err), 'err');
        }
      });
    });
    view.querySelector('#new-policy')?.addEventListener('click', () => openCreate(view, ctx));

    if (ctx.query.policy_id) {
      try {
        const detail = await api.get(`/api/policies/${ctx.query.policy_id}`);
        openPolicy(view, ctx, detail);
      } catch {
        /* 打开失败时保留列表 */
      }
    }
  },
};

export default policiesPage;
