"""
CEBIO Brasil - Rotas de Relatórios
Analytics, estatísticas e exportação de dados (admin).
"""
import csv
import io
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from ..database import get_db
from ..models.user import User
from ..models.project import Project, ProjectVersion, ProjectComment
from ..models.log import AuditLog
from ..utils.security import require_admin, get_current_user
from ..utils.audit import log_action, get_client_ip
from ..utils.pdf import generate_project_pdf

router = APIRouter(prefix="/reports", tags=["Relatórios"])


@router.get("/dashboard", summary="Dados completos do dashboard admin")
def dashboard_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Retorna todos os dados necessários para o dashboard administrativo."""
    # Projetos
    total_projects = db.query(func.count(Project.id)).filter(Project.is_deleted == False).scalar()
    by_status = db.query(Project.status, func.count(Project.id)).filter(
        Project.is_deleted == False
    ).group_by(Project.status).all()
    by_category = db.query(Project.category, func.count(Project.id)).filter(
        Project.is_deleted == False
    ).group_by(Project.category).all()

    # Usuários
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    temp_passwords = db.query(func.count(User.id)).filter(
        User.is_temp_password == True, User.is_active == True
    ).scalar()
    by_role = db.query(User.role, func.count(User.id)).group_by(User.role).all()

    # Atividade recente (últimos 10 logs)
    recent_logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10).all()
    recent_activity = []
    for log in recent_logs:
        recent_activity.append({
            "id": log.id,
            "action": log.action,
            "category": log.category,
            "severity": log.severity,
            "details": log.details,
            "user_name": log.user.name if log.user else "Sistema",
            "timestamp": log.timestamp,
        })

    # Projetos recentes
    recent_projects = db.query(Project).filter(
        Project.is_deleted == False
    ).order_by(Project.created_at.desc()).limit(5).all()
    recent_proj_list = []
    for p in recent_projects:
        recent_proj_list.append({
            "id": p.id,
            "title": p.title,
            "status": p.status,
            "category": p.category,
            "owner_name": p.owner.name if p.owner else "",
            "created_at": p.created_at,
        })

    return {
        "projects": {
            "total": total_projects,
            "by_status": {s: c for s, c in by_status},
            "by_category": {cat: c for cat, c in by_category},
            "recent": recent_proj_list,
        },
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users,
            "temp_passwords": temp_passwords,
            "by_role": {r: c for r, c in by_role},
        },
        "recent_activity": recent_activity,
    }


@router.get("/projects", summary="Relatório detalhado de projetos (admin)")
def projects_report(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    period: Optional[str] = Query(None, description="last_month | last_3months | last_year"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Relatório analítico de projetos com filtros."""
    from datetime import timedelta
    query = db.query(Project).filter(Project.is_deleted == False)

    if category:
        query = query.filter(Project.category == category)
    if status:
        query = query.filter(Project.status == status)
    if period:
        now = datetime.utcnow()
        if period == "last_month":
            query = query.filter(Project.created_at >= now - timedelta(days=30))
        elif period == "last_3months":
            query = query.filter(Project.created_at >= now - timedelta(days=90))
        elif period == "last_year":
            query = query.filter(Project.created_at >= now - timedelta(days=365))

    projects = query.order_by(Project.created_at.desc()).all()

    total = len(projects)
    by_status = {}
    by_category = {}
    durations = []

    for p in projects:
        by_status[p.status] = by_status.get(p.status, 0) + 1
        by_category[p.category] = by_category.get(p.category, 0) + 1
        if p.start_date and p.end_date:
            delta = (p.end_date - p.start_date).days
            if delta > 0:
                durations.append(delta)

    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

    items = []
    for p in projects:
        items.append({
            "id": p.id,
            "title": p.title,
            "category": p.category,
            "academic_level": p.academic_level,
            "status": p.status,
            "owner_name": p.owner.name if p.owner else "",
            "duration_days": (p.end_date - p.start_date).days if p.start_date and p.end_date else None,
            "created_at": p.created_at,
            "submitted_at": p.submitted_at,
            "reviewed_at": p.reviewed_at,
        })

    return {
        "total": total,
        "by_status": by_status,
        "by_category": by_category,
        "avg_duration_days": avg_duration,
        "items": items,
    }


