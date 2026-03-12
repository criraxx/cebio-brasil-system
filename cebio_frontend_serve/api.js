// ============================================================
// CEBIO BRASIL — Camada de integração com o Backend FastAPI
// Todos os dados vêm do banco de dados via API REST
// ============================================================

const API_BASE = '/api';

// ─── Sessão ───────────────────────────────────────────────────────────────────

const Session = {
  get token() { return localStorage.getItem('cebio_token'); },
  get user() {
    try { return JSON.parse(localStorage.getItem('cebio_user') || '{}'); }
    catch { return {}; }
  },
  set(token, user) {
    localStorage.setItem('cebio_token', token);
    localStorage.setItem('cebio_user', JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem('cebio_token');
    localStorage.removeItem('cebio_user');
  },
  isLoggedIn() { return !!this.token; },
  requireAuth(role) {
    if (!this.isLoggedIn()) { window.location.href = 'login.html'; return false; }
    const u = this.user;
    if (role && u.role !== role && u.role !== 'admin') {
      window.location.href = 'login.html'; return false;
    }
    return true;
  }
};

// ─── HTTP ─────────────────────────────────────────────────────────────────────

async function http(method, path, body = null) {
  const headers = { 'Content-Type': 'application/json' };
  if (Session.token) headers['Authorization'] = `Bearer ${Session.token}`;
  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API_BASE}${path}`, opts);
  if (res.status === 401) { Session.clear(); window.location.href = 'login.html'; return null; }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Erro ${res.status}`);
  return data;
}

async function httpUpload(path, formData) {
  const headers = {};
  if (Session.token) headers['Authorization'] = `Bearer ${Session.token}`;
  const res = await fetch(`${API_BASE}${path}`, { method: 'POST', headers, body: formData });
  if (res.status === 401) { Session.clear(); window.location.href = 'login.html'; return null; }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Erro ${res.status}`);
  return data;
}

const api = {
  get: (p) => http('GET', p),
  post: (p, b) => http('POST', p, b),
  put: (p, b) => http('PUT', p, b),
  delete: (p) => http('DELETE', p),
  upload: (p, fd) => httpUpload(p, fd),
};

// ─── Auth ─────────────────────────────────────────────────────────────────────

const Auth = {
  async login(email, password) {
    const data = await api.post('/auth/login', { email, password });
    Session.set(data.access_token, {
      id: data.user_id, name: data.name, email: data.email,
      role: data.role, is_temp_password: data.is_temp_password,
    });
    return data;
  },
  async logout() {
    try { await api.post('/auth/logout'); } catch {}
    Session.clear();
    window.location.href = 'login.html';
  },
  me: () => api.get('/auth/me'),
  changePassword: (current_password, new_password) =>
    api.post('/auth/change-password', { current_password, new_password }),
};

// ─── Usuários ─────────────────────────────────────────────────────────────────

const Users = {
  list: (p = {}) => api.get('/users?' + new URLSearchParams(p)),
  create: (d) => api.post('/users', d),
  update: (id, d) => api.put(`/users/${id}`, d),
  deactivate: (id) => api.delete(`/users/${id}`),
  getProfile: () => api.get('/users/me/profile'),
  updateProfile: (d) => api.put('/users/me/profile', d),
  resetPassword: (id) => api.post(`/users/${id}/reset-password`),
  batchActivate: (ids, activate) => api.post('/users/batch/activate', { user_ids: ids, activate }),
  batchResetPasswords: (ids) => api.post('/users/batch/reset-passwords', { user_ids: ids }),
  stats: () => api.get('/users/stats'),
};

// ─── Projetos ─────────────────────────────────────────────────────────────────

const Projects = {
  list: (p = {}) => api.get('/projects?' + new URLSearchParams(p)),
  get: (id) => api.get(`/projects/${id}`),
  create: (d) => api.post('/projects', d),
  update: (id, d) => api.put(`/projects/${id}`, d),
  delete: (id) => api.delete(`/projects/${id}`),
  submit: (id) => api.post(`/projects/${id}/submit`),
  restore: (id) => api.post(`/projects/${id}/restore`),
  updateStatus: (id, statusVal, comment = '') =>
    api.post(`/projects/${id}/status`, { status: statusVal, comment }),
  approve: (id, comment = 'Aprovado pelo administrador') =>
    api.post(`/projects/${id}/status`, { status: 'aprovado', comment }),
  reject: (id, comment = 'Rejeitado pelo administrador') =>
    api.post(`/projects/${id}/status`, { status: 'rejeitado', comment }),
  batchApprove: (ids, comment = 'Aprovado em lote') => api.post('/projects/batch/approve', { project_ids: ids, comment }),
  batchReject: (ids, comment = 'Rejeitado em lote') => api.post('/projects/batch/reject', { project_ids: ids, comment }),
  versions: (id) => api.get(`/projects/${id}/versions`),
  stats: () => api.get('/projects/stats'),
  addComment: (id, content) => api.post(`/projects/${id}/comments`, { content }),
  uploadFile: (id, formData) => api.upload(`/projects/${id}/files/upload`, formData),
  deleteFile: (id, fileId) => api.delete(`/projects/${id}/files/${fileId}`),
  addLink: (id, linkData) => api.post(`/projects/${id}/links`, linkData),
  deleteLink: (id, linkId) => api.delete(`/projects/${id}/links/${linkId}`),
};

// ─── Auditoria ────────────────────────────────────────────────────────────────

const Audit = {
  list: (p = {}) => api.get('/audit?' + new URLSearchParams(p)),
  stats: () => api.get('/audit/stats'),
};

// ─── Notificações ─────────────────────────────────────────────────────────────

const Notifications = {
  list: (p = {}) => api.get('/notifications?' + new URLSearchParams(p)),
  broadcast: (d) => api.post('/notifications/mass-send', d),
  adminAll: (p = {}) => api.get('/notifications/admin/all?' + new URLSearchParams(p)),
  markRead: (id) => api.post(`/notifications/${id}/read`),
  markAllRead: () => api.post('/notifications/read-all'),
  delete: (id) => api.delete(`/notifications/${id}`),
};

// ─── Relatórios ───────────────────────────────────────────────────────────────

const Reports = {
  users: (fmt = 'json') => api.get(`/reports/users?format=${fmt}`),
  projects: (fmt = 'json') => api.get(`/reports/projects?format=${fmt}`),
};

// ─── Admin ────────────────────────────────────────────────────────────────────

const Admin = {
  health: () => api.get('/admin/health'),
  status: () => api.get('/admin/status'),
  maintenance: (enabled, message = '') => api.post('/admin/maintenance', { enabled, message }),
  backup: async () => {
    const res = await fetch(`${API_BASE}/admin/backup`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${Session.token}` }
    });
    if (!res.ok) throw new Error('Erro ao criar backup');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `cebio_backup_${new Date().toISOString().slice(0,10)}.zip`;
    a.click();
  },
  config: () => api.get('/admin/config'),
  updateConfig: (key, value) => api.put(`/admin/config/${key}`, { value }),
};

// ─── Helpers de UI ────────────────────────────────────────────────────────────

