import { api } from '../api.js';
import {
  ENUMS,
  can,
  correctionSourceTone,
  correctionStatusTone,
  CORRECTION_FIELD_OPTIONS,
} from '../config.js';
import { drawer, errorBox, errorMessage, esc, field, fmtTime, table, toast } from '../ui.js';

const state = { q: '', industry: '', district: '', qualification: '' };

function valueText(value) {
  if (value === null || value === undefined || value === '') return '—';
  return esc(value);
}

function correctionTimeline(items, canVerify) {
  if (!items || items.length === 0) {
    return '<div class="empty"><div class="mark">暂无更正留痕</div><p>该企业画像还没有收到过工商回传、客户补录或年报核对。</p></div>';
  }
  return `<div class="correction-list">${items
    .map(
      (c) => `<article class="correction-card" data-correction-id="${c.id}">
        <div class="correction-head">
          <span class="badge ${correctionStatusTone(c.status)}">${esc(c.status_label)}</span>
          <span class="badge ${correctionSourceTone(c.source)}">${esc(c.source_label)}</span>
          <b>${esc(c.field_label)}</b>
          <span class="mono muted">${fmtTime(c.received_at)}</span>
        </div>
        <div class="correction-flow">
          <span class="old">${valueText(c.old_value)}</span>
          <i>→</i>
          <span class="new">${valueText(c.new_value)}</span>
        </div>
        <div class="correction-meta">
          <span>来源单号：${esc(c.source_ref || '—')} · 可信度 ${Number(c.trust_level).toFixed(2)}</span>
          <span>提交人：${esc(c.submitted_by || '—')}</span>
        </div>
        ${c.note ? `<p class="correction-note">${esc(c.note)}</p>` : ''}
        ${
          c.verified_at
            ? `<p class="correction-note muted">核验：${esc(c.verified_by || '—')} · ${fmtTime(c.verified_at)}${c.verify_note ? ` · ${esc(c.verify_note)}` : ''}</p>`
            : ''
        }
        ${
          c.impact && c.impact.summary
            ? `<p class="correction-impact">影响：${esc(c.impact.summary)}</p>`
            : ''
        }
        ${
          canVerify && c.status === 'pending'
            ? `<div class="correction-actions">
                <button class="btn sm accent" data-verify="${c.id}">核验通过（入画像）</button>
                <button class="btn sm ghost" data-reject="${c.id}">驳回</button>
              </div>`
            : ''
        }
      </article>`,
    )
    .join('')}</div>`;
}

function openCompany(view, ctx, company) {
  const editable = can(ctx.user.role, 'company:write');
  const { root, close } = drawer({
    title: company.name,
    subtitle: `${company.code} · ${company.industry} / ${company.district}`,
    body: `
      <div id="company-summary">
        ${
          company.pending_corrections
            ? `<div class="pending-banner" data-testid="pending-banner">该企业有 <b>${company.pending_corrections}</b> 条画像更正待核验；待核验值不参与匹配。</div>`
            : '<div class="pending-banner ok">画像指标均已核验，无待处理更正。</div>'
        }
        ${table({
          rows: [company],
          columns: [
            { key: 'industry', label: '所属行业' },
            { key: 'district', label: '注册地' },
            {
              key: 'revenue_wan',
              label: '营业收入(万)',
              render: (r) => Number(r.revenue_wan).toLocaleString('zh-CN'),
            },
            { key: 'rd_ratio', label: '研发占比', render: (r) => `${Number(r.rd_ratio).toFixed(1)}%` },
            { key: 'employees', label: '员工人数' },
            {
              key: 'qualifications',
              label: '资质',
              render: (r) => (r.qualifications || []).map((q) => `<span class="badge info">${esc(q)}</span>`).join(' ') || '—',
            },
          ],
        })}
      </div>

      ${
        editable
          ? `<form id="correction-form" class="correction-form">
              <h3>提交画像更正（先留痕，核验通过才入画像）</h3>
              <div class="filter-bar">
                ${field({ label: '更正字段', name: 'field', value: 'rd_ratio', options: CORRECTION_FIELD_OPTIONS })}
                ${field({
                  label: '来源',
                  name: 'source',
                  value: 'registry',
                  options: Object.entries(ENUMS.correctionSource).map(([value, label]) => ({ value, label })),
                })}
              </div>
              <div class="filter-bar">
                ${field({ label: '新值（资质用顿号/逗号分隔多项）', name: 'new_value', placeholder: '如 3.4 或 高新技术企业、专精特新' })}
                ${field({ label: '来源单号 / 批次', name: 'source_ref', placeholder: '如 工商回传批次 GS-20261109' })}
              </div>
              ${field({ label: '备注', name: 'note', placeholder: '记录差异原因与核对口径' })}
              <div class="form-error" id="correction-error"></div>
              <button class="btn accent" type="submit">提交更正（待核验）</button>
            </form>`
          : '<span class="mono muted">只读角色不能提交画像更正（后端返回 403）</span>'
      }

      <h3 style="margin:16px 0 8px;font-size:0.96rem">更正留痕（来源 / 收到时间 / 确认状态）</h3>
      <div id="correction-timeline"><div class="empty"><div class="mark">加载中…</div></div></div>`,
  });

  async function loadTimeline() {
    const data = await api.get(`/api/companies/${company.id}/corrections`);
    root.querySelector('#correction-timeline').innerHTML = correctionTimeline(data.items, editable);
    bindVerifyActions();
  }

  async function verify(id, action, note) {
    await api.patch(`/api/corrections/${id}/${action}`, { note: note || null });
    toast(action === 'verify' ? '已核验，新值进入画像并作用于下一次匹配' : '已驳回，该值不进入画像');
    await loadTimeline();
    await companiesPage.render(view, ctx);
  }

  function bindVerifyActions() {
    root.querySelectorAll('[data-verify],[data-reject]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.verify || btn.dataset.reject;
        const action = btn.dataset.verify ? 'verify' : 'reject';
        const note = prompt(action === 'verify' ? '核验备注（可留空）：' : '驳回原因（可留空）：') || '';
        try {
          await verify(id, action, note.trim());
        } catch (err) {
          toast(errorMessage(err), 'err');
        }
      });
    });
  }

  root.querySelector('#correction-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.target;
    const body = {
      field: form.field.value,
      new_value: form.new_value.value.trim(),
      source: form.source.value,
      source_ref: form.source_ref.value.trim(),
      note: form.note.value.trim() || null,
    };
    if (!body.new_value) {
      root.querySelector('#correction-error').textContent = '请填写更正新值';
      return;
    }
    try {
      await api.post(`/api/corrections/company/${company.id}`, body);
      toast('更正已留痕，状态为待核验');
      close();
      await companiesPage.render(view, ctx);
    } catch (err) {
      root.querySelector('#correction-error').textContent = errorMessage(err);
    }
  });

  loadTimeline().catch((err) => {
    root.querySelector('#correction-timeline').innerHTML = errorBox(errorMessage(err));
  });
}

