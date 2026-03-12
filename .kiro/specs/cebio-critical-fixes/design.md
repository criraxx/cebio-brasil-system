# Design Document

## Overview

Este documento descreve o design técnico para correção de 10 falhas críticas identificadas na auditoria do sistema CEBIO Brasil. As correções são organizadas em três grupos prioritários:

**Grupo 1 - CRÍTICO (Bloqueadores):**
- Download de arquivos (Req 1)
- Gestão de senhas temporárias (Req 2)
- Troca de senha obrigatória (Req 3)

**Grupo 2 - ALTO (Funcionalidades Essenciais):**
- Restauração de versões (Req 4)
- Proteção de dados sensíveis (Req 5)
- Histórico de auditoria (Req 6)

**Grupo 3 - MÉDIO (Melhorias de UX e Performance):**
- Feedback de operações (Req 7)
- Geração de relatórios PDF (Req 8)
- Notificações em massa (Req 9)
- Modo manutenção (Req 10)

O design mantém compatibilidade com a arquitetura existente (FastAPI + SQLAlchemy + HTML/JS) e reutiliza componentes como sistema de auditoria e notificações.

## Architecture

### Backend Architecture

```
cebio_api/app/
├── routers/
│   ├── files.py          # NOVO: Download de arquivos
│   ├── auth.py           # MODIFICADO: Troca de senha
│   ├── users.py          # MODIFICADO: Criação com senha temporária
│   ├── projects.py       # MODIFICADO: Restauração de versões
│   ├── reports.py        # MODIFICADO: Geração de PDF
│   ├── notifications.py  # MODIFICADO: Processamento em lote
│   └── admin.py          # MODIFICADO: Modo manutenção
├── schemas/
│   ├── file.py           # NOVO: Schemas de arquivo
│   ├── user.py           # MODIFICADO: Remover hashed_password
│   └── auth.py           # MODIFICADO: Adicionar requires_password_change
├── models/
│   ├── file.py           # NOVO: Model de arquivo
│   └── user.py           # MODIFICADO: Adicionar requires_password_change
└── utils/
    ├── files.py          # NOVO: Validação e storage de arquivos
    └── pdf.py            # NOVO: Geração de PDF
```

### Frontend Architecture

```
cebio_frontend_serve/
├── components/
│   ├── toast.js          # NOVO: Sistema unificado de notificações
│   ├── loading.js        # NOVO: Indicadores de loading
│   └── password-modal.js # NOVO: Modal de troca de senha
├── api.js                # MODIFICADO: Tratamento de erros melhorado
├── admin-*.html          # MODIFICADO: Exibir senha temporária
├── pesquisador-*.html    # MODIFICADO: Links de download
└── bolsista-*.html       # MODIFICADO: Links de download
```

### Data Flow

**Download de Arquivos:**
```
User clicks download → Frontend GET /files/{uuid} → Backend validates permissions
→ Backend streams file → Frontend initiates download
```

**Criação de Usuário:**
```
Admin submits form → Backend generates temp password → Backend creates user
→ Backend returns {user, temporary_password} → Frontend shows modal with password
```

**Troca de Senha:**
```
User logs in → Backend returns {requires_password_change: true}
→ Frontend shows modal → User submits new password → Backend validates & updates
→ Backend sets requires_password_change=false → Frontend allows navigation
```

**Restauração de Versão:**
```
User selects version → Frontend POST /projects/{id}/restore/{version_id}
→ Backend creates backup version → Backend copies historical data
→ Backend logs operation → Frontend reloads project data
```

## Components and Interfaces

### 1. File Download System

**Backend Components:**

```python
# models/file.py
class File(Base):
    id: int
    uuid: str  # UUID para acesso público
    original_filename: str
    mime_type: str
    size_bytes: int
    storage_path: str
    project_id: int
    uploaded_by: int
    uploaded_at: datetime
    
# schemas/file.py
class FileResponse(BaseModel):
    uuid: str
    original_filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime
    
# routers/files.py
@router.get("/files/{file_uuid}")
async def download_file(
    file_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Buscar arquivo por UUID
    # Validar permissões (usuário tem acesso ao projeto?)
    # Retornar FileResponse com StreamingResponse
```

**Frontend Components:**

```javascript
// Renderizar links de download
function renderFileLinks(files) {
    return files.map(file => `
        <a href="/api/files/${file.uuid}" 
           download="${file.original_filename}"
           class="file-link">
            <i class="icon-download"></i>
            ${file.original_filename}
            (${formatFileSize(file.size_bytes)})
        </a>
    `).join('');
}

// Iniciar download
async function downloadFile(fileUuid, filename) {
    showLoading();
    try {
        const response = await fetch(`/api/files/${fileUuid}`);
        if (!response.ok) throw new Error('Download failed');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(url);
        
        showToast('Download concluído', 'success');
    } catch (error) {
        showToast('Erro ao baixar arquivo', 'error');
    } finally {
        hideLoading();
    }
}
```

### 2. Password Management System

**Backend Components:**

