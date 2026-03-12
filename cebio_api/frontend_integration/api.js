/**
 * CEBIO Brasil - Módulo de Integração com API Backend
 * Substitui o script.js estático por chamadas reais ao backend FastAPI.
 */

// ─── Configuração ─────────────────────────────────────────────────────────────
const API_BASE_URL = "/api";

// ─── Utilitários de Sessão ────────────────────────────────────────────────────
const Auth = {
  getToken: () => localStorage.getItem("cebio_token"),
  setToken: (token) => localStorage.setItem("cebio_token", token),
  removeToken: () => localStorage.removeItem("cebio_token"),

  getUser: () => {
    const u = localStorage.getItem("cebio_user");
    return u ? JSON.parse(u) : {};
  },
  setUser: (user) => localStorage.setItem("cebio_user", JSON.stringify(user)),
  removeUser: () => localStorage.removeItem("cebio_user"),

  isAuthenticated: () => !!localStorage.getItem("cebio_token"),

  isAdmin: () => {
    const u = Auth.getUser();
    return u && u.role === "admin";
  },

  logout: () => {
    Auth.removeToken();
    Auth.removeUser();
    window.location.href = "login.html";
  },

  requireAuth: (role) => {
    if (!Auth.isAuthenticated()) {
      window.location.href = "login.html";
      return false;
    }
    const u = Auth.getUser();
    if (role && u.role !== role && u.role !== "admin") {
      window.location.href = "login.html";
      return false;
    }
    return true;
  },
};

// ─── Cliente HTTP ─────────────────────────────────────────────────────────────
async function apiRequest(method, endpoint, body = null, isFormData = false) {
  const headers = {};
  const token = Auth.getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!isFormData) headers["Content-Type"] = "application/json";

  const options = { method, headers };
  if (body) options.body = isFormData ? body : JSON.stringify(body);

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, options);

    if (response.status === 401) {
      Auth.logout();
      return null;
    }

    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || `Erro ${response.status}`);
      }
      return data;
    }

    if (!response.ok) throw new Error(`Erro ${response.status}`);
    return response;
  } catch (error) {
    console.error(`[API] ${method} ${endpoint}:`, error.message);
    throw error;
  }
}

const api = {
  get: (endpoint) => apiRequest("GET", endpoint),
  post: (endpoint, body) => apiRequest("POST", endpoint, body),
  put: (endpoint, body) => apiRequest("PUT", endpoint, body),
  delete: (endpoint) => apiRequest("DELETE", endpoint),
  upload: (endpoint, formData) => apiRequest("POST", endpoint, formData, true),
};

// ─── Autenticação ─────────────────────────────────────────────────────────────
const AuthAPI = {
  login: async (email, password) => {
    const data = await api.post("/auth/login", { email, password });
    if (data) {
      Auth.setToken(data.access_token);
      Auth.setUser({
        id: data.user_id,
        name: data.name,
        email: data.email,
        role: data.role,
        is_temp_password: data.is_temp_password,
      });
    }
    return data;
  },

  logout: async () => {
    try { await api.post("/auth/logout"); } catch (e) {}
    Auth.logout();
  },

  me: () => api.get("/auth/me"),

  changePassword: (current_password, new_password) =>
    api.post("/auth/change-password", { current_password, new_password }),
};

// ─── Usuários ─────────────────────────────────────────────────────────────────
const UsersAPI = {
  list: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/users${qs ? "?" + qs : ""}`);
  },
  stats: () => api.get("/users/stats"),
  get: (id) => api.get(`/users/${id}`),
  create: (data) => api.post("/users", data),
  update: (id, data) => api.put(`/users/${id}`, data),
  delete: (id) => api.delete(`/users/${id}`),
  getProfile: () => api.get("/users/me/profile"),
  updateProfile: (data) => api.put("/users/me/profile", data),
  resetPassword: (id) => api.post(`/users/${id}/reset-password`),
  batchActivate: (user_ids, activate) =>
    api.post("/users/batch/activate", { user_ids, activate }),
  batchResetPasswords: (user_ids) =>
    api.post("/users/batch/reset-passwords", { user_ids }),
};

// ─── Projetos ─────────────────────────────────────────────────────────────────
const ProjectsAPI = {
  list: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/projects${qs ? "?" + qs : ""}`);
  },
  stats: () => api.get("/projects/stats"),
  get: (id) => api.get(`/projects/${id}`),
  create: (data) => api.post("/projects", data),
  update: (id, data) => api.put(`/projects/${id}`, data),
  delete: (id) => api.delete(`/projects/${id}`),
  submit: (id) => api.post(`/projects/${id}/submit`),
  restore: (id) => api.post(`/projects/${id}/restore`),
  
  updateStatus: (id, status, comment = "") =>
    api.post(`/projects/${id}/status`, { status, comment }),
  
  approve: (id, comment = "Aprovado pelo administrador") =>
    api.post(`/projects/${id}/status`, { status: "aprovado", comment }),
    
  reject: (id, comment = "Rejeitado pelo administrador") =>
    api.post(`/projects/${id}/status`, { status: "rejeitado", comment }),

  batchApprove: (project_ids, comment = "Aprovado em lote") =>
    api.post("/projects/batch/approve", { project_ids, comment }),
    
  batchReject: (project_ids, comment = "Rejeitado em lote") =>
    api.post("/projects/batch/reject", { project_ids, comment }),

  getComments: (id) => api.get(`/projects/${id}/comments`),
  addComment: (id, content) =>
    api.post(`/projects/${id}/comments`, { content }),

  getVersions: (id) => api.get(`/projects/${id}/versions`),

  uploadFile: (id, formData) => api.upload(`/projects/${id}/files/upload`, formData),
  deleteFile: (projectId, fileId) =>
    api.delete(`/projects/${projectId}/files/${fileId}`),

  addLink: (id, data) =>
    api.post(`/projects/${id}/links`, data),
    
  deleteLink: (projectId, linkId) =>
    api.delete(`/projects/${projectId}/links/${linkId}`),
};

