import { api } from '../api.js';
import { ENUMS, runTone } from '../config.js';
import { drawer, errorBox, errorMessage, esc, fmtTime, kv, table, toast } from '../ui.js';

async function download(path, filename) {
  try {
    await api.download(path, filename);
    toast('已生成下载文件');
  } catch (err) {
    toast(errorMessage(err), 'err');
  }
}

function openRun(view, run) {
  drawer({
    title: `运行 ${run.run_no}`,
    subtitle: `${fmtTime(run.started_at)} · ${ENUMS.trigger[run.trigger] || run.trigger} · ${run.operator_email}`,
    body: `${kv([
      ['状态', esc(ENUMS.runStatus[run.status] || run.status)],
      ['政策数', esc(run.policy_count)],
      ['企业数', esc(run.company_count)],
      ['进入清单', `${esc(run.match_count)} 条`],
      ['P0', `${esc(run.p0_count)} 条`],
      ['参数', `<span class="mono">${esc(JSON.stringify(run.params || {}))}</span>`],
      ['指标', `<span class="mono">${esc(JSON.stringify(run.metrics || {}))}</span>`],
    ])}
    <h3 style="margin:12px 0 6px;font-size:0.96rem">运行日志</h3>
    <pre class="code">${esc(run.log_text || '（无日志）')}</pre>`,
  });
}

export const exportsPage = {
  async render(view, ctx) {
    let runs;
    try {
      runs = await api.get('/api/match-runs', { limit: 20 });
    } catch (err) {
      view.innerHTML = errorBox(errorMessage(err));
      view.querySelector('#retry-btn')?.addEventListener('click', () => exportsPage.render(view, ctx));
      return;
    }
    const latest = runs.items[0];
    view.innerHTML = `
      <section class="panel">
        <div class="panel-head">
          <h2>申报清单导出</h2>
          <span class="meta">CSV · UTF-8 BOM · Excel 可直接打开</span>
        </div>
        <div class="panel-body export-block">
          <div class="export-note">
            导出列：序号 / 运行编号 / 政策编号与标题 / 发文机关 / 申报截止 / 企业名称 / 行业 / 注册地 /
            营业收入 / 研发占比 / 员工人数 / 匹配得分 / 优先级 / 硬条件 / 缺口提示 / 复核状态 / 复核人 / 备注。
            排序：P0 → P1 → P2，同优先级按得分降序。只导出硬条件全部通过的企业。
          </div>
          <div class="filter-bar">
            <button class="btn accent" id="export-latest">导出本次运行（${latest ? latest.match_count : 0} 条）</button>
            <button class="btn ghost" id="export-all">导出全部匹配结果</button>
            <button class="btn ghost" id="export-policies">导出政策台账 CSV</button>
          </div>
        </div>
        ${table({
          rows: runs.items,
          empty: { title: '还没有匹配运行', hint: '到匹配工作台发起一次。' },
          columns: [
            { key: 'run_no', label: '运行号', className: 'mono' },
            { key: 'status', label: '状态', render: (row) => `<span class="badge ${runTone(row.status)}">${esc(row.status_label)}</span>` },
            { key: 'started_at', label: '开始时间', render: (row) => fmtTime(row.started_at) },
            { key: 'policy_count', label: '政策', className: 'num' },
            { key: 'company_count', label: '企业', className: 'num' },
            { key: 'match_count', label: '清单条数', className: 'num' },
            { key: 'p0_count', label: 'P0', className: 'num' },
            {
              key: 'actions',
              label: '操作',
              render: (row) => `<button class="btn sm ghost" data-export-run="${row.id}">导出 CSV</button>`,
            },
          ],
        })}
      </section>`;
    view.querySelector('#export-latest')?.addEventListener('click', () => {
      if (latest) download(`/api/exports/matches.csv?run_id=${latest.id}`, 'policyfit-matches.csv');
    });
    view.querySelector('#export-all')?.addEventListener('click', () => {
      download('/api/exports/matches.csv', 'policyfit-matches-all.csv');
    });
    view.querySelector('#export-policies')?.addEventListener('click', () => {
      download('/api/exports/policies.csv', 'policyfit-policies.csv');
    });
    view.querySelectorAll('[data-export-run]').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        download(`/api/exports/matches.csv?run_id=${button.dataset.exportRun}`, 'policyfit-matches.csv');
      });
    });
    view.querySelectorAll('table.data tbody tr').forEach((row) => {
      row.addEventListener('click', () => {
        const run = runs.items.find((item) => String(item.id) === row.dataset.id);
        if (run) openRun(view, run);
      });
    });
  },
};

export default exportsPage;