```python
# models/user.py (adicionar campo)
class User(Base):
    # ... campos existentes
    requires_password_change: bool = True  # Default true para novos usuários
    
# schemas/user.py
class UserCreate(BaseModel):
    username: str
    email: str
    role: str
    # Senha não é fornecida, será gerada
    
class UserCreateResponse(BaseModel):
    user: UserResponse
    temporary_password: str  # Retornado apenas na criação
    
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    requires_password_change: bool
    # hashed_password REMOVIDO
    
# routers/users.py
@router.post("/users", response_model=UserCreateResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # Gerar senha temporária aleatória (12 caracteres)
    temp_password = generate_secure_password()
    
    # Criar usuário com requires_password_change=True
    user = User(
        **user_data.dict(),
        hashed_password=hash_password(temp_password),
        requires_password_change=True
    )
    db.add(user)
    db.commit()
    
    # Registrar auditoria
    log_action(db, current_user.id, "user_created", user.id)
    
    # Enviar email se configurado
    if email_configured():
        send_temp_password_email(user.email, temp_password)
    
    return UserCreateResponse(
        user=UserResponse.from_orm(user),
        temporary_password=temp_password
    )
```

**Frontend Components:**

```javascript
// Modal de exibição de senha temporária
function showTemporaryPasswordModal(username, password) {
    const modal = `
        <div class="modal" id="temp-password-modal">
            <div class="modal-content">
                <h2>Usuário Criado com Sucesso</h2>
                <p>Usuário: <strong>${username}</strong></p>
                <p>Senha temporária:</p>
                <div class="password-display">
                    <code id="temp-password">${password}</code>
                    <button onclick="copyPassword()">
                        <i class="icon-copy"></i> Copiar
                    </button>
                </div>
                <div class="alert alert-warning">
                    <i class="icon-warning"></i>
                    Esta senha não será exibida novamente. 
                    Certifique-se de copiá-la e enviá-la ao usuário.
                </div>
                <button onclick="closeModal()">Entendi</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modal);
}

function copyPassword() {
    const password = document.getElementById('temp-password').textContent;
    navigator.clipboard.writeText(password);
    showToast('Senha copiada!', 'success');
}

// Criar usuário
async function createUser(userData) {
    showLoading();
    try {
        const response = await apiCall('/users', 'POST', userData);
        showTemporaryPasswordModal(
            response.user.username, 
            response.temporary_password
        );
        return response.user;
    } catch (error) {
        showToast('Erro ao criar usuário', 'error');
    } finally {
        hideLoading();
    }
}
```

### 3. Password Change System

**Backend Components:**

```python
# schemas/auth.py
class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
    requires_password_change: bool  # NOVO
    
class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Senha deve ter no mínimo 8 caracteres')
        if not any(c.isdigit() for c in v):
            raise ValueError('Senha deve conter pelo menos um número')
        if not any(c.isalpha() for c in v):
            raise ValueError('Senha deve conter pelo menos uma letra')
        return v
        
# routers/auth.py
@router.post("/auth/login", response_model=LoginResponse)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(401, "Credenciais inválidas")
    
    token = create_access_token(user.id)
    
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.from_orm(user),
        requires_password_change=user.requires_password_change
    )

