/**
 * CEBIO Brasil - Correções de XSS
 * Este arquivo contém funções auxiliares para renderização segura
 */

/**
 * Renderiza lista de projetos de forma segura
 */
function renderProjectsList(projects, container) {
  if (!container) return;
  
  container.textContent = ''; // Limpar
  
  if (!projects || projects.length === 0) {
    container.textContent = 'Nenhum projeto encontrado';
    return;
  }
  
  projects.forEach(p => {
    const div = document.createElement('div');
    div.style.cssText = 'padding:12px 0;border-bottom:1px solid #f0f0f0';
    
    const headerDiv = document.createElement('div');
    headerDiv.style.cssText = 'display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px';
    
    const title = document.createElement('h4');
    title.style.cssText = 'margin:0;font-size:14px;color:#1b7a3a';
    title.textContent = p.title; // Seguro - usa textContent
    
    const badge = document.createElement('span');
    badge.className = badgeStatus(p.status).match(/class="([^"]+)"/)?.[1] || '';
    badge.textContent = badgeStatus(p.status).match(/>([^<]+)</)?.[1] || p.status;
    
    headerDiv.appendChild(title);
    headerDiv.appendChild(badge);
    
    const metaDiv = document.createElement('div');
    metaDiv.style.cssText = 'font-size:12px;color:#9e9e9e';
    
    const category = document.createElement('span');
    category.textContent = p.category || '0';
    
    const owner = document.createElement('span');
    owner.textContent = p.owner_name || 'Sem informação';
    
    const date = document.createElement('span');
    date.textContent = fmtDateOnly(p.created_at);
    
    metaDiv.appendChild(category);
    metaDiv.appendChild(document.createTextNode(' • '));
    metaDiv.appendChild(owner);
    metaDiv.appendChild(document.createTextNode(' • '));
    metaDiv.appendChild(date);
    
    div.appendChild(headerDiv);
    div.appendChild(metaDiv);
    container.appendChild(div);
  });
}

/**
 * Renderiza lista de logs de auditoria de forma segura
 */
function renderAuditLogs(logs, container) {
  if (!container) return;
  
  container.textContent = ''; // Limpar
  
  if (!logs || logs.length === 0) {
    container.textContent = 'Nenhum log recente';
    return;
  }
  
  logs.forEach(l => {
    const div = document.createElement('div');
    div.style.cssText = 'display:flex;gap:12px;padding:10px 0;border-bottom:1px solid #f0f0f0';
    
    const icon = document.createElement('div');
    icon.style.cssText = 'width:32px;height:32px;border-radius:50%;background:#f5f5f5;display:flex;align-items:center;justify-content:center;flex-shrink:0';
    icon.textContent = '📋';
    
    const content = document.createElement('div');
    content.style.cssText = 'flex:1';
    
    const action = document.createElement('div');
    action.style.cssText = 'font-weight:500;font-size:13px';
    action.textContent = l.action || 'Ação';
    
    const details = document.createElement('div');
    details.style.cssText = 'font-size:12px;color:#757575;margin-top:2px';
    details.textContent = l.details || '';
    
    const time = document.createElement('div');
    time.style.cssText = 'font-size:11px;color:#9e9e9e;margin-top:4px';
    time.textContent = fmtDate(l.timestamp);
    
    content.appendChild(action);
    content.appendChild(details);
    content.appendChild(time);
    
    div.appendChild(icon);
    div.appendChild(content);
    container.appendChild(div);
  });
}

/**
 * Renderiza tabela de usuários de forma segura
 */
function renderUsersTable(users, tbody) {
  if (!tbody) return;
  
  tbody.textContent = ''; // Limpar
  
  if (!users || users.length === 0) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = 6;
    td.style.textAlign = 'center';
    td.style.padding = '40px';
    td.style.color = '#888';
    td.textContent = 'Nenhum usuário encontrado';
    tr.appendChild(td);
    tbody.appendChild(tr);
    return;
  }
  
  users.forEach(u => {
    const tr = document.createElement('tr');
    
    // ID
    const tdId = document.createElement('td');
    tdId.textContent = u.id;
    tr.appendChild(tdId);
    
    // Nome
    const tdName = document.createElement('td');
    const nameDiv = document.createElement('div');
    nameDiv.style.fontWeight = '500';
    nameDiv.textContent = u.name;
    const emailDiv = document.createElement('div');
    emailDiv.style.fontSize = '12px';
    emailDiv.style.color = '#888';
    emailDiv.textContent = u.email;
    tdName.appendChild(nameDiv);
    tdName.appendChild(emailDiv);
    tr.appendChild(tdName);
    
    // Role
    const tdRole = document.createElement('td');
    const roleBadge = document.createElement('span');
    roleBadge.className = u.role === 'admin' ? 'badge badge-red' : 
                          u.role === 'pesquisador' ? 'badge badge-blue' : 'badge badge-gray';
    roleBadge.textContent = u.role;
    tdRole.appendChild(roleBadge);
    tr.appendChild(tdRole);
    
    // Status
    const tdStatus = document.createElement('td');
    const statusBadge = document.createElement('span');
    statusBadge.className = u.is_active ? 'badge badge-green' : 'badge badge-gray';
    statusBadge.textContent = u.is_active ? 'Ativo' : 'Inativo';
    tdStatus.appendChild(statusBadge);
    tr.appendChild(tdStatus);
    
    // Último login
    const tdLogin = document.createElement('td');
    tdLogin.textContent = u.last_login ? fmtDate(u.last_login) : 'Nenhum acesso';
    tr.appendChild(tdLogin);
    
    // Criado em
    const tdCreated = document.createElement('td');
    tdCreated.textContent = fmtDateOnly(u.created_at);
    tr.appendChild(tdCreated);
    
    // Ações
    const tdActions = document.createElement('td');
    const actionsDiv = document.createElement('div');
    actionsDiv.style.cssText = 'display:flex;gap:8px';
    
    const viewBtn = document.createElement('button');
    viewBtn.className = 'btn btn-sm btn-blue';
    viewBtn.textContent = 'Ver';
    viewBtn.onclick = () => window.location.href = `admin-usuario-detalhes.html?id=${u.id}`;
    
    const editBtn = document.createElement('button');
    editBtn.className = 'btn btn-sm btn-gray';
    editBtn.textContent = 'Editar';
    editBtn.onclick = () => editUser(u.id);
    
    actionsDiv.appendChild(viewBtn);
    actionsDiv.appendChild(editBtn);
    tdActions.appendChild(actionsDiv);
    tr.appendChild(tdActions);
    
    tbody.appendChild(tr);
  });
}
