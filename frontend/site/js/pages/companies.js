import { api } from '../api.js';
import { can } from '../config.js';
import { drawer, errorBox, errorMessage, esc, field, kv, table, toast } from '../ui.js';

const state = { q: '', industry: '', district: '', qualification: '' };

function openCompany(view, ctx, company) {
  const editable = can(ctx.user.role, 'company:write');
  const { root, close } = drawer({
    title: company.name,
    subtitle: `${company.code} · ${company.industry} / ${company.district}`,
    body: `${kv([
      ['所属行业', esc(company.industry)],
      ['注册地', esc(company.district)],
      ['营业收入', `${Number(company.revenue_wan).toLocaleString('zh-CN')} 万元`],
      ['研发占比', `<b>${Number(company.rd_ratio).toFixed(1)}%</b>`],
      ['员工人数', `${esc(company.employees)} 人`],
      ['企业资质', (company.qualifications || []).length ? (company.qualifications || []).map((q) => `<span class="badge info">${esc(q)}</span>`).join(' ') : '—'],
      ['联系人电话', company.contact_masked ? '<span class="mono muted">***（只读角色不可见）</span>' : `<span class="mono">${esc(company.contact)}</span>`],
      ['客户经理', esc(company.owner)],
    ])}
    ${
      editable
        ? `<form id="company-form" style="display:grid;gap:10px;border-top:1px dashed var(--rule-strong);padding-top:12px">
            ${field({ label: '营业收入（万元）', name: 'revenue_wan', type: 'number', value: company.revenue_wan })}
            ${field({ label: '研发占比（%）', name: 'rd_ratio', type: 'number', value: company.rd_ratio })}
            ${field({ label: '员工人数', name: 'employees', type: 'number', value: company.employees })}
            <button class="btn accent" type="submit">更新画像</button>
          </form>`
        : '<span class="mono muted">只读角色不能修改企业画像</span>'
    }`,
  });
  root.querySelector('#company-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.target;
    try {
      await api.patch(`/api/companies/${company.id}`, {
        revenue_wan: Number(form.revenue_wan.value),
        rd_ratio: Number(form.rd_ratio.value),
        employees: Number(form.employees.value),
      });
      toast('企业画像已更新');
      close();
      await companiesPage.render(view, ctx);
    } catch (err) {
      toast(errorMessage(err), 'err');
    }
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
          <span class="meta">${data.total} 家在册 · 联系人电话仅政策运营/专员可见</span>
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
            { key: 'name', label: '企业名称', render: (row) => `<b>${esc(row.name)}</b><div class="mono muted">${esc(row.code)}</div>` },
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