@router.post("/auth/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validar senha atual
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(400, "Senha atual incorreta")
    
    # Atualizar senha
    current_user.hashed_password = hash_password(request.new_password)
    current_user.requires_password_change = False
    db.commit()
    
    # Registrar auditoria
    log_action(db, current_user.id, "password_changed", current_user.id)
    
    return {"message": "Senha alterada com sucesso"}
```

**Frontend Components:**

```javascript
// Verificar necessidade de troca de senha após login
async function handleLogin(credentials) {
    showLoading();
    try {
        const response = await apiCall('/auth/login', 'POST', credentials);
        
        // Salvar token
        localStorage.setItem('token', response.access_token);
        localStorage.setItem('user', JSON.stringify(response.user));
        
        // Verificar se precisa trocar senha
        if (response.requires_password_change) {
            showPasswordChangeModal(true); // Modal obrigatório
            return;
        }
        
        // Redirecionar para dashboard
        redirectToDashboard(response.user.role);
    } catch (error) {
        showToast('Erro ao fazer login', 'error');
    } finally {
        hideLoading();
    }
}

// Modal de troca de senha obrigatória
function showPasswordChangeModal(mandatory = false) {
    const modal = `
        <div class="modal modal-mandatory" id="password-change-modal">
            <div class="modal-content">
                <h2>Troca de Senha ${mandatory ? 'Obrigatória' : ''}</h2>
                ${mandatory ? '<p class="alert alert-info">Você precisa trocar sua senha temporária antes de continuar.</p>' : ''}
                <form id="password-change-form">
                    <div class="form-group">
                        <label>Senha Atual</label>
                        <input type="password" name="current_password" required>
                    </div>
                    <div class="form-group">
                        <label>Nova Senha</label>
                        <input type="password" name="new_password" required 
                               minlength="8" pattern=".*[0-9].*[a-zA-Z].*|.*[a-zA-Z].*[0-9].*">
                        <small>Mínimo 8 caracteres, incluindo letras e números</small>
                    </div>
                    <div class="form-group">
                        <label>Confirmar Nova Senha</label>
                        <input type="password" name="confirm_password" required>
                    </div>
                    <button type="submit">Alterar Senha</button>
                    ${!mandatory ? '<button type="button" onclick="closeModal()">Cancelar</button>' : ''}
                </form>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modal);
    
    // Impedir fechamento se obrigatório
    if (mandatory) {
        document.querySelector('.modal').classList.add('no-close');
    }
    
    // Handler do formulário
    document.getElementById('password-change-form').addEventListener('submit', handlePasswordChange);
}

async function handlePasswordChange(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    
    const currentPassword = formData.get('current_password');
    const newPassword = formData.get('new_password');
    const confirmPassword = formData.get('confirm_password');
    
    // Validar confirmação
    if (newPassword !== confirmPassword) {
        showToast('As senhas não coincidem', 'error');
        return;
    }
    
    showLoading();
    try {
        await apiCall('/auth/change-password', 'POST', {
            current_password: currentPassword,
            new_password: newPassword
        });
        
        showToast('Senha alterada com sucesso!', 'success');
        closeModal();
        
        // Atualizar flag no localStorage
        const user = JSON.parse(localStorage.getItem('user'));
        user.requires_password_change = false;
        localStorage.setItem('user', JSON.stringify(user));
        
        // Redirecionar se era obrigatório
        if (document.querySelector('.modal-mandatory')) {
            redirectToDashboard(user.role);
        }
    } catch (error) {
        showToast(error.message || 'Erro ao alterar senha', 'error');
    } finally {
        hideLoading();
    }
}
```

### 4. Version Restoration System

**Backend Components:**

```python
# routers/projects.py
@router.post("/projects/{project_id}/restore/{version_id}")
async def restore_project_version(
    project_id: int,
    version_id: int,
    current_user: User = Depends(require_pesquisador_or_admin),
    db: Session = Depends(get_db)
):
    # Buscar projeto e versão
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Projeto não encontrado")
    
    version = db.query(ProjectVersion).filter(
        ProjectVersion.id == version_id,
        ProjectVersion.project_id == project_id
    ).first()
    if not version:
        raise HTTPException(404, "Versão não encontrada")
    
    # Validar permissões
    if not can_edit_project(current_user, project):
        raise HTTPException(403, "Sem permissão para editar este projeto")
    
    # Criar backup da versão atual antes de restaurar
    backup_version = ProjectVersion(
        project_id=project.id,
        title=project.title,
        description=project.description,
        status=project.status,
        data=project.data,
        created_by=current_user.id,
        created_at=datetime.utcnow(),
        version_note=f"Backup automático antes de restaurar versão {version_id}"
    )
    db.add(backup_version)
    
    # Restaurar dados da versão histórica
    project.title = version.title
    project.description = version.description
    project.status = version.status
    project.data = version.data
    project.updated_at = datetime.utcnow()
    project.updated_by = current_user.id
    
    db.commit()
    
    # Registrar auditoria
    log_action(
        db, 
        current_user.id, 
        "project_version_restored",
        project.id,
        details={"version_id": version_id, "backup_version_id": backup_version.id}
    )
    
    return {
        "message": "Versão restaurada com sucesso",
        "backup_version_id": backup_version.id
    }
```

**Frontend Components:**

```javascript
// Listar versões com botão de restaurar
function renderVersionHistory(versions) {
    return versions.map(version => `
        <div class="version-item">
            <div class="version-info">
                <strong>${version.version_note || 'Versão sem nota'}</strong>
                <span class="version-date">${formatDate(version.created_at)}</span>
                <span class="version-author">por ${version.created_by_name}</span>
            </div>
            <button onclick="restoreVersion(${version.id})" 
                    class="btn-restore">
                <i class="icon-restore"></i> Restaurar
            </button>
        </div>
    `).join('');
}

// Restaurar versão com confirmação
async function restoreVersion(versionId) {
    const confirmed = confirm(
        'Tem certeza que deseja restaurar esta versão? ' +
        'A versão atual será salva como backup.'
    );
    
    if (!confirmed) return;
    
    showLoading();
    try {
        const projectId = getCurrentProjectId();
        await apiCall(`/projects/${projectId}/restore/${versionId}`, 'POST');
        
        showToast('Versão restaurada com sucesso!', 'success');
        
        // Recarregar dados do projeto
        await loadProjectDetails(projectId);
        await loadVersionHistory(projectId);
    } catch (error) {
        showToast('Erro ao restaurar versão', 'error');
    } finally {
        hideLoading();
    }
}
```

### 5. Security - Password Hash Protection

**Backend Components:**

```python
# schemas/user.py (atualizar)
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    requires_password_change: bool
    created_at: datetime
    
    class Config:
        orm_mode = True
        # Excluir explicitamente hashed_password
        fields = {'hashed_password': {'exclude': True}}

# Alternativa: usar from_orm customizado
@classmethod
def from_orm(cls, obj):
    # Garantir que hashed_password nunca seja incluído
    data = {
        'id': obj.id,
        'username': obj.username,
        'email': obj.email,
        'role': obj.role,
        'requires_password_change': obj.requires_password_change,
        'created_at': obj.created_at
    }
    return cls(**data)

# routers/auth.py (atualizar /auth/me)
@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    return UserResponse.from_orm(current_user)

# routers/users.py (atualizar listagem)
@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    return [UserResponse.from_orm(user) for user in users]
```

### 6. Audit History Improvements

**Backend Components:**

```python
# schemas/log.py
class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    action: str
    target_type: str
    target_id: int
    details: dict
    timestamp: datetime
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()  # Formato ISO consistente
        }

# routers/audit.py
@router.get("/audit/logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    return [AuditLogResponse.from_orm(log) for log in logs]
```

**Frontend Components:**

```javascript
// Formatação consistente de datas
function formatDate(isoString) {
    try {
        const date = new Date(isoString);
        if (isNaN(date.getTime())) {
            // Data inválida, retornar original
            return isoString;
        }
        return date.toLocaleString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        // Em caso de erro, retornar original sem quebrar
        return isoString;
    }
}

// Renderizar histórico de auditoria
function renderAuditLog(logs) {
    // Remover dados mock, usar apenas dados reais
    return logs.map(log => `
        <tr>
            <td>${formatDate(log.timestamp)}</td>
            <td>${log.user_name}</td>
            <td>${log.action}</td>
            <td>${log.target_type}</td>
            <td>${log.details ? JSON.stringify(log.details) : '-'}</td>
        </tr>
    `).join('');
}
```

### 7. Unified Feedback System

**Frontend Components:**

```javascript
// components/toast.js - Sistema unificado de notificações
class ToastManager {
    constructor() {
        this.container = null;
        this.init();
    }
    
    init() {
        if (!document.getElementById('toast-container')) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('toast-container');
        }
    }
    
    show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const icon = this.getIcon(type);
        toast.innerHTML = `
            <i class="${icon}"></i>
            <span>${message}</span>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        this.container.appendChild(toast);
        
        // Auto-remover após duração
        setTimeout(() => {
            toast.classList.add('toast-fade-out');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
    
    getIcon(type) {
        const icons = {
            success: 'icon-check-circle',
            error: 'icon-x-circle',
            warning: 'icon-alert-triangle',
            info: 'icon-info'
        };
        return icons[type] || icons.info;
    }
}

// Instância global
const toastManager = new ToastManager();

// Funções helper
function showToast(message, type = 'info') {
    toastManager.show(message, type);
}

// components/loading.js - Indicadores de loading
class LoadingManager {
    constructor() {
        this.overlay = null;
        this.counter = 0;
        this.init();
    }
    
    init() {
        if (!document.getElementById('loading-overlay')) {
            this.overlay = document.createElement('div');
            this.overlay.id = 'loading-overlay';
            this.overlay.className = 'loading-overlay';
            this.overlay.innerHTML = `
                <div class="loading-spinner">
                    <div class="spinner"></div>
                    <p>Carregando...</p>
                </div>
            `;
            document.body.appendChild(this.overlay);
        } else {
            this.overlay = document.getElementById('loading-overlay');
        }
    }
    
    show() {
        this.counter++;
        this.overlay.classList.add('active');
    }
    
    hide() {
        this.counter = Math.max(0, this.counter - 1);
        if (this.counter === 0) {
            this.overlay.classList.remove('active');
        }
    }
}

// Instância global
const loadingManager = new LoadingManager();

function showLoading() {
    loadingManager.show();
}

function hideLoading() {
    loadingManager.hide();
}
```

**API Client with Enhanced Error Handling:**

```javascript
// api.js (atualizar)
async function apiCall(endpoint, method = 'GET', data = null) {
    const token = localStorage.getItem('token');
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
        }
    };
    
    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`/api${endpoint}`, options);
        
        // Verificar modo manutenção
        if (response.status === 503) {
            window.location.href = '/maintenance.html';
            throw new Error('Sistema em manutenção');
        }
        
        // Tratar erros HTTP
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `Erro ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        // Erro de rede
        if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
            throw new Error('Erro de conexão. Verifique sua internet.');
        }
        
        // Timeout
        if (error.name === 'AbortError') {
            throw new Error('A operação demorou muito. Tente novamente.');
        }
        
        throw error;
    }
}
```

### 8. PDF Report Generation

**Backend Components:**

```python
# utils/pdf.py
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from io import BytesIO

def generate_project_pdf(project: Project, versions: List[ProjectVersion]) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Título
    story.append(Paragraph(f"Relatório do Projeto: {project.title}", styles['Title']))
    story.append(Spacer(1, 12))
    
    # Informações básicas
    info_data = [
        ['Status:', project.status],
        ['Criado em:', project.created_at.strftime('%d/%m/%Y')],
        ['Atualizado em:', project.updated_at.strftime('%d/%m/%Y')],
        ['Responsável:', project.owner.username]
    ]
    info_table = Table(info_data)
    story.append(info_table)
    story.append(Spacer(1, 12))
    
    # Descrição
    story.append(Paragraph("Descrição:", styles['Heading2']))
    story.append(Paragraph(project.description or 'Sem descrição', styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Histórico de versões
    if versions:
        story.append(Paragraph("Histórico de Versões:", styles['Heading2']))
        version_data = [['Data', 'Autor', 'Nota']]
        for v in versions:
            version_data.append([
                v.created_at.strftime('%d/%m/%Y %H:%M'),
                v.created_by_user.username,
                v.version_note or '-'
            ])
        version_table = Table(version_data)
        story.append(version_table)
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# routers/reports.py
@router.get("/reports/project/{project_id}/pdf")
async def generate_project_report(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Projeto não encontrado")
    
    if not can_view_project(current_user, project):
        raise HTTPException(403, "Sem permissão para visualizar este projeto")
    
    versions = db.query(ProjectVersion).filter(
        ProjectVersion.project_id == project_id
    ).order_by(ProjectVersion.created_at.desc()).all()
    
    try:
        pdf_buffer = generate_project_pdf(project, versions)
        
        # Registrar auditoria
        log_action(db, current_user.id, "report_generated", project.id)
        
        filename = f"projeto_{project.id}_{project.title[:30]}.pdf"
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar PDF: {str(e)}")
```

**Frontend Components:**

```javascript
// Gerar e baixar PDF
async function generateProjectPDF(projectId) {
    showLoading();
    try {
        const response = await fetch(`/api/reports/project/${projectId}/pdf`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Erro ao gerar PDF');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `projeto_${projectId}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
        
        showToast('PDF gerado com sucesso!', 'success');
    } catch (error) {
        showToast(error.message || 'Erro ao gerar PDF', 'error');
    } finally {
        hideLoading();
    }
}
```

### 9. Batch Notifications

**Backend Components:**

```python
# routers/notifications.py
class BatchNotificationRequest(BaseModel):
    user_ids: List[int]
    title: str
    message: str
    
