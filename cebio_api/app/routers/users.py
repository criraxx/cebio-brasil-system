"""
CEBIO Brasil - Rotas de Usuários
Admin cria usuários; CRUD completo com funções administrativas.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from ..database import get_db
from ..models.user import User
from ..models.notification import Notification
from ..schemas.user import (
    UserAdminCreate, UserAdminUpdate, UserOut, UserList,
    BatchActivateRequest, BatchPasswordResetRequest,
)
from ..utils.security import hash_password, generate_temp_password, require_admin, get_current_user
from ..utils.audit import log_action, get_client_ip

router = APIRouter(prefix="/users", tags=["Usuários"])


# ─── Listagem ─────────────────────────────────────────────────────────────────

@router.get("", response_model=UserList, summary="Listar usuários (admin)")
def list_users(
    search: Optional[str] = Query(None, description="Busca por nome, email ou CPF"),
    role: Optional[str] = Query(None, description="Filtrar por role: admin|pesquisador|bolsista"),
    is_active: Optional[bool] = Query(None, description="Filtrar por status ativo/inativo"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Lista todos os usuários com filtros e paginação. Apenas admins."""
    query = db.query(User)

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                User.name.ilike(term),
                User.email.ilike(term),
                User.cpf.ilike(term),
            )
        )
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page

    return UserList(
        items=[UserOut.model_validate(u) for u in users],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/stats", summary="Estatísticas de usuários (admin)")
def user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Retorna estatísticas gerais de usuários para o dashboard."""
    total = db.query(func.count(User.id)).scalar()
    active = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    inactive = db.query(func.count(User.id)).filter(User.is_active == False).scalar()
    temp_passwords = db.query(func.count(User.id)).filter(
        User.is_temp_password == True, User.is_active == True
    ).scalar()
    by_role = db.query(User.role, func.count(User.id)).group_by(User.role).all()

    return {
        "total": total,
        "active": active,
        "inactive": inactive,
        "temp_passwords": temp_passwords,
        "by_role": {r: c for r, c in by_role},
    }


# ─── Criação (Admin) ──────────────────────────────────────────────────────────

@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED, summary="Criar usuário (admin)")
def create_user(
    request: Request,
    data: UserAdminCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Admin cria um novo usuário com senha temporária.
    Se não informar senha, uma senha aleatória é gerada.
    Retorna a senha temporária para o admin repassar ao usuário.
    """
    # Verifica duplicidade de email
    if db.query(User).filter(User.email == data.email.lower()).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe um usuário com o email '{data.email}'.",
        )

    # Verifica duplicidade de CPF
    if data.cpf and db.query(User).filter(User.cpf == data.cpf).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe um usuário com o CPF '{data.cpf}'.",
        )

    # Gera senha temporária se não fornecida
    plain_password = data.password if data.password else generate_temp_password()

    import uuid
    new_user = User(
        open_id=f"cebio-{uuid.uuid4().hex[:16]}",  # openId obrigatório no banco
        name=data.name,
        email=data.email.lower().strip(),
        cpf=data.cpf,
        hashed_password=hash_password(plain_password),
        role=data.role,
        institution=data.institution,
        is_active=True,
        is_temp_password=True,
        created_by=current_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Notificação de boas-vindas
    notif = Notification(
        user_id=new_user.id,
        title="Bem-vindo ao CEBIO Brasil!",
        message=f"Sua conta foi criada pelo administrador. Use a senha temporária para fazer login e depois altere-a.",
        notification_type="info",
        category="user",
    )
    db.add(notif)
    db.commit()

    log_action(
        db, "USER_CREATED",
        user_id=current_user.id,
        target_user_id=new_user.id,
        details=f"Novo usuário criado: {new_user.name} ({new_user.role})",
        ip_address=get_client_ip(request),
    )

    return {
        "message": "Usuário criado com sucesso.",
        "user": UserOut.model_validate(new_user),
        "temp_password": plain_password,  # Admin deve repassar ao usuário
    }


# ─── Detalhes ─────────────────────────────────────────────────────────────────

@router.get("/{user_id}", response_model=UserOut, summary="Detalhes de um usuário")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return UserOut.model_validate(user)


# ─── Atualização ──────────────────────────────────────────────────────────────

@router.put("/{user_id}", response_model=UserOut, summary="Atualizar usuário (admin)")
def update_user(
    user_id: int,
    request: Request,
    data: UserAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    # Verifica duplicidade de email se alterado
    if data.email and data.email.lower() != user.email:
        if db.query(User).filter(User.email == data.email.lower()).first():
            raise HTTPException(status_code=409, detail="Email já em uso.")
        user.email = data.email.lower().strip()

    if data.name is not None:
        user.name = data.name
    if data.cpf is not None:
        user.cpf = data.cpf
    if data.role is not None:
        user.role = data.role
    if data.institution is not None:
        user.institution = data.institution
    if data.is_active is not None:
        user.is_active = data.is_active

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    log_action(
        db, "USER_UPDATED",
        user_id=current_user.id,
        target_user_id=user.id,
        details=f"Usuário atualizado: {user.name}",
        ip_address=get_client_ip(request),
    )

    return UserOut.model_validate(user)


# ─── Exclusão (soft: desativar) ───────────────────────────────────────────────

@router.delete("/{user_id}", summary="Desativar usuário (admin)")
def deactivate_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode desativar sua própria conta.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()

    log_action(
        db, "USER_DEACTIVATED",
        user_id=current_user.id,
        target_user_id=user.id,
        details=f"Usuário desativado: {user.name}",
        ip_address=get_client_ip(request),
        severity="high",
    )

    return {"message": f"Usuário '{user.name}' desativado com sucesso."}


# ─── Reset de Senha Individual ────────────────────────────────────────────────

@router.post("/{user_id}/reset-password", summary="Reset de senha (admin)")
def reset_password(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin redefine a senha de um usuário para uma senha temporária."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    new_password = generate_temp_password()
    user.hashed_password = hash_password(new_password)
    user.is_temp_password = True
    user.updated_at = datetime.utcnow()
    db.commit()

    # Notificação ao usuário
    notif = Notification(
        user_id=user.id,
        title="Senha redefinida pelo administrador",
        message="Sua senha foi redefinida. Faça login com a nova senha temporária e altere-a imediatamente.",
        notification_type="warning",
        category="user",
    )
    db.add(notif)
    db.commit()

    log_action(
        db, "PASSWORD_RESET",
        user_id=current_user.id,
        target_user_id=user.id,
        details=f"Senha redefinida para: {user.name}",
        ip_address=get_client_ip(request),
    )

    return {
        "message": f"Senha de '{user.name}' redefinida com sucesso.",
        "temp_password": new_password,
    }


# ─── Ações em Lote ────────────────────────────────────────────────────────────

@router.post("/batch/activate", summary="Ativar/desativar usuários em lote (admin)")
def batch_activate(
    request: Request,
    data: BatchActivateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Ativa ou desativa múltiplos usuários de uma vez."""
    if not data.user_ids:
        raise HTTPException(status_code=400, detail="Informe ao menos um user_id.")

    # Não permite desativar a si mesmo
    if not data.activate and current_user.id in data.user_ids:
        raise HTTPException(status_code=400, detail="Você não pode desativar sua própria conta.")

    users = db.query(User).filter(User.id.in_(data.user_ids)).all()
    if not users:
        raise HTTPException(status_code=404, detail="Nenhum usuário encontrado.")

    action_verb = "ativado" if data.activate else "desativado"
    for user in users:
        user.is_active = data.activate
        user.updated_at = datetime.utcnow()

    db.commit()

    action_key = "BATCH_ACTIVATED" if data.activate else "USER_DEACTIVATED"
    log_action(
        db, action_key,
        user_id=current_user.id,
        details=f"{len(users)} usuários {action_verb}s em lote: {[u.name for u in users]}",
        ip_address=get_client_ip(request),
    )

    return {
        "message": f"{len(users)} usuário(s) {action_verb}(s) com sucesso.",
        "affected_ids": [u.id for u in users],
    }


@router.post("/batch/reset-passwords", summary="Reset de senhas em lote (admin)")
def batch_reset_passwords(
    request: Request,
    data: BatchPasswordResetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Redefine senhas temporárias para múltiplos usuários de uma vez."""
    if not data.user_ids:
        raise HTTPException(status_code=400, detail="Informe ao menos um user_id.")

    users = db.query(User).filter(User.id.in_(data.user_ids)).all()
    if not users:
        raise HTTPException(status_code=404, detail="Nenhum usuário encontrado.")

    results = []
    for user in users:
        new_password = generate_temp_password()
        user.hashed_password = hash_password(new_password)
        user.is_temp_password = True
        user.updated_at = datetime.utcnow()
        results.append({"user_id": user.id, "name": user.name, "temp_password": new_password})

        notif = Notification(
            user_id=user.id,
            title="Senha redefinida pelo administrador",
            message="Sua senha foi redefinida. Faça login com a nova senha temporária e altere-a.",
            notification_type="warning",
            category="user",
        )
        db.add(notif)

    db.commit()

    log_action(
        db, "BATCH_PASSWORD_RESET",
        user_id=current_user.id,
        details=f"Reset de senha em lote para {len(users)} usuários",
        ip_address=get_client_ip(request),
        severity="high",
    )

    return {
        "message": f"Senhas redefinidas para {len(users)} usuário(s).",
        "results": results,
    }


# ─── Perfil do próprio usuário ────────────────────────────────────────────────

@router.get("/me/profile", response_model=UserOut, summary="Obter próprio perfil")
def get_own_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna os dados do perfil do usuário autenticado."""
    return UserOut.model_validate(current_user)


@router.put("/me/profile", response_model=UserOut, summary="Atualizar próprio perfil")
def update_own_profile(
    request: Request,
    data: UserAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permite ao usuário atualizar seu próprio nome e instituição (não pode alterar role)."""
    if data.name is not None and data.name.strip():
        current_user.name = data.name.strip()
    if data.institution is not None:
        current_user.institution = data.institution
    if data.cpf is not None:
        current_user.cpf = data.cpf
    # Não permite alterar role, email ou status pelo próprio perfil

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)

    log_action(
        db, "USER_UPDATED",
        user_id=current_user.id,
        details="Usuário atualizou o próprio perfil",
        ip_address=get_client_ip(request),
    )

    return UserOut.model_validate(current_user)



# ─── Gerenciamento Avançado de Usuários (Admin) ──────────────────────────────

@router.get("/{user_id}/details", summary="Detalhes completos do usuário (admin)")
def get_user_details(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Retorna informações detalhadas de um usuário para o painel admin.
    Inclui: dados básicos, estatísticas, projetos, logs de auditoria.
    """
    from ..models.project import Project
    from ..models.log import AuditLog
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    # Contar projetos
    project_count = db.query(func.count(Project.id)).filter(
        Project.owner_id == user_id,
        Project.is_deleted == False
    ).scalar()
    
    # Projetos por status
    projects_by_status = db.query(Project.status, func.count(Project.id)).filter(
        Project.owner_id == user_id,
        Project.is_deleted == False
    ).group_by(Project.status).all()
    
    # Contar atividades (logs de auditoria)
    activity_count = db.query(func.count(AuditLog.id)).filter(
        AuditLog.user_id == user_id
    ).scalar()
    
    # Últimos logins (últimos 10 logs de LOGIN)
    recent_logins = db.query(AuditLog).filter(
        AuditLog.user_id == user_id,
        AuditLog.action == "USER_LOGIN"
    ).order_by(AuditLog.timestamp.desc()).limit(10).all()
    
    login_history = []
    for log in recent_logins:
        login_history.append({
            "timestamp": log.timestamp,
            "ip_address": log.ip_address,
            "details": log.details
        })
    
    # Últimas atividades (últimos 20 logs)
    recent_activities = db.query(AuditLog).filter(
        AuditLog.user_id == user_id
    ).order_by(AuditLog.timestamp.desc()).limit(20).all()
    
    activities = []
    for log in recent_activities:
        activities.append({
            "id": log.id,
            "action": log.action,
            "category": log.category,
            "severity": log.severity,
            "details": log.details,
            "ip_address": log.ip_address,
            "timestamp": log.timestamp
        })
    
    return {
        "user": UserOut.model_validate(user),
        "statistics": {
            "total_projects": project_count,
            "projects_by_status": {s: c for s, c in projects_by_status},
            "total_activities": activity_count,
            "login_count": len(login_history)
        },
        "login_history": login_history,
        "recent_activities": activities
    }


@router.get("/{user_id}/projects", summary="Projetos do usuário (admin)")
def get_user_projects(
    user_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Lista todos os projetos de um usuário específico."""
    from ..models.project import Project
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    query = db.query(Project).filter(
        Project.owner_id == user_id,
        Project.is_deleted == False
    )
    
    total = query.count()
    projects = query.order_by(Project.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    items = []
    for p in projects:
        items.append({
            "id": p.id,
            "title": p.title,
            "category": p.category,
            "status": p.status,
            "created_at": p.created_at,
            "submitted_at": p.submitted_at,
            "reviewed_at": p.reviewed_at
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }


@router.post("/{user_id}/suspend", summary="Suspender usuário (admin)")
def suspend_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Suspende temporariamente um usuário."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode suspender a si mesmo.")
    
    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()
    
    log_action(
        db, "USER_SUSPENDED",
        user_id=current_user.id,
        details=f"Usuário '{user.name}' (ID: {user.id}) foi suspenso",
        ip_address=get_client_ip(request),
        severity="high"
    )
    
    # Notificar usuário
    notif = Notification(
        user_id=user.id,
        title="Conta Suspensa",
        message="Sua conta foi suspensa temporariamente. Entre em contato com o administrador.",
        notification_type="error",
        category="admin"
    )
    db.add(notif)
    db.commit()
    
    return {"message": f"Usuário '{user.name}' suspenso com sucesso."}


@router.post("/{user_id}/reactivate", summary="Reativar usuário (admin)")
def reactivate_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Reativa um usuário suspenso."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    user.is_active = True
    user.updated_at = datetime.utcnow()
    db.commit()
    
    log_action(
        db, "USER_REACTIVATED",
        user_id=current_user.id,
        details=f"Usuário '{user.name}' (ID: {user.id}) foi reativado",
        ip_address=get_client_ip(request),
        severity="medium"
    )
    
    # Notificar usuário
    notif = Notification(
        user_id=user.id,
        title="Conta Reativada",
        message="Sua conta foi reativada. Você já pode acessar o sistema normalmente.",
        notification_type="success",
        category="admin"
    )
    db.add(notif)
    db.commit()
    
    return {"message": f"Usuário '{user.name}' reativado com sucesso."}


@router.post("/{user_id}/change-email", summary="Alterar email do usuário (admin)")
def change_user_email(
    user_id: int,
    request: Request,
    new_email: str = Query(..., description="Novo email"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Altera o email de um usuário."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    # Verificar se email já existe
    existing = db.query(User).filter(User.email == new_email, User.id != user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Este email já está em uso.")
    
    old_email = user.email
    user.email = new_email
    user.updated_at = datetime.utcnow()
    db.commit()
    
    log_action(
        db, "USER_EMAIL_CHANGED",
        user_id=current_user.id,
        details=f"Email do usuário '{user.name}' alterado de '{old_email}' para '{new_email}'",
        ip_address=get_client_ip(request),
        severity="high"
    )
    
    # Notificar usuário
    notif = Notification(
        user_id=user.id,
        title="Email Alterado",
        message=f"Seu email foi alterado para {new_email}. Use este email para fazer login.",
        notification_type="warning",
        category="admin"
    )
    db.add(notif)
    db.commit()
    
    return {"message": f"Email alterado de '{old_email}' para '{new_email}'."}


@router.post("/{user_id}/send-notification", summary="Enviar notificação para usuário (admin)")
def send_user_notification(
    user_id: int,
    request: Request,
    title: str = Query(..., description="Título da notificação"),
    message: str = Query(..., description="Mensagem"),
    notification_type: str = Query("info", description="Tipo: info|success|warning|error"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Envia uma notificação direta para um usuário."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    notif = Notification(
        user_id=user.id,
        title=title,
        message=message,
        notification_type=notification_type,
        category="admin"
    )
    db.add(notif)
    db.commit()
    
    log_action(
        db, "NOTIFICATION_SENT_TO_USER",
        user_id=current_user.id,
        details=f"Notificação enviada para '{user.name}': {title}",
        ip_address=get_client_ip(request)
    )
    
    return {"message": f"Notificação enviada para '{user.name}'."}


@router.get("/{user_id}/export/json", summary="Exportar dados do usuário em JSON (admin)")
def export_user_json(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Exporta todos os dados de um usuário em formato JSON."""
    import json
    import io
    from fastapi.responses import StreamingResponse
    from ..models.project import Project
    from ..models.log import AuditLog
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    # Coletar dados
    projects = db.query(Project).filter(Project.owner_id == user_id).all()
    logs = db.query(AuditLog).filter(AuditLog.user_id == user_id).order_by(AuditLog.timestamp.desc()).limit(1000).all()
    
    data = {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "cpf": user.cpf,
            "role": user.role,
            "institution": user.institution,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        },
        "projects": [
            {
                "id": p.id,
                "title": p.title,
                "category": p.category,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in projects
        ],
        "activity_logs": [
            {
                "action": l.action,
                "category": l.category,
                "severity": l.severity,
                "details": l.details,
                "timestamp": l.timestamp.isoformat() if l.timestamp else None
            }
            for l in logs
        ],
        "exported_at": datetime.utcnow().isoformat(),
        "exported_by": current_user.name
    }
    
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    filename = f"usuario_{user.id}_{user.name.replace(' ', '_')}_dados.json"
    
    log_action(
        db, "USER_DATA_EXPORTED",
        user_id=current_user.id,
        details=f"Dados do usuário '{user.name}' exportados em JSON",
        severity="medium"
    )
    
    return StreamingResponse(
        io.BytesIO(json_bytes),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{user_id}/export/activities-csv", summary="Exportar atividades em CSV (admin)")
def export_user_activities_csv(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Exporta histórico de atividades do usuário em CSV."""
    import csv
    import io
    from fastapi.responses import StreamingResponse
    from ..models.log import AuditLog
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    logs = db.query(AuditLog).filter(
        AuditLog.user_id == user_id
    ).order_by(AuditLog.timestamp.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Data/Hora", "Ação", "Categoria", "Severidade", "Detalhes", "IP"])
    
    for log in logs:
        writer.writerow([
            log.timestamp.strftime("%d/%m/%Y %H:%M:%S") if log.timestamp else "",
            log.action,
            log.category or "",
            log.severity or "",
            log.details or "",
            log.ip_address or ""
        ])
    
    output.seek(0)
    filename = f"usuario_{user.id}_{user.name.replace(' ', '_')}_atividades.csv"
    
    log_action(
        db, "USER_ACTIVITIES_EXPORTED",
        user_id=current_user.id,
        details=f"Atividades do usuário '{user.name}' exportadas em CSV"
    )
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )



@router.get("/search/cpf/{cpf}", summary="Buscar usuário por CPF")
def search_user_by_cpf(
    cpf: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Busca um usuário pelo CPF. Retorna dados básicos se encontrado."""
    # Limpar CPF (remover pontos e traços)
    cpf_clean = cpf.replace(".", "").replace("-", "").replace("/", "")
    
    user = db.query(User).filter(User.cpf == cpf_clean).first()
    
    if not user:
        return {"found": False, "message": "Usuário não encontrado"}
    
    return {
        "found": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "cpf": user.cpf,
            "institution": user.institution,
            "role": user.role
        }
    }
