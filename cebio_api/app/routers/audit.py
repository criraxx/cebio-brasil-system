"""
CEBIO Brasil - Rotas de Auditoria
Listagem e exportação de logs de auditoria (apenas admin).
"""
import csv
import io
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from ..database import get_db
from ..models.log import AuditLog
from ..models.user import User
from ..utils.security import require_admin, get_current_user

router = APIRouter(prefix="/audit", tags=["Auditoria"])


@router.get("", summary="Listar logs de auditoria")
def list_logs(
    search: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista logs de auditoria. Admins veem tudo, usuários comuns veem apenas os seus."""
    query = db.query(AuditLog)
    
    # Se não for admin, filtrar apenas logs do próprio usuário
    if current_user.role != "admin":
        query = query.filter(AuditLog.user_id == current_user.id)

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                AuditLog.action.ilike(term),
                AuditLog.details.ilike(term),
                AuditLog.ip_address.ilike(term),
            )
        )
    if severity:
        query = query.filter(AuditLog.severity == severity)
    if category:
        query = query.filter(AuditLog.category == category)
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if date_from:
        try:
            query = query.filter(AuditLog.timestamp >= datetime.strptime(date_from, "%Y-%m-%d"))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(AuditLog.timestamp <= datetime.strptime(date_to + " 23:59:59", "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            pass

    total = query.count()
    logs = query.order_by(AuditLog.timestamp.desc()).offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page

    # Enriquecer com nome do usuário
    result = []
    for log in logs:
        user_name = None
        if log.user:
            user_name = log.user.name
        result.append({
            "id": log.id,
            "action": log.action,
            "category": log.category,
            "severity": log.severity,
            "details": log.details,
            "ip_address": log.ip_address,
            "user_id": log.user_id,
            "user_name": user_name,
            "target_user_id": log.target_user_id,
            "target_project_id": log.target_project_id,
            "timestamp": log.timestamp,
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }


@router.get("/stats", summary="Estatísticas de auditoria (admin)")
def audit_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Retorna estatísticas dos logs para o dashboard de auditoria."""
    from datetime import date, timedelta
    today = datetime.utcnow().date()

    total = db.query(func.count(AuditLog.id)).scalar()
    critical = db.query(func.count(AuditLog.id)).filter(AuditLog.severity == "critical").scalar()
    today_count = db.query(func.count(AuditLog.id)).filter(
        func.date(AuditLog.timestamp) == today
    ).scalar()
    unique_users = db.query(func.count(func.distinct(AuditLog.user_id))).filter(
        AuditLog.user_id.isnot(None)
    ).scalar()
    by_severity = db.query(AuditLog.severity, func.count(AuditLog.id)).group_by(AuditLog.severity).all()
    by_category = db.query(AuditLog.category, func.count(AuditLog.id)).group_by(AuditLog.category).all()

    return {
        "total": total,
        "critical": critical,
        "today": today_count,
        "unique_users": unique_users,
        "by_severity": {s: c for s, c in by_severity},
        "by_category": {cat: c for cat, c in by_category},
    }


@router.get("/export", summary="Exportar logs em CSV (admin)")
def export_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Exporta todos os logs de auditoria em formato CSV."""
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Timestamp", "Ação", "Categoria", "Severidade", "Usuário ID",
                     "Usuário Nome", "Detalhes", "IP", "Projeto ID", "Usuário Alvo ID"])

    for log in logs:
        user_name = log.user.name if log.user else ""
        writer.writerow([
            log.id,
            log.timestamp.strftime("%d/%m/%Y %H:%M:%S") if log.timestamp else "",
            log.action,
            log.category or "",
            log.severity,
            log.user_id or "",
            user_name,
            log.details or "",
            log.ip_address or "",
            log.target_project_id or "",
            log.target_user_id or "",
        ])

    output.seek(0)
    filename = f"cebio_audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