@router.get("/users", summary="Relatório de usuários (admin)")
def users_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Relatório analítico de usuários."""
    users = db.query(User).order_by(User.created_at.desc()).all()

    items = []
    for u in users:
        project_count = db.query(func.count(Project.id)).filter(
            Project.owner_id == u.id, Project.is_deleted == False
        ).scalar()
        items.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "is_temp_password": u.is_temp_password,
            "last_login": u.last_login,
            "created_at": u.created_at,
            "project_count": project_count,
        })

    return {
        "total": len(items),
        "items": items,
    }


@router.get("/export/projects", summary="Exportar projetos em CSV (admin)")
def export_projects_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Exporta todos os projetos em formato CSV."""
    projects = db.query(Project).filter(Project.is_deleted == False).order_by(Project.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Título", "Categoria", "Nível Acadêmico", "Status",
        "Autor Principal", "Data Início", "Data Fim", "Duração (dias)",
        "Criado em", "Submetido em", "Revisado em", "Comentário Revisão"
    ])

    for p in projects:
        duration = ""
        if p.start_date and p.end_date:
            duration = str((p.end_date - p.start_date).days)
        writer.writerow([
            p.id,
            p.title,
            p.category,
            p.academic_level or "",
            p.status,
            p.owner.name if p.owner else "",
            p.start_date.strftime("%d/%m/%Y") if p.start_date else "",
            p.end_date.strftime("%d/%m/%Y") if p.end_date else "",
            duration,
            p.created_at.strftime("%d/%m/%Y %H:%M") if p.created_at else "",
            p.submitted_at.strftime("%d/%m/%Y %H:%M") if p.submitted_at else "",
            p.reviewed_at.strftime("%d/%m/%Y %H:%M") if p.reviewed_at else "",
            p.review_comment or "",
        ])

    output.seek(0)
    filename = f"cebio_projetos_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/users", summary="Exportar usuários em CSV (admin)")
def export_users_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Exporta todos os usuários em formato CSV."""
    users = db.query(User).order_by(User.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Nome", "Email", "CPF", "Tipo", "Status",
        "Senha Temporária", "Último Login", "Cadastrado em", "Instituição"
    ])

    for u in users:
        writer.writerow([
            u.id,
            u.name,
            u.email,
            u.cpf or "",
            u.role,
            "Ativo" if u.is_active else "Inativo",
            "Sim" if u.is_temp_password else "Não",
            u.last_login.strftime("%d/%m/%Y %H:%M") if u.last_login else "Nunca",
            u.created_at.strftime("%d/%m/%Y %H:%M") if u.created_at else "",
            u.institution or "",
        ])

    output.seek(0)
    filename = f"cebio_usuarios_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/full", summary="Exportação completa do sistema em JSON (admin)")
def export_full_json(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Exporta todos os dados do sistema em JSON (backup completo)."""
    users = db.query(User).all()
    projects = db.query(Project).all()
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(5000).all()

    def fmt_dt(dt):
        return dt.isoformat() if dt else None

    data = {
        "exported_at": datetime.utcnow().isoformat(),
        "exported_by": current_user.name,
        "users": [
            {
                "id": u.id, "name": u.name, "email": u.email,
                "cpf": u.cpf, "role": u.role, "institution": u.institution,
                "is_active": u.is_active, "created_at": fmt_dt(u.created_at),
            }
            for u in users
        ],
        "projects": [
            {
                "id": p.id, "title": p.title, "category": p.category,
                "status": p.status, "owner_id": p.owner_id,
                "academic_level": p.academic_level,
                "created_at": fmt_dt(p.created_at),
                "submitted_at": fmt_dt(p.submitted_at),
            }
            for p in projects
        ],
        "audit_logs": [
            {
                "id": l.id, "action": l.action, "severity": l.severity,
                "user_id": l.user_id, "details": l.details,
                "timestamp": fmt_dt(l.timestamp),
            }
            for l in logs
        ],
    }

    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    filename = f"cebio_backup_completo_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    return StreamingResponse(
        io.BytesIO(json_bytes),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )



@router.get("/project/{project_id}/pdf", summary="Gerar relatório PDF de um projeto")
async def generate_project_report_pdf(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Gera relatório PDF completo de um projeto.
    Inclui: informações básicas, autores, histórico de versões e comentários.
    """
    # Buscar projeto com relacionamentos
    project = db.query(Project).options(
        joinedload(Project.owner),
        joinedload(Project.authors),
        joinedload(Project.links),
        joinedload(Project.files)
    ).filter(Project.id == project_id).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projeto não encontrado."
        )
    
    # Validar permissões: admin vê tudo, outros só seus projetos
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para gerar relatório deste projeto."
        )
    
    # Buscar histórico de versões
    versions = db.query(ProjectVersion).options(
        joinedload(ProjectVersion.author)
    ).filter(
        ProjectVersion.project_id == project_id
    ).order_by(ProjectVersion.version_number.desc()).all()
    
    # Buscar comentários
    comments = db.query(ProjectComment).options(
        joinedload(ProjectComment.author)
    ).filter(
        ProjectComment.project_id == project_id
    ).order_by(ProjectComment.created_at.desc()).all()
    
    try:
        # Gerar PDF
        pdf_buffer = generate_project_pdf(project, versions, comments)
        
        # Nome do arquivo
        safe_title = "".join(c for c in project.title if c.isalnum() or c in (' ', '-', '_'))[:50]
        filename = f"CEBIO_Projeto_{project_id}_{safe_title}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # Registrar auditoria
        log_action(
            db, "REPORT_GENERATED",
            user_id=current_user.id,
            target_project_id=project.id,
            details=f"Relatório PDF gerado para projeto '{project.title[:60]}'",
            ip_address=get_client_ip(request),
        )
        
        # Retornar PDF
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except Exception as e:
        # Log de erro
        log_action(
            db, "REPORT_ERROR",
            user_id=current_user.id,
            target_project_id=project.id,
            details=f"Erro ao gerar PDF: {str(e)}",
            ip_address=get_client_ip(request),
            severity="high"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar relatório PDF: {str(e)}"
        )