@router.post("/notifications/batch")
async def send_batch_notifications(
    request: BatchNotificationRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if len(request.user_ids) > 100:
        raise HTTPException(400, "Máximo de 100 usuários por lote")
    
    success_count = 0
    failed_count = 0
    failed_users = []
    
    try:
        # Processar em transação única
        for user_id in request.user_ids:
            try:
                notification = Notification(
                    user_id=user_id,
                    title=request.title,
                    message=request.message,
                    created_by=current_user.id,
                    created_at=datetime.utcnow(),
                    read=False
                )
                db.add(notification)
                success_count += 1
            except Exception as e:
                failed_count += 1
                failed_users.append(user_id)
        
        db.commit()
        
        # Registrar auditoria
        log_action(
            db,
            current_user.id,
            "batch_notification_sent",
            None,
            details={
                "total": len(request.user_ids),
                "success": success_count,
                "failed": failed_count
            }
        )
        
        return {
            "total": len(request.user_ids),
            "success": success_count,
            "failed": failed_count,
            "failed_users": failed_users
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Erro ao enviar notificações: {str(e)}")
```

**Frontend Components:**

```javascript
// Enviar notificações em lote
async function sendBatchNotifications(userIds, title, message) {
    showLoading();
    try {
        const response = await apiCall('/notifications/batch', 'POST', {
            user_ids: userIds,
            title: title,
            message: message
        });
        
        // Exibir resultado
        const successMsg = `${response.success} notificações enviadas com sucesso`;
        const failMsg = response.failed > 0 ? `, ${response.failed} falharam` : '';
        
        showToast(successMsg + failMsg, response.failed > 0 ? 'warning' : 'success');
        
        return response;
    } catch (error) {
        showToast('Erro ao enviar notificações', 'error');
        throw error;
    } finally {
        hideLoading();
    }
}
```

### 10. Maintenance Mode

**Backend Components:**

```python
# routers/admin.py
@router.post("/admin/maintenance")
async def toggle_maintenance_mode(
    enabled: bool,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    system_config = db.query(SystemConfig).first()
    if not system_config:
        system_config = SystemConfig()
        db.add(system_config)
    
    system_config.maintenance_mode = enabled
    db.commit()
    
    log_action(
        db,
        current_user.id,
        "maintenance_mode_toggled",
        None,
        details={"enabled": enabled}
    )
    
    return {"maintenance_mode": enabled}

@router.get("/admin/maintenance")
async def get_maintenance_status(db: Session = Depends(get_db)):
    system_config = db.query(SystemConfig).first()
    return {"maintenance_mode": system_config.maintenance_mode if system_config else False}

# Middleware para verificar modo manutenção
from fastapi import Request
from fastapi.responses import JSONResponse

async def maintenance_middleware(request: Request, call_next):
    # Permitir endpoints de admin e verificação de manutenção
    if request.url.path.startswith('/api/admin/maintenance'):
        return await call_next(request)
    
    db = next(get_db())
    system_config = db.query(SystemConfig).first()
    
    if system_config and system_config.maintenance_mode:
        return JSONResponse(
            status_code=503,
            content={"detail": "Sistema em manutenção"}
        )
    
    return await call_next(request)
```

**Frontend Components:**

```javascript
// Verificar modo manutenção periodicamente
let maintenanceCheckInterval = null;

function startMaintenanceCheck() {
    // Verificar a cada 30 segundos
    maintenanceCheckInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/admin/maintenance');
            const data = await response.json();
            
            if (data.maintenance_mode) {
                handleMaintenanceMode();
            }
        } catch (error) {
            // Ignorar erros de verificação
        }
    }, 30000);
}

function handleMaintenanceMode() {
    // Parar verificações
    if (maintenanceCheckInterval) {
        clearInterval(maintenanceCheckInterval);
    }
    
    // Fazer logout
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    
    // Redirecionar para página de manutenção
    window.location.href = '/maintenance.html';
}

// Iniciar verificação ao carregar página
document.addEventListener('DOMContentLoaded', () => {
    if (localStorage.getItem('token')) {
        startMaintenanceCheck();
    }
});

// maintenance.html
const maintenancePageHTML = `
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Sistema em Manutenção - CEBIO Brasil</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .maintenance-container {
            text-align: center;
            background: white;
            padding: 3rem;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        .maintenance-icon {
            font-size: 4rem;
            margin-bottom: 1rem;
        }
        h1 {
            color: #333;
            margin-bottom: 1rem;
        }
        p {
            color: #666;
            margin-bottom: 2rem;
        }
        .btn-retry {
            background: #667eea;
            color: white;
            border: none;
            padding: 0.75rem 2rem;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1rem;
        }
        .btn-retry:hover {
            background: #5568d3;
        }
    </style>
</head>
<body>
    <div class="maintenance-container">
        <div class="maintenance-icon">🔧</div>
        <h1>Sistema em Manutenção</h1>
        <p>Estamos realizando melhorias no sistema.<br>Por favor, tente novamente em alguns minutos.</p>
        <button class="btn-retry" onclick="checkAndRedirect()">Tentar Novamente</button>
    </div>
    <script>
        async function checkAndRedirect() {
            try {
                const response = await fetch('/api/admin/maintenance');
                const data = await response.json();
                
                if (!data.maintenance_mode) {
                    window.location.href = '/';
                } else {
                    alert('Sistema ainda em manutenção. Tente novamente em alguns minutos.');
                }
            } catch (error) {
                alert('Erro ao verificar status. Tente novamente.');
            }
        }
    </script>
</body>
</html>
`;
```

## Data Models

### File Model

```python
class File(Base):
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, nullable=False)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    storage_path = Column(String(500), nullable=False)
    
    # Relacionamentos
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relações
    project = relationship("Project", back_populates="files")
    uploader = relationship("User")
