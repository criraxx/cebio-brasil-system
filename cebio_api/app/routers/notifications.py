"""
CEBIO Brasil - Rotas de Notificações
Notificações individuais, leitura e envio em massa (admin).
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models.user import User
from ..models.notification import Notification
from ..schemas.notification import NotificationOut, MassNotificationRequest
from ..utils.security import require_admin, get_current_user
from ..utils.audit import log_action, get_client_ip

router = APIRouter(prefix="/notifications", tags=["Notificações"])


@router.get("", summary="Listar notificações do usuário autenticado")
def list_notifications(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna as notificações do usuário logado."""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)

    total = query.count()
    unread_count = db.query(func.count(Notification.id)).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).scalar()

    items = query.order_by(Notification.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [NotificationOut.model_validate(n) for n in items],
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "per_page": per_page,
    }


@router.post("/{notification_id}/read", summary="Marcar notificação como lida")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")

    notif.is_read = True
    notif.read_at = datetime.utcnow()
    db.commit()
    return {"message": "Notificação marcada como lida."}


@router.post("/read-all", summary="Marcar todas as notificações como lidas")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.utcnow()
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).update({"is_read": True, "read_at": now})
    db.commit()
    return {"message": "Todas as notificações marcadas como lidas."}


@router.delete("/{notification_id}", summary="Remover notificação")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")
    db.delete(notif)
    db.commit()
    return {"message": "Notificação removida."}


# ─── Admin: Envio em Massa ────────────────────────────────────────────────────

@router.post("/mass-send", summary="Enviar notificações em massa (admin)")
def mass_send(
    request: Request,
    data: MassNotificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Envia notificações para grupos de usuários de forma otimizada.
    - Se target_roles fornecido: envia para todos os usuários com aquelas roles.
    - Se target_user_ids fornecido: envia para usuários específicos.
    - Se ambos vazios: envia para todos os usuários ativos.
    
    Limite: máximo 100 usuários por lote.
    Processamento: transação única para melhor performance.
    """
    query = db.query(User).filter(User.is_active == True)

    if data.target_user_ids:
        query = query.filter(User.id.in_(data.target_user_ids))
    elif data.target_roles:
        query = query.filter(User.role.in_(data.target_roles))

    users = query.all()
    if not users:
        raise HTTPException(status_code=404, detail="Nenhum usuário encontrado para os critérios informados.")
    
    # Validar limite de 100 usuários
    if len(users) > 100:
        raise HTTPException(
            status_code=400,
            detail=f"Limite de 100 usuários por lote excedido. Encontrados: {len(users)} usuários. "
                   "Por favor, refine os filtros ou envie em múltiplos lotes."
        )

    # Processar em transação única para melhor performance
    success_count = 0
    failed_count = 0
    failed_users = []
    
    try:
        # Criar todas as notificações em uma única transação
        notifications = []
        for user in users:
            try:
                notif = Notification(
                    user_id=user.id,
                    title=data.title,
                    message=data.message,
                    notification_type=data.notification_type,
                    category="admin",
                    created_at=datetime.utcnow()
                )
                notifications.append(notif)
                success_count += 1
            except Exception as e:
                failed_count += 1
                failed_users.append({
                    "user_id": user.id,
                    "user_name": user.name,
                    "error": str(e)
                })
        
        # Adicionar todas de uma vez (bulk insert)
        if notifications:
            db.bulk_save_objects(notifications)
        
        db.commit()

        # Log de auditoria com detalhes
        log_action(
            db, "NOTIFICATION_MASS_SENT",
            user_id=current_user.id,
            details=f"Notificação em massa enviada. Título: '{data.title}'. "
                   f"Sucesso: {success_count}, Falhas: {failed_count}",
            ip_address=get_client_ip(request),
        )

        return {
            "message": f"Notificação enviada com sucesso.",
            "total": len(users),
            "success": success_count,
            "failed": failed_count,
            "failed_users": failed_users if failed_users else None
        }
    
    except Exception as e:
        db.rollback()
        log_action(
            db, "NOTIFICATION_MASS_ERROR",
            user_id=current_user.id,
            details=f"Erro ao enviar notificações em massa: {str(e)}",
            ip_address=get_client_ip(request),
            severity="high"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar notificações em massa: {str(e)}"
        )


@router.get("/admin/all", summary="Listar todas as notificações (admin)")
def admin_list_all(
    user_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin visualiza todas as notificações do sistema."""
    query = db.query(Notification)
    if user_id:
        query = query.filter(Notification.user_id == user_id)

    total = query.count()
    items = query.order_by(Notification.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [NotificationOut.model_validate(n) for n in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }
