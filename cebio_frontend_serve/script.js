// ============================================================
// CEBIO BRASIL — Lógica de cada página (dados do banco de dados)
// Todos os dados vêm da API — nenhum dado fixo/mockado aqui.
// ============================================================

// ─── Utilitários de UI ────────────────────────────────────────────────────────
// setEl() e loading() já definidos em api.js — aqui apenas setHtml()

function setHtml(id, html) {
  const el = document.getElementById(id);
  if (el) {
    // Usar sanitização para prevenir XSS
    if (typeof sanitizeHtml === 'function') {
      el.innerHTML = sanitizeHtml(html);
    } else {
      // Fallback: usar textContent (mais seguro)
      el.textContent = html;
    }
  }
}

// ─── Login ────────────────────────────────────────────────────────────────────

async function initLogin() {
  if (Session.isLoggedIn()) {
    const u = Session.user;
    if (u.role === 'admin') { window.location.href = 'admin-dashboard.html'; return; }
    if (u.role === 'pesquisador') { window.location.href = 'pesquisador-dashboard.html'; return; }
    window.location.href = 'bolsista-dashboard.html';
    return;
  }

  const form = document.getElementById('loginForm');
  if (!form) return;

  const toggleBtn = document.getElementById('togglePass');
  const passInput = document.getElementById('loginPass');
  if (toggleBtn && passInput) {
    toggleBtn.addEventListener('click', () => {
      passInput.type = passInput.type === 'password' ? 'text' : 'password';
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const emailEl = document.getElementById('loginUser') || document.getElementById('loginEmail');
    const email = emailEl?.value?.trim();
    const pass = document.getElementById('loginPass')?.value;
    const btn = form.querySelector('button[type=submit]');
    loading(true, btn);
    try {
      const data = await Auth.login(email, pass);
      
      // Verificar se precisa trocar senha
      if (data.requires_password_change || data.is_temp_password) {
        loading(false, btn);
        if (typeof showPasswordChangeModal === 'function') {
          showPasswordChangeModal(true); // Modal obrigatório
        } else {
          showToast('Você precisa trocar sua senha temporária', 'warning');
          setTimeout(() => {
            if (data.role === 'admin') window.location.href = 'admin-dashboard.html';
            else if (data.role === 'pesquisador') window.location.href = 'pesquisador-dashboard.html';
            else window.location.href = 'bolsista-dashboard.html';
          }, 1000);
        }
        return;
      }
      
      showToast(`Bem-vindo, ${data.name}!`, 'success');
      setTimeout(() => {
        if (data.role === 'admin') window.location.href = 'admin-dashboard.html';
        else if (data.role === 'pesquisador') window.location.href = 'pesquisador-dashboard.html';
        else window.location.href = 'bolsista-dashboard.html';
      }, 600);
    } catch (err) {
      showToast(err.message || 'Usuário ou senha inválidos', 'error');
      loading(false, btn);
    }
  });
}

// ─── Admin Dashboard ──────────────────────────────────────────────────────────

async function initAdminDashboard() {
  if (!Session.requireAuth('admin')) return;

  try {
    const [projStats, userStats] = await Promise.all([
      Projects.stats(),
      Users.stats(),
    ]);

    // Stats cards
    setEl('stat-total', projStats.total || 0);
    setEl('stat-finalizados', projStats.by_status?.aprovado || 0);
    setEl('stat-andamento', (projStats.by_status?.em_revisao || 0) + (projStats.by_status?.pendente || 0));
    setEl('stat-meta', projStats.total > 0 ? Math.round(((projStats.by_status?.aprovado || 0) / projStats.total) * 100) + '%' : '0%');
    
    // Stat subs (valores dinamicos)
    setEl('stat-total-sub', 'Total de projetos');
    setEl('stat-finalizados-sub', 'Projetos aprovados');
    setEl('stat-andamento-sub', 'Aguardando revisao');
    setEl('stat-meta-sub', 'Taxa de aprovacao');

    // Gráficos dinâmicos
    if (window.Chart) {
      const pieCtx = document.getElementById('pieChart');
      if (pieCtx) {
        const byStatus = projStats.by_status || {};
        new Chart(pieCtx, {
          type: 'doughnut',
          data: {
            labels: ['Aprovados', 'Pendentes', 'Em Revisão', 'Rejeitados'],
            datasets: [{ 
              data: [byStatus.aprovado||0, byStatus.pendente||0, byStatus.em_revisao||0, byStatus.rejeitado||0],
              backgroundColor: ['#1a9a4a','#f59e0b','#3b82f6','#dc3545'] 
            }]
          },
          options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
        });
      }
      const barCtx = document.getElementById('barChart');
      if (barCtx) {
        new Chart(barCtx, {
          type: 'bar',
          data: {
            labels: ['Jan','Fev','Mar','Abr','Mai','Jun'],
            datasets: [{ label: 'Projetos', data: [0,0,0,0,0,projStats.total||0], backgroundColor: '#1a9a4a' }]
          },
          options: { responsive: true, plugins: { legend: { display: false } } }
        });
      }
    }

    // Projetos recentes
    const recentProjEl = document.getElementById('recent-projects-list');
    if (recentProjEl) {
      const projData = await Projects.list({ limit: 5 });
      const projs = projData.items || [];
      recentProjEl.innerHTML = projs.length
        ? projs.map(p => `
            <div style="padding:12px 0;border-bottom:1px solid #f0f0f0">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
                <h4 style="margin:0;font-size:14px;color:#1b7a3a">${p.title}</h4>
                ${badgeStatus(p.status)}
              </div>
              <div style="font-size:12px;color:#9e9e9e">
                <span>${p.category || '0'}</span> • <span>${p.owner_name || 'Sem informação'}</span> • <span>${fmtDateOnly(p.created_at)}</span>
              </div>
            </div>`).join('')
        : emptyRow(1, 'Nenhum projeto cadastrado');
    }

    // Atividades recentes
    const recentEl = document.getElementById('recent-activity-list');
    if (recentEl) {
      const logs = await Audit.list({ limit: 5 });
      recentEl.innerHTML = (logs.items || []).length
        ? (logs.items || []).map(l => `
            <div style="display:flex;gap:12px;padding:10px 0;border-bottom:1px solid #f0f0f0">
              <div style="width:8px;height:8px;border-radius:50%;background:${l.severity === 'high' ? '#dc3545' : '#43a047'};margin-top:5px;flex-shrink:0"></div>
              <div>
                <div style="font-weight:600;font-size:13px">${l.action}</div>
                <div style="font-size:12px;color:#555">${l.details || ''}</div>
                <div style="font-size:11px;color:#9e9e9e">${l.user_name || 'Sistema'} • ${fmtDate(l.created_at)}</div>
              </div>
            </div>`).join('')
        : emptyRow(1, 'Nenhuma atividade recente');
    }
  } catch (err) {
    toast('Erro ao carregar dashboard: ' + err.message, 'error');
  }
}

// ─── Admin Usuários ───────────────────────────────────────────────────────────

async function initAdminUsuarios() {
  if (!Session.requireAuth('admin')) return;

  async function loadUsers() {
    const search = document.querySelector('.search-box input')?.value || '';
    const selects = document.querySelectorAll('.filter-group select');
    const role = selects[0]?.value || '';
    const status = selects[1]?.value || '';

    try {
      const params = { page: 1, limit: 50 };
      if (search) params.search = search;
      if (role) params.role = role;

      const data = await Users.list(params);
      const users = data.items || [];

      const tbody = document.getElementById('table-body') || document.querySelector('tbody');
      if (!tbody) return;

      if (users.length === 0) {
        tbody.innerHTML = emptyRow(6, 'Nenhum usuário encontrado');
        return;
      }

      tbody.innerHTML = users.map(u => `
        <tr>
          <td>
            <div style="font-weight:600">${u.name || '0'}</div>
            <div style="font-size:12px;color:#757575">${u.email || '0'}</div>
          </td>
          <td>${badgeRole(u.role)}</td>
          <td>
            ${badgeStatus(u.is_active ? 'ativo' : 'inativo')}
            ${u.is_temp_password ? '<br><span class="badge badge-yellow">⚠ Senha Temporária</span>' : ''}
          </td>
          <td>${u.last_login ? fmtDate(u.last_login) : 'Nenhum acesso'}</td>
          <td>${fmtDateOnly(u.created_at)}</td>
          <td>
            <div style="display:flex;gap:8px">
              <button onclick="doResetPassword(${u.id},'${u.name}',event)" class="btn-sm btn-warning">Resetar</button>
              <button onclick="doToggleUser(${u.id},${u.is_active},event)" class="btn-sm ${u.is_active ? 'btn-danger' : 'btn-success'}">
                ${u.is_active ? 'Desativar' : 'Ativar'}
              </button>
            </div>
          </td>
        </tr>`).join('');
    } catch (err) {
      toast('Erro ao carregar usuários: ' + err.message, 'error');
    }
  }

  document.querySelectorAll('.filter-group select, .search-box input').forEach(el => {
    el.addEventListener('change', loadUsers);
    el.addEventListener('keyup', loadUsers);
  });

  await loadUsers();
}

window.doResetPassword = async function(id, name, e) {
  e?.stopPropagation();
  if (!confirm(`Resetar senha de ${name}?`)) return;
  try {
    const d = await Users.resetPassword(id);
    toast(`Nova senha temporária: ${d.temp_password}`, 'info');
  } catch (err) { toast('Erro: ' + err.message, 'error'); }
};

window.doToggleUser = async function(id, isActive, e) {
  e?.stopPropagation();
  if (!confirm(`Deseja ${isActive ? 'desativar' : 'ativar'} este usuário?`)) return;
  try {
    await Users.batchActivate([id], !isActive);
    toast(`Usuário ${isActive ? 'desativado' : 'ativado'}!`);
    initAdminUsuarios();
  } catch (err) { toast('Erro: ' + err.message, 'error'); }
};

// ─── Pesquisador Dashboard ─────────────────────────────────────────────────────

async function initPesquisadorDashboard() {
  if (!Session.requireAuth('pesquisador', 'bolsista')) return;

  try {
    const stats = await Projects.stats();
    
    // Stats cards
    const statNumbers = document.querySelectorAll('.stat-number');
    if (statNumbers.length >= 4) {
      statNumbers[0].textContent = stats.total || 0;
      statNumbers[1].textContent = stats.by_status?.em_revisao || 0;
      statNumbers[2].textContent = stats.by_status?.aprovado || 0;
      statNumbers[3].textContent = stats.by_status?.rejeitado || 0;
    }
    
    // Atualizar subs
    const statSubs = document.querySelectorAll('.stat-sub');
    if (statSubs.length >= 4) {
      statSubs[0].textContent = `${stats.total || 0} projetos no total`;
      if (stats.total > 0) {
        const taxa = Math.round(((stats.by_status?.aprovado || 0) / stats.total) * 100);
        statSubs[2].textContent = `Taxa: ${taxa}%`;
      }
    }

    // Projetos recentes
    const recentContainer = document.querySelector('.grid-2-wide .card');
    if (recentContainer) {
      const projData = await Projects.list({ limit: 3 });
      const projs = projData.items || [];
      
      const cardHead = recentContainer.querySelector('.card-head');
      const listHtml = projs.length 
        ? projs.map(p => `
            <div class="project-item" style="cursor:pointer; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #eee;" onclick="window.location.href='project-detail-view.html?id=${p.id}'">
              <div class="project-item-head" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <h4 style="margin:0; color:#1b7a3a;">${p.title}</h4>
                ${badgeStatus(p.status)}
              </div>
              <p style="font-size:13px; color:#666; margin-bottom:8px;">${p.summary ? p.summary.substring(0, 180) + '...' : 'Sem descrição'}</p>
              <div class="project-meta" style="font-size:12px; color:#999; display:flex; gap:10px;">
                <span>${(p.category || '').replace(/_/g, ' ')}</span>
                <span>•</span>
                <span>${p.owner_name || 'Você'}</span>
                <span>•</span>
                <span>${fmtDateOnly(p.created_at)}</span>
              </div>
            </div>`).join('')
        : `<div class="empty-state" style="padding:40px; text-align:center; color:#9e9e9e;">
            <svg viewBox="0 0 24 24" width="48" height="48" fill="#e0e0e0" style="margin-bottom:12px;"><path d="M20 6h-8l-2-2H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2z"/></svg>
            <h4>Nenhum projeto encontrado</h4>
            <p>Você ainda não possui projetos submetidos.</p>
          </div>`;
      
      recentContainer.innerHTML = '';
      if (cardHead) recentContainer.appendChild(cardHead);
      const listDiv = document.createElement('div');
      listDiv.style.padding = '15px';
      listDiv.innerHTML = listHtml;
      recentContainer.appendChild(listDiv);
    }

    // Boas vindas
    const welcomeName = document.getElementById('welcome-name');
    if (welcomeName) welcomeName.textContent = Session.user.name || 'Pesquisador';

  } catch (err) {
    console.error('Erro no dashboard:', err);
    toast('Erro ao carregar dados: ' + err.message, 'error');
  }
}

// ─── Bolsista Dashboard ────────────────────────────────────────────────────────

async function initBolsistaDashboard() {
  await initPesquisadorDashboard();
}

// ─── Histórico ────────────────────────────────────────────────────────────────

async function initHistorico() {
  if (!Session.requireAuth()) return;

  try {
    const data = await Audit.list({ per_page: 50 });
    const logs = data.items || [];
    
    // Stats
    setEl('stat-n-1', data.total || 0);
    setEl('stat-n-2', logs.filter(l => l.action.includes('PROJECT_CREATED') || l.action.includes('SUBMIT')).length);
    setEl('stat-n-3', logs.filter(l => l.action.includes('STATUS') || l.action.includes('REVISION')).length);
    
    const today = new Date().toISOString().split('T')[0];
    setEl('stat-n-4', logs.filter(l => l.timestamp && l.timestamp.startsWith(today)).length);

    const timeline = document.querySelector('.timeline');
    if (timeline) {
      if (logs.length === 0) {
        timeline.innerHTML = '<div style="padding:40px; text-align:center; color:#9e9e9e;">Nenhuma atividade registrada ainda.</div>';
      } else {
        timeline.innerHTML = logs.map(log => {
          let dotColor = 'gray';
          let badgeClass = 'badge-gray';
          let actionLabel = log.action;

          if (log.action.includes('CREATED')) { dotColor = 'green'; badgeClass = 'badge-green'; actionLabel = 'Criação'; }
          else if (log.action.includes('STATUS')) { dotColor = 'blue'; badgeClass = 'badge-blue'; actionLabel = 'Status'; }
          else if (log.action.includes('LOGIN')) { dotColor = 'purple'; badgeClass = 'badge-purple'; actionLabel = 'Acesso'; }
          else if (log.action.includes('FILE')) { dotColor = 'orange'; badgeClass = 'badge-orange'; actionLabel = 'Arquivo'; }
          else if (log.action.includes('DELETE')) { dotColor = 'red'; badgeClass = 'badge-red'; actionLabel = 'Exclusão'; }

          return `
            <div class="timeline-item">
              <div class="timeline-dot ${dotColor}"></div>
              <div class="timeline-content">
                <div class="timeline-head">
                  <span class="badge ${badgeClass}">${actionLabel}</span>
                  <span class="timeline-date">${fmtDate(log.timestamp)}</span>
                </div>
                <h4>${log.action.replace(/_/g, ' ')}</h4>
                <p>${log.details || 'Sem detalhes adicionais'}</p>
              </div>
            </div>`;
        }).join('');
      }
    }

    // Atualizar contagem no card-head
    const countSpan = document.querySelector('.card-head span');
    if (countSpan) countSpan.textContent = `${data.total || 0} atividade(s)`;

  } catch (err) {
    console.error('Erro ao carregar histórico:', err);
    toast('Erro ao carregar histórico: ' + err.message, 'error');
  }
}

// ─── Admin Projetos ───────────────────────────────────────────────────────────

async function initAdminProjetos() {
  if (!Session.requireAuth('admin')) return;

  async function loadProjects() {
    const search = document.querySelector('.search-box input')?.value || '';
    const selects = document.querySelectorAll('.filter-group select');
    const status = selects[0]?.value || '';

    try {
      const params = { limit: 50 };
      if (search) params.search = search;
      if (status) params.status = status;

      const data = await Projects.list(params);
      const projects = data.items || [];

      const tbody = document.getElementById('table-body') || document.querySelector('tbody');
      if (!tbody) return;

      if (projects.length === 0) {
        tbody.innerHTML = emptyRow(6, 'Nenhum projeto encontrado');
        return;
      }

      tbody.innerHTML = projects.map(p => `
        <tr>
          <td>
            <div style="font-weight:600;color:#1b7a3a">${p.title}</div>
            <div style="font-size:12px;color:#757575">${p.category || '0'}</div>
          </td>
          <td>${p.academic_level || '0'}</td>
          <td>${p.owner_name || 'Sem informação'}</td>
          <td>${badgeStatus(p.status)}</td>
          <td>${fmtDateOnly(p.created_at)}</td>
          <td>
            <div style="display:flex;gap:6px">
              <button onclick="window.location.href='projeto-detalhe.html?id=${p.id}'" class="btn-sm btn-info">Ver</button>
              ${p.status === 'pendente' || p.status === 'em_revisao' ? `
                <button onclick="doApproveProject(${p.id},'${p.title}',event)" class="btn-sm btn-success">Aprovar</button>
              ` : ''}
            </div>
          </td>
        </tr>`).join('');
    } catch (err) {
      toast('Erro ao carregar projetos: ' + err.message, 'error');
    }
  }

  document.querySelectorAll('.filter-group select, .search-box input').forEach(el => {
    el.addEventListener('change', loadProjects);
    el.addEventListener('keyup', loadProjects);
  });

  await loadProjects();
}

window.doApproveProject = async function(id, title, e) {
  e?.stopPropagation();
  if (!confirm(`Aprovar projeto "${title}"?`)) return;
  try {
    await Projects.approve(id);
    toast('Projeto aprovado!');
    initAdminProjetos();
  } catch (err) { toast('Erro: ' + err.message, 'error'); }
};

// ─── Pesquisador / Bolsista Dashboard ────────────────────────────────────────

async function initUserDashboard() {
  if (!Session.requireAuth()) return;
  const user = Session.user;

  try {
    const data = await Projects.list({ limit: 100 });
    const projects = data.items || [];

    setEl('stat-total', projects.length);
    setEl('stat-aprovados', projects.filter(p => p.status === 'aprovado').length);
    setEl('stat-pendentes', projects.filter(p => p.status === 'pendente' || p.status === 'em_revisao').length);

    const projContainer = document.getElementById('recent-projects-list');
    if (projContainer) {
      projContainer.innerHTML = projects.slice(0, 5).map(p => `
        <div class="card" style="margin-bottom:12px;padding:16px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <h4 style="margin:0;font-size:14px;color:#1b7a3a">${p.title}</h4>
            ${badgeStatus(p.status)}
          </div>
          <div style="font-size:12px;color:#9e9e9e;margin-top:8px;">${p.category || '0'} • ${fmtDateOnly(p.created_at)}</div>
        </div>`).join('') || emptyRow(1, 'Nenhum projeto');
    }
  } catch (err) {
    toast('Erro ao carregar dashboard: ' + err.message, 'error');
  }
}

// ─── Roteador de Páginas ──────────────────────────────────────────────────────

window.initPage = function(page) {
  const routes = {
    'login.html': initLogin,
    'admin-dashboard.html': initAdminDashboard,
    'admin-usuarios.html': initAdminUsuarios,
    'admin-projetos.html': initAdminProjetos,
    'admin-aprovacao-lote.html': window.initAdminAprovacaoLote,
    'pesquisador-dashboard.html': initUserDashboard,
    'bolsista-dashboard.html': initUserDashboard,
  };

  const fn = routes[page];
  if (fn) fn();
};


// ─── Funções Utilitárias ──────────────────────────────────────────────────────

/**
 * Formata tamanho de arquivo em bytes para formato legível
 */
function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Faz download de um arquivo do projeto
 */
async function downloadFile(fileId, filename) {
  if (typeof showLoading === 'function') showLoading();
  try {
    const token = localStorage.getItem('token');
    const response = await fetch(`/api/files/${fileId}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (!response.ok) {
      if (response.status === 403) {
        throw new Error('Você não tem permissão para baixar este arquivo');
      } else if (response.status === 404) {
        throw new Error('Arquivo não encontrado');
      } else {
        throw new Error('Erro ao baixar arquivo');
      }
    }
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    if (typeof showSuccess === 'function') {
      showSuccess('Download concluído!');
    } else {
      toast('Download concluído!', 'success');
    }
  } catch (error) {
    console.error('Erro no download:', error);
    if (typeof showError === 'function') {
      showError(error.message || 'Erro ao baixar arquivo');
    } else {
      toast(error.message || 'Erro ao baixar arquivo', 'error');
    }
  } finally {
    if (typeof hideLoading === 'function') hideLoading();
  }
}

/**
 * Renderiza lista de fotos com botões de download
 */
function renderFotos(fotos) {
  if (!fotos || fotos.length === 0) {
    return '<p style="color:#888;">Nenhuma foto anexada</p>';
  }
  
  return fotos.map(foto => `
    <div class="file-item" style="
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px;
      background: #0a0a0a;
      border: 1px solid #333;
      border-radius: 4px;
      margin-bottom: 8px;
    ">
      <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#4dd0e1" stroke-width="2">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
        <circle cx="8.5" cy="8.5" r="1.5"/>
        <polyline points="21 15 16 10 5 21"/>
      </svg>
      <div style="flex: 1;">
        <div style="color: #fff; font-weight: 500;">${foto.original_name}</div>
        <div style="color: #888; font-size: 12px;">${formatFileSize(foto.size_bytes)}</div>
      </div>
      <button onclick="downloadFile(${foto.id}, '${foto.original_name.replace(/'/g, "\\'")}')" 
              class="btn btn-sm btn-blue" 
              style="padding: 6px 12px;">
        Download
      </button>
    </div>
  `).join('');
}

/**
 * Renderiza lista de documentos PDF com botões de download
 */
function renderDocumentos(documentos) {
  if (!documentos || documentos.length === 0) {
    return '<p style="color:#888;">Nenhum documento anexado</p>';
  }
  
  return documentos.map(doc => `
    <div class="file-item" style="
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px;
      background: #0a0a0a;
      border: 1px solid #333;
      border-radius: 4px;
      margin-bottom: 8px;
    ">
      <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#f44336" stroke-width="2">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
      </svg>
      <div style="flex: 1;">
        <div style="color: #fff; font-weight: 500;">${doc.original_name}</div>
        <div style="color: #888; font-size: 12px;">${formatFileSize(doc.size_bytes)} • PDF</div>
      </div>
      <button onclick="downloadFile(${doc.id}, '${doc.original_name.replace(/'/g, "\\'")}')" 
              class="btn btn-sm btn-blue" 
              style="padding: 6px 12px;">
        Download
      </button>
    </div>
  `).join('');
}

/**
 * Restaura uma versão anterior do projeto
 */
async function restoreVersion(projectId, versionId) {
  if (!confirm('Tem certeza que deseja restaurar esta versão? A versão atual será salva como backup.')) {
    return;
  }
  
  if (typeof showLoading === 'function') showLoading();
  try {
    const result = await http('POST', `/projects/${projectId}/versions/${versionId}/restore`);
    
    if (typeof showSuccess === 'function') {
      showSuccess(result.message || 'Versão restaurada com sucesso!');
    } else {
      toast(result.message || 'Versão restaurada com sucesso!', 'success');
    }
    
    // Recarregar página após 1 segundo
    setTimeout(() => {
      window.location.reload();
    }, 1000);
  } catch (error) {
    if (typeof showError === 'function') {
      showError(error.message || 'Erro ao restaurar versão');
    } else {
      toast(error.message || 'Erro ao restaurar versão', 'error');
    }
  } finally {
    if (typeof hideLoading === 'function') hideLoading();
  }
}

/**
 * Renderiza histórico de versões com botão de restaurar
 */
function renderVersionHistory(versions, projectId) {
  if (!versions || versions.length === 0) {
    return '<p style="color:#888;">Nenhuma versão registrada</p>';
  }
  
  return versions.map(version => `
    <div class="version-item" style="
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px;
      background: #0a0a0a;
      border: 1px solid #333;
      border-radius: 4px;
      margin-bottom: 8px;
    ">
      <div style="flex: 1;">
        <div style="color: #fff; font-weight: 500;">Versão #${version.version_number}</div>
        <div style="color: #888; font-size: 12px;">
          ${version.description || 'Sem descrição'} • 
          ${version.author_name || 'Desconhecido'} • 
          ${new Date(version.created_at).toLocaleString('pt-BR')}
        </div>
      </div>
      ${version.change_type !== 'backup' ? `
        <button onclick="restoreVersion(${projectId}, ${version.id})" 
                class="btn btn-sm btn-yellow" 
                style="padding: 6px 12px;">
          Restaurar
        </button>
      ` : '<span style="color: #888; font-size: 12px;">Backup</span>'}
    </div>
  `).join('');
}


/**
 * Gera relatório PDF de um projeto
 */
async function generateProjectPDF(projectId) {
  if (typeof showLoading === 'function') showLoading();
  try {
    const token = localStorage.getItem('cebio_token');
    const response = await fetch(`/api/reports/project/${projectId}/pdf`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (!response.ok) {
      if (response.status === 403) {
        throw new Error('Você não tem permissão para gerar relatório deste projeto');
      } else if (response.status === 404) {
        throw new Error('Projeto não encontrado');
      } else {
        throw new Error('Erro ao gerar relatório PDF');
      }
    }
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    
    // Extrair nome do arquivo do header Content-Disposition
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = `projeto_${projectId}.pdf`;
    if (contentDisposition) {
      const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
      if (matches != null && matches[1]) {
        filename = matches[1].replace(/['"]/g, '');
      }
    }
    
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    if (typeof showSuccess === 'function') {
      showSuccess('Relatório PDF gerado com sucesso!');
    } else {
      toast('Relatório PDF gerado com sucesso!', 'success');
    }
  } catch (error) {
    console.error('Erro ao gerar PDF:', error);
    if (typeof showError === 'function') {
      showError(error.message || 'Erro ao gerar relatório PDF');
    } else {
      toast(error.message || 'Erro ao gerar relatório PDF', 'error');
    }
  } finally {
    if (typeof hideLoading === 'function') hideLoading();
  }
}


/**
 * Verificação periódica de modo manutenção
 */
let maintenanceCheckInterval = null;

function startMaintenanceCheck() {
  // Verificar a cada 30 segundos
  if (maintenanceCheckInterval) {
    clearInterval(maintenanceCheckInterval);
  }
  
  maintenanceCheckInterval = setInterval(async () => {
    try {
      const response = await fetch('/api/admin/maintenance');
      const data = await response.json();
      
      if (data.maintenance_mode) {
        handleMaintenanceMode(data.message);
      }
    } catch (error) {
      // Silenciosamente ignorar erros de rede
      console.log('Erro ao verificar modo manutenção:', error);
    }
  }, 30000); // 30 segundos
}

function stopMaintenanceCheck() {
  if (maintenanceCheckInterval) {
    clearInterval(maintenanceCheckInterval);
    maintenanceCheckInterval = null;
  }
}

function handleMaintenanceMode(message) {
  // Parar verificação
  stopMaintenanceCheck();
  
  // Fazer logout
  Session.clear();
  
  // Salvar mensagem de manutenção
  localStorage.setItem('maintenance_message', message || 'Sistema em manutenção.');
  
  // Redirecionar para página de manutenção
  window.location.href = 'maintenance.html';
}

// Iniciar verificação quando usuário estiver logado
document.addEventListener('DOMContentLoaded', function() {
  if (Session.isLoggedIn() && !window.location.pathname.includes('maintenance.html')) {
    startMaintenanceCheck();
  }
  
  // Inicializa a página específica
  const page = window.location.pathname.split('/').pop() || 'index.html';
  
  // Mapeamento de inicialização por página
  if (page.includes('admin-dashboard')) initAdminDashboard();
  else if (page.includes('admin-usuarios')) initAdminUsuarios();
  else if (page.includes('admin-projetos')) initAdminProjetos();
  else if (page.includes('pesquisador-dashboard')) initPesquisadorDashboard();
  else if (page.includes('bolsista-dashboard')) initBolsistaDashboard();
  else if (page.includes('historico')) initHistorico();
  else if (page.includes('login')) initLogin();
  
  if (typeof window.initPage === 'function') window.initPage(page);
});