```

### User Model Updates

```python
class User(Base):
    __tablename__ = "users"
    
    # Campos existentes...
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)
    
    # NOVO: Flag para forçar troca de senha
    requires_password_change = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```


## Correctness Properties

Uma propriedade é uma característica ou comportamento que deve ser verdadeiro em todas as execuções válidas de um sistema - essencialmente, uma declaração formal sobre o que o sistema deve fazer. Propriedades servem como ponte entre especificações legíveis por humanos e garantias de correção verificáveis por máquina.

### Property 1: File Upload Metadata Preservation

*For any* arquivo válido enviado ao sistema, os metadados (nome original, tipo MIME, tamanho) devem ser armazenados corretamente e recuperáveis.

**Validates: Requirements 1.1**

### Property 2: File Download Round Trip

*For any* arquivo enviado por um usuário autenticado, fazer download do arquivo deve retornar conteúdo idêntico ao arquivo original.

**Validates: Requirements 1.2**

### Property 3: Unauthorized File Access Rejection

*For any* usuário sem permissão tentando acessar um arquivo, o sistema deve retornar erro 403.

**Validates: Requirements 1.3**

### Property 4: File Links Completeness

*For any* projeto com arquivos anexados, a interface deve exibir links de download para todos os arquivos.

**Validates: Requirements 1.5**

### Property 5: Temporary Password Generation

*For any* novo usuário criado por admin, o sistema deve gerar uma senha temporária aleatória e retorná-la na resposta.

**Validates: Requirements 2.1, 2.2**

### Property 6: Password Change Flag Initialization

*For any* novo usuário criado, a flag requires_password_change deve ser inicializada como true.

**Validates: Requirements 2.3**

### Property 7: Login Response Includes Password Change Flag

*For any* usuário com requires_password_change=true que faz login, a resposta deve incluir a flag requires_password_change.

**Validates: Requirements 3.1**

### Property 8: Navigation Blocking Until Password Change

*For any* usuário com requires_password_change=true, tentativas de navegação devem ser bloqueadas até que a senha seja trocada.

**Validates: Requirements 3.3**

### Property 9: Password Strength Validation

*For any* senha submetida para troca, senhas fracas (menos de 8 caracteres ou sem letras e números) devem ser rejeitadas.

**Validates: Requirements 3.4**

### Property 10: Password Change Flag Reset

*For any* usuário que troca a senha com sucesso, a flag requires_password_change deve ser atualizada para false.

**Validates: Requirements 3.5**

### Property 11: Password Change Audit Logging

*For any* troca de senha bem-sucedida, deve existir uma entrada correspondente no log de auditoria.

**Validates: Requirements 3.6**

### Property 12: Version Restoration Validation

*For any* solicitação de restauração de versão, versões inválidas ou que não pertencem ao projeto devem ser rejeitadas.

**Validates: Requirements 4.1**

### Property 13: Backup Before Restoration

*For any* restauração de versão autorizada, uma nova versão com dados atuais deve ser criada antes da restauração.

**Validates: Requirements 4.2**

### Property 14: Version Data Integrity

*For any* versão restaurada, os dados do projeto devem ser idênticos aos dados da versão histórica.

**Validates: Requirements 4.3**

### Property 15: Restoration Metadata Preservation

*For any* restauração de versão, metadados de auditoria (quem restaurou, quando, qual versão) devem ser preservados.

**Validates: Requirements 4.4**

### Property 16: Restoration Audit Logging

*For any* operação de restauração concluída, deve existir uma entrada no log de auditoria.

**Validates: Requirements 4.6**

### Property 17: Password Hash Exclusion from All Endpoints

*For any* endpoint que retorna dados de usuário, o campo hashed_password nunca deve estar presente na resposta.

**Validates: Requirements 5.1, 5.2, 5.3**

### Property 18: Consistent Date Formatting

*For any* dados de auditoria retornados pelo backend, todas as datas devem seguir formato ISO consistente.

**Validates: Requirements 6.1**

### Property 19: Frontend Date Display

*For any* data exibida no frontend, deve estar formatada em formato local (DD/MM/YYYY HH:mm).

**Validates: Requirements 6.2**

### Property 20: Critical Operations Audit Logging

*For any* operação crítica (criação, edição, exclusão, restauração), deve existir entrada correspondente no log de auditoria.

**Validates: Requirements 6.5**

### Property 21: Loading Indicator Display

*For any* operação assíncrona iniciada, um indicador de loading deve ser exibido.

**Validates: Requirements 7.1**

### Property 22: Success Toast Display

*For any* operação concluída com sucesso, um toast de sucesso deve ser exibido.

**Validates: Requirements 7.2**

### Property 23: Error Toast Display

*For any* operação que falha, um toast de erro deve ser exibido.

**Validates: Requirements 7.3**

### Property 24: PDF Content Completeness

*For any* relatório PDF gerado, deve conter todos os dados do projeto (título, descrição, datas, responsáveis, status, histórico).

**Validates: Requirements 8.1, 8.2**

### Property 25: PDF Filename Descriptiveness

*For any* PDF gerado, o nome do arquivo deve ser descritivo e incluir identificação do projeto.

**Validates: Requirements 8.3**

### Property 26: PDF Generation Error Handling

*For any* falha na geração de PDF, o backend deve retornar erro descritivo.

**Validates: Requirements 8.5**

### Property 27: PDF Generation Audit Logging

*For any* relatório PDF gerado, deve existir entrada no log de auditoria.

**Validates: Requirements 8.6**

### Property 28: Batch Notification Processing

*For any* notificação em lote enviada para múltiplos usuários, o backend deve processar em transação única.

**Validates: Requirements 9.1**

### Property 29: Batch Notification Summary

*For any* processamento em lote concluído, a resposta deve conter resumo com total, sucessos e falhas.

**Validates: Requirements 9.4**

### Property 30: Maintenance Mode HTTP Status

*For any* requisição quando modo manutenção está ativado, o backend deve retornar status 503.

**Validates: Requirements 10.1**

### Property 31: Maintenance Mode Periodic Check

*For any* usuário logado, o frontend deve verificar modo manutenção periodicamente.

**Validates: Requirements 10.2**

### Property 32: Maintenance Mode Round Trip

*For any* sistema, ativar e depois desativar modo manutenção deve restaurar acesso normal.

**Validates: Requirements 10.5**

### Property 33: Maintenance Mode Logout

*For any* usuário logado quando modo manutenção é detectado, o sistema deve fazer logout automático.

**Validates: Requirements 10.6**


## Error Handling

### Backend Error Handling

**HTTP Status Codes:**
- 200: Operação bem-sucedida
- 400: Dados inválidos (validação falhou)
- 401: Não autenticado
- 403: Sem permissão
- 404: Recurso não encontrado
- 500: Erro interno do servidor
- 503: Sistema em manutenção

**Error Response Format:**
```json
{
    "detail": "Mensagem de erro descritiva",
    "error_code": "OPTIONAL_ERROR_CODE",
    "field_errors": {
        "field_name": ["erro específico do campo"]
    }
}
```

**Exception Handling:**
```python
# Validação de entrada
try:
    validate_password_strength(password)
