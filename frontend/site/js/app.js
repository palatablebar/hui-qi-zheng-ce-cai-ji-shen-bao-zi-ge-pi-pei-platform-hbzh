import { api } from './api.js';
import { BRAND, NAV, ROLE_LABELS, can } from './config.js';
import { session } from './store.js';
import { errorMessage, esc, toast } from './ui.js';
import loginPage from './pages/login.js';
import overviewPage from './pages/overview.js';
import policiesPage from './pages/policies.js';
import companiesPage from './pages/companies.js';
import matchesPage from './pages/matches.js';
import exportsPage from './pages/exports.js';
import auditPage from './pages/audit.js';

const routes = [
  { path: '#/overview', page: overviewPage, permission: 'overview:read' },
  { path: '#/policies', page: policiesPage, permission: 'policy:read' },
  { path: '#/companies', page: companiesPage, permission: 'company:read' },
  { path: '#/matches', page: matchesPage, permission: 'match:read' },
  { path: '#/exports', page: exportsPage, permission: 'export:read' },
  { path: '#/audit', page: auditPage, permission: 'audit:read' },
];

let currentUser = null;
let listening = false;

function setActiveNav(path) {
  document.querySelectorAll('.rail nav a').forEach((link) => {
    link.classList.toggle('active', link.getAttribute('href') === path);
  });
}

function forbidden(view, ctx) {
  view.innerHTML = `<section class="panel"><div class="empty" data-testid="forbidden">
    <div class="mark">这一卷不在你的调阅范围</div>
    <p>当前角色是「${esc(ROLE_LABELS[ctx.user.role] || ctx.user.role)}」，该模块需要更高权限（后端返回 403）。</p>
    <button class="btn ghost" data-back>回到总览目录</button>
  </div></section>`;
  view.querySelector('[data-back]')?.addEventListener('click', () => {
    location.hash = '#/overview';
  });
}

async function renderLogin() {
  currentUser = null;
  const root = document.getElementById('app');
  root.className = '';
  await loginPage.render(root, { reload: boot });
}

async function renderRoute() {
  const view = document.getElementById('view');
  if (!view || !currentUser) return;
  const raw = location.hash || '#/overview';
  const [path, qs] = raw.split('?');
  const query = Object.fromEntries(new URLSearchParams(qs || ''));
  if (path === '#/login') {
    session.clear();
    return renderLogin();
  }
  const route = routes.find((item) => item.path === path) || routes[0];
  if (!can(currentUser.role, route.permission)) {
    setActiveNav('');
    return forbidden(view, { user: currentUser });
  }
  setActiveNav(route.path);
  view.innerHTML = '<div class="empty"><div class="mark">正在调阅…</div></div>';
  const ctx = {
    user: currentUser,
    query,
    navigate: (hash) => {
      location.hash = hash;
    },
    reload: boot,
    logout,
  };
  try {
    await route.page.render(view, ctx);
  } catch (err) {
    view.innerHTML = `<div class="error-box"><span>${esc(errorMessage(err))}</span><button class="btn sm ghost" data-retry>重试</button></div>`;
    view.querySelector('[data-retry]')?.addEventListener('click', () => renderRoute());
  }
}

function logout() {
  session.clear();
  toast('已退出登记簿');
  location.hash = '#/login';
  boot();
}

function renderShell() {
  const root = document.getElementById('app');
  root.className = '';
  const navItems = NAV.filter((item) => can(currentUser.role, item.permission));
  root.innerHTML = `
    <div class="shell">
      <aside class="rail">
        <div class="rail-mark">
          <b>企服通</b>
          <small>POLICY&nbsp;REGISTER</small>
        </div>
        <nav>
          ${navItems
            .map(
              (item) =>
                `<a href="${item.to}" data-nav="${item.to.replace('#/', '')}" data-testid="nav-${item.to.replace('#/', '')}"><i>${item.no}</i>${esc(item.label)}</a>`,
            )
            .join('')}
        </nav>
        <div class="rail-foot">
          <b>${esc(BRAND.org)}</b>
          <span>${esc(ROLE_LABELS[currentUser.role] || currentUser.role)} · ${esc(currentUser.display_name)}</span>
          <span class="mono" id="worker-state" data-testid="worker-state">后台任务 · 检测中</span>
          <button class="btn sm ghost" id="logout" style="margin-top:6px">退出登录</button>
        </div>
      </aside>
      <div class="main">
        <header class="topbar">
          <div>
            <div class="eyebrow">${esc(BRAND.edition)} · 政策服务台账</div>
            <h1>${esc(BRAND.title)}</h1>
            <div class="sub">${esc(BRAND.subtitle)}</div>
          </div>
          <div class="topbar-meta">
            <div class="who">
              <b data-testid="who-name">${esc(currentUser.display_name)}</b>
              <div class="tiny mono">${esc(currentUser.email)}</div>
            </div>
          </div>
        </header>
        <section class="view" id="view"></section>
      </div>
    </div>`;
  root.querySelector('#logout')?.addEventListener('click', logout);
  api
    .get('/api/overview')
    .then((data) => {
      const node = document.getElementById('worker-state');
      if (node) node.textContent = data.worker_alive ? '后台任务 · 在岗' : '后台任务 · 心跳超时';
    })
    .catch(() => {});
}

async function boot() {
  if (!listening) {
    window.addEventListener('hashchange', () => {
      if (!session.token()) return renderLogin();
      renderRoute();
    });
    listening = true;
  }
  if (!session.token()) return renderLogin();
  try {
    const me = await api.get('/api/auth/me');
    currentUser = me.user;
    session.setUser(me.user);
  } catch {
    session.clear();
    return renderLogin();
  }
  renderShell();
  await renderRoute();
}

boot();