function toast(msg, type = 'success') {
  const colors = { success: '#1a9a4a', error: '#dc3545', warning: '#f59e0b', info: '#3b82f6' };
  const t = document.createElement('div');
  t.style.cssText = `position:fixed;bottom:24px;right:24px;z-index:9999;background:${colors[type]||colors.success};
    color:#fff;padding:12px 20px;border-radius:10px;font-size:14px;font-weight:500;
    box-shadow:0 4px 16px rgba(0,0,0,0.25);max-width:380px;line-height:1.4;
    animation:slideIn .25s ease;`;
  // SEGURANÇA: Usar textContent ao invés de innerHTML para prevenir XSS
  t.textContent = msg;
  if (!document.getElementById('cebio-toast-style')) {
    const s = document.createElement('style');
    s.id = 'cebio-toast-style';
    s.textContent = '@keyframes slideIn{from{transform:translateX(120%);opacity:0}to{transform:translateX(0);opacity:1}}';
    document.head.appendChild(s);
  }
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

function loading(show, el) {
  if (!el) return;
  if (show) { 
    el._orig = el.textContent; 
    el.textContent = 'Carregando...'; 
    el.disabled = true; 
  }
  else { 
    if (el._orig !== undefined) el.textContent = el._orig; 
    el.disabled = false; 
  }
}

function fmtDate(dt) {
  if (!dt) return 'Não especificada';
  return new Date(dt).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

function fmtDateOnly(dt) {
  if (!dt) return 'Não especificada';
  return new Date(dt).toLocaleDateString('pt-BR');
}

function badgeStatus(s) {
  const map = {
    rascunho: 'badge-yellow', pendente: 'badge-yellow', em_submissao: 'badge-yellow',
    aprovado: 'badge-green', rejeitado: 'badge-red', em_revisao: 'badge-blue', 
    ativo: 'badge-green', inativo: 'badge-red',
  };
  const labels = {
    rascunho: 'Rascunho', pendente: 'Pendente', em_submissao: 'Em Submissão',
    aprovado: 'Aprovado', rejeitado: 'Rejeitado', em_revisao: 'Em Revisão', 
    ativo: 'Ativo', inativo: 'Inativo',
  };
  return `<span class="badge ${map[s]||'badge-yellow'}">${labels[s]||s}</span>`;
}

function badgeRole(r) {
  const map = { admin: 'badge-red', pesquisador: 'badge-blue', bolsista: 'badge-green' };
  const labels = { admin: 'Administrador', pesquisador: 'Pesquisador', bolsista: 'Bolsista' };
  return `<span class="badge ${map[r]||'badge-yellow'}">${labels[r]||r}</span>`;
}

function emptyRow(cols, msg = 'Nenhum registro encontrado') {
  return `<tr><td colspan="${cols}" style="text-align:center;padding:32px;color:#9e9e9e;font-style:italic">${msg}</td></tr>`;
}

function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val ?? '0';
}

// ─── Inicialização Global ─────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function () {
  const user = Session.user;

  // Preenche nome/role do usuário logado em todos os elementos
  document.querySelectorAll('.user-name, .uname, #header-user-name, #sidebar-user-name').forEach(el => {
    el.textContent = user.name || user.email || 'Usuário';
  });
  document.querySelectorAll('.uinst, #sidebar-user-inst').forEach(el => {
    el.textContent = user.institution || 'CEBIO Brasil — Centro de Excelência em Bioinsumos';
  });
  document.querySelectorAll('.user-badge-type').forEach(el => {
    const roles = { admin: 'Administrador', pesquisador: 'Pesquisador', bolsista: 'Bolsista' };
    el.textContent = roles[user.role] || user.role || '';
  });
  const avatar = document.getElementById('user-avatar');
  if (avatar) avatar.textContent = (user.name || 'U').charAt(0).toUpperCase();

  // Botão logout
  document.querySelectorAll('.logout-btn, [data-logout]').forEach(el => {
    el.style.cursor = 'pointer';
    el.addEventListener('click', (e) => { e.preventDefault(); Auth.logout(); });
  });

  // Redirecionamento global para elementos com data-href
  document.querySelectorAll('[data-href]').forEach(el => {
    el.style.cursor = 'pointer';
    el.addEventListener('click', (e) => {
      e.preventDefault();
      const href = el.getAttribute('data-href');
      if (href) window.location.href = href;
    });
  });

  // Alerta de senha temporária
  if (user && user.is_temp_password && !window.location.pathname.includes('login')) {
    toast('⚠️ Altere sua senha temporária no perfil.', 'warning');
  }

  // Inicializa a página específica
  const page = window.location.pathname.split('/').pop() || 'index.html';
  if (typeof window.initPage === 'function') window.initPage(page);
});