except ValueError as e:
    raise HTTPException(400, str(e))

# Recursos não encontrados
if not resource:
    raise HTTPException(404, "Recurso não encontrado")

# Permissões
if not has_permission(user, resource):
    raise HTTPException(403, "Sem permissão para acessar este recurso")

# Erros internos
try:
    perform_operation()
except Exception as e:
    logger.error(f"Erro interno: {str(e)}")
    raise HTTPException(500, "Erro interno do servidor")
```

### Frontend Error Handling

**Network Errors:**
```javascript
try {
    const response = await apiCall(endpoint, method, data);
    return response;
} catch (error) {
    if (error.message.includes('conexão')) {
        showToast('Erro de conexão. Verifique sua internet.', 'error');
    } else if (error.message.includes('timeout')) {
        showToast('Operação demorou muito. Tente novamente.', 'error');
    } else {
        showToast(error.message || 'Erro desconhecido', 'error');
    }
    throw error;
}
```

**Validation Errors:**
```javascript
// Validação no frontend antes de enviar
function validateForm(formData) {
    const errors = [];
    
    if (!formData.username || formData.username.length < 3) {
        errors.push('Nome de usuário deve ter no mínimo 3 caracteres');
    }
    
    if (!formData.email || !isValidEmail(formData.email)) {
        errors.push('Email inválido');
    }
    
    if (errors.length > 0) {
        errors.forEach(error => showToast(error, 'error'));
        return false;
    }
    
    return true;
}
```

**Graceful Degradation:**
```javascript
// Tratamento de erro sem quebrar interface
function formatDate(isoString) {
    try {
        const date = new Date(isoString);
        if (isNaN(date.getTime())) {
            return isoString; // Retornar original se inválido
        }
        return date.toLocaleString('pt-BR');
    } catch (error) {
        console.error('Erro ao formatar data:', error);
        return isoString; // Não quebrar a interface
    }
}
```

## Testing Strategy

### Dual Testing Approach

Este projeto utiliza uma abordagem dupla de testes:

1. **Testes Unitários**: Validam exemplos específicos, casos extremos e condições de erro
2. **Testes Baseados em Propriedades**: Validam propriedades universais através de múltiplas entradas geradas

Ambos são complementares e necessários para cobertura abrangente.

### Property-Based Testing

**Framework:** pytest com hypothesis (Python)

**Configuração:**
- Mínimo 100 iterações por teste de propriedade
- Cada teste deve referenciar a propriedade do design
- Tag format: `# Feature: cebio-critical-fixes, Property {number}: {property_text}`

**Exemplo de Teste de Propriedade:**