// ─── Notificações ─────────────────────────────────────────────────────────────
const NotificationsAPI = {
  list: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/notifications${qs ? "?" + qs : ""}`);
  },
  markRead: (id) => api.post(`/notifications/${id}/read`),
  markAllRead: () => api.post("/notifications/read-all"),
  delete: (id) => api.delete(`/notifications/${id}`),
  massSend: (data) => api.post("/notifications/mass-send", data),
  adminList: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/notifications/admin/all${qs ? "?" + qs : ""}`);
  },
};

// ─── Auditoria ────────────────────────────────────────────────────────────────
const AuditAPI = {
  list: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/audit${qs ? "?" + qs : ""}`);
  },
  stats: () => api.get("/audit/stats"),
};

// ─── Relatórios ───────────────────────────────────────────────────────────────
const ReportsAPI = {
  projects: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/reports/projects${qs ? "?" + qs : ""}`);
  },
  users: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/reports/users${qs ? "?" + qs : ""}`);
  },
};

// ─── Administração ────────────────────────────────────────────────────────────
const AdminAPI = {
  status: () => api.get("/admin/status"),
  health: () => api.get("/admin/health"),
  toggleMaintenance: (enabled, message = "") =>
    api.post("/admin/maintenance", { enabled, message }),
  createBackup: () => api.post("/admin/backup"),
  listConfigs: () => api.get("/admin/config"),
  updateConfig: (key, value) => api.put(`/admin/config/${key}`, { value }),
};

// ─── Utilitários de UI ────────────────────────────────────────────────────────
function showToast(message, type = "success") {
  const colors = { success: "#1a9a4a", error: "#dc3545", warning: "#f59e0b", info: "#3b82f6" };
  const toast = document.createElement("div");
  toast.style.cssText = `position:fixed;bottom:24px;right:24px;z-index:9999;background:${colors[type]};
    color:#fff;padding:12px 20px;border-radius:10px;font-size:14px;font-weight:500;
    box-shadow:0 4px 16px rgba(0,0,0,0.25);max-width:380px;line-height:1.4;
    animation:slideIn .25s ease;`;
  toast.innerHTML = message;
  if (!document.getElementById('cebio-toast-style')) {
    const s = document.createElement('style');
    s.id = 'cebio-toast-style';
    s.textContent = '@keyframes slideIn{from{transform:translateX(120%);opacity:0}to{transform:translateX(0);opacity:1}}';
    document.head.appendChild(s);
  }
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function formatDate(dateStr) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function formatDateOnly(dateStr) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("pt-BR");
}

function formatStatus(s) {
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

// ─── Inicialização Global ─────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", function () {
  const user = Auth.getUser();

  // Preencher dados do usuário em toda a interface
  if (user && user.name) {
    document.querySelectorAll(".user-name, .uname, #header-user-name, #sidebar-user-name").forEach(el => el.textContent = user.name);
    document.querySelectorAll(".user-role, .user-badge-type").forEach(el => {
      const roles = { admin: "Administrador", pesquisador: "Pesquisador", bolsista: "Bolsista" };
      el.textContent = roles[user.role] || user.role;
    });
    document.querySelectorAll(".uinst, #sidebar-user-inst").forEach(el => el.textContent = user.institution || "CEBIO Brasil");
    const avatar = document.getElementById('user-avatar');
    if (avatar) avatar.textContent = (user.name || 'U').charAt(0).toUpperCase();
  }

  // Configurar botões de logout
  document.querySelectorAll(".logout-btn, [data-action='logout']").forEach(btn => {
    btn.addEventListener("click", (e) => { e.preventDefault(); AuthAPI.logout(); });
  });

  // Alerta de senha temporária
  if (user && user.is_temp_password && !window.location.pathname.includes("login")) {
    showToast("⚠️ Altere sua senha temporária no perfil.", "warning");
  }
});

// Exportar para uso global
window.CEBIO = {
  Auth, AuthAPI, UsersAPI, ProjectsAPI, NotificationsAPI, AuditAPI, ReportsAPI, AdminAPI,
  showToast, formatDate, formatDateOnly, formatStatus
};