export const companiesPage = {
  async render(view, ctx) {
    let data;
    let options;
    try {
      [data, options] = await Promise.all([
        api.get('/api/companies', {
          q: state.q,
          industry: state.industry,
          district: state.district,
          qualification: state.qualification,
          limit: 60,
        }),
        api.get('/api/overview/options'),
      ]);
    } catch (err) {
      view.innerHTML = errorBox(errorMessage(err));
      view.querySelector('#retry-btn')?.addEventListener('click', () => companiesPage.render(view, ctx));
      return;
    }
    view.innerHTML = `
      <section class="panel">
        <div class="panel-head">
          <h2>企业画像</h2>
          <span class="meta">${data.total} 家在册 · 待核验更正 ${data.pending_total || 0} 条 · 联系人电话仅政策运营/专员可见</span>
        </div>
        <div class="panel-body">
          <div class="filter-bar" id="company-filters">
            ${field({ label: '搜索', name: 'q', value: state.q, placeholder: '企业名称 / 编号' })}
            ${field({ label: '行业', name: 'industry', value: state.industry, options: [{ value: '', label: '全部' }, ...options.industries.map((v) => ({ value: v, label: v }))] })}
            ${field({ label: '注册地', name: 'district', value: state.district, options: [{ value: '', label: '全部' }, ...options.districts.map((v) => ({ value: v, label: v }))] })}
            ${field({ label: '资质', name: 'qualification', value: state.qualification, options: [{ value: '', label: '全部' }, ...options.qualifications.map((v) => ({ value: v, label: v }))] })}
            <div class="spacer"></div>
          </div>
        </div>
        ${table({
          rows: data.items,
          empty: { title: '没有符合条件的企业', hint: '放宽筛选或先在匹配工作台看结果。' },
          columns: [
            {
              key: 'name',
              label: '企业名称',
              render: (row) => `<b>${esc(row.name)}</b>
                <div class="mono muted">${esc(row.code)}</div>
                ${row.pending_corrections ? `<span class="badge warn" data-testid="row-pending">待核验 ${row.pending_corrections}</span>` : ''}`,
            },
            { key: 'industry', label: '行业' },
            { key: 'district', label: '注册地' },
            { key: 'revenue_wan', label: '营业收入(万)', className: 'num', render: (row) => Number(row.revenue_wan).toLocaleString('zh-CN') },
            { key: 'rd_ratio', label: '研发占比', className: 'num', render: (row) => `${Number(row.rd_ratio).toFixed(1)}%` },
            { key: 'employees', label: '员工', className: 'num' },
            { key: 'qualifications', label: '资质', render: (row) => (row.qualifications || []).map((q) => `<span class="badge">${esc(q)}</span>`).join(' ') || '—' },
            { key: 'contact', label: '联系电话', className: 'mono', render: (row) => (row.contact_masked ? '***' : esc(row.contact)) },
          ],
        })}
      </section>`;
    const filters = view.querySelector('#company-filters');
    filters?.addEventListener('change', () => {
      state.q = filters.querySelector('[name=q]').value.trim();
      state.industry = filters.querySelector('[name=industry]').value;
      state.district = filters.querySelector('[name=district]').value;
      state.qualification = filters.querySelector('[name=qualification]').value;
      companiesPage.render(view, ctx);
    });
    filters?.querySelector('[name=q]')?.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        state.q = event.target.value.trim();
        companiesPage.render(view, ctx);
      }
    });
    view.querySelectorAll('table.data tbody tr').forEach((row) => {
      row.addEventListener('click', () => {
        const item = data.items.find((entry) => String(entry.id) === row.dataset.id);
        if (item) openCompany(view, ctx, item);
      });
    });
  },
};

export default companiesPage;