```python
from hypothesis import given, strategies as st
import pytest

# Feature: cebio-critical-fixes, Property 2: File Download Round Trip
@given(
    file_content=st.binary(min_size=1, max_size=10000),
    filename=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=('Cs',)))
)
@pytest.mark.property_test
def test_file_download_round_trip(client, auth_token, file_content, filename):
    """
    For any arquivo enviado por um usuário autenticado,
    fazer download do arquivo deve retornar conteúdo idêntico ao arquivo original.
    """
    # Upload file
    upload_response = client.post(
        "/api/files/upload",
        files={"file": (filename, file_content)},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert upload_response.status_code == 200
    file_uuid = upload_response.json()["uuid"]
    
    # Download file
    download_response = client.get(
        f"/api/files/{file_uuid}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert download_response.status_code == 200
    
    # Verify content is identical
    assert download_response.content == file_content

# Feature: cebio-critical-fixes, Property 9: Password Strength Validation
@given(
    weak_password=st.one_of(
        st.text(max_size=7),  # Muito curta
        st.text(min_size=8, alphabet=st.characters(whitelist_categories=('Ll', 'Lu'))),  # Só letras
        st.text(min_size=8, alphabet=st.characters(whitelist_categories=('Nd',)))  # Só números
    )
)
@pytest.mark.property_test
def test_weak_password_rejection(client, auth_token, weak_password):
    """
    For any senha submetida para troca, senhas fracas devem ser rejeitadas.
    """
    response = client.post(
        "/api/auth/change-password",
        json={
            "current_password": "ValidPassword123",
            "new_password": weak_password
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 400
    assert "senha" in response.json()["detail"].lower()
```

### Unit Testing

**Framework:** pytest (Python), Jest (JavaScript)

**Foco dos Testes Unitários:**
- Exemplos específicos de uso correto
- Casos extremos (arquivos vazios, strings muito longas)
- Condições de erro (recursos não encontrados, permissões negadas)
- Integração entre componentes

**Exemplo de Teste Unitário:**

```python
def test_create_user_returns_temporary_password(client, admin_token):
    """Teste específico: criação de usuário retorna senha temporária"""
    response = client.post(
        "/api/users",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "role": "bolsista"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "temporary_password" in data
    assert len(data["temporary_password"]) >= 12
    assert data["user"]["requires_password_change"] is True

def test_download_nonexistent_file_returns_404(client, auth_token):
    """Caso extremo: arquivo não existe"""
    response = client.get(
        "/api/files/nonexistent-uuid",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404

def test_unauthorized_file_access_returns_403(client, user_token):
    """Condição de erro: usuário sem permissão"""
    # Criar arquivo como outro usuário
    file_uuid = create_file_as_different_user()
    
    # Tentar acessar sem permissão
    response = client.get(
        f"/api/files/{file_uuid}",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403
```

### Frontend Testing

**Framework:** Jest + Testing Library

**Exemplo:**

```javascript
import { render, screen, fireEvent, waitFor } from '@testing-library/dom';
import { showTemporaryPasswordModal, copyPassword } from './user-management';

describe('Temporary Password Modal', () => {
    test('displays password and copy button', () => {
        showTemporaryPasswordModal('testuser', 'TempPass123');
        
        expect(screen.getByText('testuser')).toBeInTheDocument();
        expect(screen.getByText('TempPass123')).toBeInTheDocument();
        expect(screen.getByText(/não será exibida novamente/i)).toBeInTheDocument();
    });
    
    test('copies password to clipboard', async () => {
        showTemporaryPasswordModal('testuser', 'TempPass123');
        
        const copyButton = screen.getByText(/copiar/i);
        fireEvent.click(copyButton);
        
        await waitFor(() => {
            expect(navigator.clipboard.writeText).toHaveBeenCalledWith('TempPass123');
        });
    });
});
```

### Test Coverage Goals

- Backend: Mínimo 80% de cobertura de código
- Frontend: Mínimo 70% de cobertura de código
- Todas as propriedades de correção devem ter testes de propriedade
- Todos os endpoints críticos devem ter testes unitários
- Todos os fluxos de erro devem ser testados

### Integration Testing

**Cenários de Integração:**

1. **Fluxo Completo de Criação de Usuário:**
   - Admin cria usuário → Senha temporária gerada → Modal exibido → Email enviado

2. **Fluxo Completo de Primeiro Login:**
   - Usuário faz login → Flag detectada → Modal obrigatório → Senha trocada → Navegação liberada

3. **Fluxo Completo de Upload e Download:**
   - Arquivo enviado → Metadados salvos → Link exibido → Download funciona → Conteúdo idêntico

4. **Fluxo Completo de Restauração:**
   - Versão selecionada → Backup criado → Dados restaurados → Auditoria registrada → UI atualizada

### Security Testing

**Testes de Segurança Específicos:**

```python
def test_hashed_password_never_exposed_in_any_endpoint(client, admin_token):
    """Validar que nenhum endpoint expõe hashed_password"""
    endpoints = [
        "/api/auth/me",
        "/api/users",
        "/api/users/1"
    ]
    
    for endpoint in endpoints:
        response = client.get(
            endpoint,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Verificar que hashed_password não está na resposta
        response_text = response.text.lower()
        assert "hashed_password" not in response_text
        assert "password" not in response.json() or "temporary_password" in response.json()
```

### Performance Testing

**Testes de Performance para Notificações em Lote:**

```python
import time

def test_batch_notifications_performance(client, admin_token):
    """Validar que notificações em lote são eficientes"""
    user_ids = list(range(1, 101))  # 100 usuários
    
    start_time = time.time()
    response = client.post(
        "/api/notifications/batch",
        json={
            "user_ids": user_ids,
            "title": "Test",
            "message": "Test message"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    end_time = time.time()
    
    assert response.status_code == 200
    assert end_time - start_time < 5.0  # Deve completar em menos de 5 segundos
```
