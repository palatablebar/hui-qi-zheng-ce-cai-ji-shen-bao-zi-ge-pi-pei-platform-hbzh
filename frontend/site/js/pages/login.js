import { api } from '../api.js';
import { session } from '../store.js';
import { BRAND } from '../config.js';
import { errorMessage, esc, redhead, seal, toast } from '../ui.js';

const REGISTER_ROWS = [
  ['收字 2026-101', '园区经发委', '2026 年度专精特新培育资助', '11-18'],
  ['收字 2026-102', '苏州市科技局', '2026 年高新技术企业认定奖励', '11-24'],
  ['收字 2026-103', '园区科创委', '软件和信息服务业成长奖励', '11-26'],
];

export const loginPage = {
  async render(root, ctx) {
    root.className = 'login-host';
    root.innerHTML = `
      <div class="login">
        <section class="login-brief">
          ${redhead({ org: '苏州工业园区企服通', doc: '苏园企服〔2026〕登记第 07 号' })}
          <div class="ledger-title">
            <b>收文登记簿</b>
            <span class="mono muted">RECEIPT&nbsp;REGISTER · 24 条在册</span>
          </div>
          <h1>惠企政策<br /><em>采集与申报资格匹配台</em></h1>
          <p class="tagline">${esc(BRAND.loginLead)}</p>
          <div class="table-wrap">
            <table class="data register">
              <thead><tr><th>登记号</th><th>来文单位</th><th>政策标题</th><th>截止</th></tr></thead>
              <tbody>
                ${REGISTER_ROWS.map(
                  (row) => `<tr><td class="mono">${esc(row[0])}</td><td>${esc(row[1])}</td><td>${esc(row[2])}</td><td class="mono">${esc(row[3])}</td></tr>`,
                ).join('')}
              </tbody>
            </table>
          </div>
          <div class="export-note" style="margin-top:2px">
            登记须知：政策原文入库后由抽取器生成申报条件，置信度低于 0.60 的条件须由政策运营人工确认；
            匹配清单只收录硬条件全部通过的企业，软条件缺口会随清单一起导出。
          </div>
          <div class="brief-points">
            ${BRAND.loginPoints
              .map(([no, text]) => `<div class="brief-point"><i>${esc(no)}</i><span>${esc(text)}</span></div>`)
              .join('')}
          </div>
          <div class="eyebrow">${esc(BRAND.org)} · 内部工作台</div>
        </section>
        <section class="login-form-wrap">
          <form class="login-card" id="login-form" novalidate>
            <div class="redhead left">
              <span class="org">收文登记单</span>
              <span class="doc">FORM PF-01 · 登记人签名生效</span>
            </div>
            <div>
              <div class="brand">${esc(BRAND.title)}</div>
              <div class="sub">用内部账号登记调阅。三个账号权限不同：政策运营可维护台账，政策专员跑匹配复核，客户经理只读（看不到联系人电话）。</div>
            </div>
            <div class="field">
              <label for="email">登记邮箱</label>
              <input id="email" name="email" type="email" autocomplete="username" value="admin@${esc(BRAND.short)}.io" required />
            </div>
            <div class="field">
              <label for="password">登记口令</label>
              <input id="password" name="password" type="password" autocomplete="current-password" value="Demo@2026" required />
            </div>
            <div class="form-error" id="login-error" role="alert"></div>
            <div class="form-row">
              <button class="btn accent" id="login-submit" type="submit">登记并调阅</button>
              ${seal('企服通\n政策服务', true)}
            </div>
            <div class="login-hint">
              演示账号（口令 <code>Demo@2026</code>）：<br />
              <code>admin@${esc(BRAND.short)}.io</code> 政策运营 · <code>analyst@${esc(BRAND.short)}.io</code> 政策专员 ·
              <code>viewer@${esc(BRAND.short)}.io</code> 客户经理
            </div>
          </form>
        </section>
      </div>`;

    const form = root.querySelector('#login-form');
    const errorNode = root.querySelector('#login-error');
    const submit = root.querySelector('#login-submit');
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      errorNode.textContent = '';
      submit.disabled = true;
      submit.textContent = '正在核对…';
      try {
        const result = await api.post('/api/auth/login', {
          email: form.email.value.trim(),
          password: form.password.value,
        });
        session.set(result.access_token, result.user);
        toast(`欢迎回来，${result.user.display_name}`);
        location.hash = '#/overview';
        await ctx.reload();
      } catch (err) {
        errorNode.textContent = err.code === 'AUTH_INVALID' ? '账号或口令不正确' : errorMessage(err);
      } finally {
        submit.disabled = false;
        submit.textContent = '登记并调阅';
      }
    });
  },
};

export default loginPage;
