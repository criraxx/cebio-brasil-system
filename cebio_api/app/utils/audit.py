"""
CEBIO Brasil - Utilitário de Auditoria
Funções para registrar ações no log de auditoria automaticamente.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from ..models.log import AuditLog

# Mapeamento de ação -> severidade padrão
SEVERITY_MAP = {
    "LOGIN": "low",
    "LOGIN_SUCCESS": "low",
    "LOGIN_FAILED": "medium",
    "LOGOUT": "low",
    "USER_CREATED": "medium",
    "USER_UPDATED": "medium",
    "USER_DELETED": "high",
    "USER_ACTIVATED": "medium",
    "USER_DEACTIVATED": "high",
    "PASSWORD_RESET": "medium",
    "PROJECT_CREATED": "medium",
    "PROJECT_UPDATED": "medium",
    "PROJECT_SUBMITTED": "medium",
    "PROJECT_APPROVED": "high",
    "PROJECT_REJECTED": "high",
    "PROJECT_DELETED": "high",
    "PROJECT_RESTORED": "high",
    "BATCH_APPROVED": "high",
    "BATCH_REJECTED": "high",
    "BATCH_ACTIVATED": "medium",
    "BATCH_PASSWORD_RESET": "high",
    "NOTIFICATION_SENT": "low",
    "BACKUP_CREATED": "medium",
    "MAINTENANCE_ON": "high",
    "MAINTENANCE_OFF": "medium",
    "EXPORT_DATA": "medium",
    "FILE_UPLOADED": "low",
    "FILE_DELETED": "medium",
    "SYSTEM_CONFIG_CHANGED": "high",
}

CATEGORY_MAP = {
    "LOGIN": "Login", "LOGIN_SUCCESS": "Login", "LOGIN_FAILED": "Login", "LOGOUT": "Login",
    "USER_CREATED": "User", "USER_UPDATED": "User", "USER_DELETED": "User",
    "USER_ACTIVATED": "User", "USER_DEACTIVATED": "User", "PASSWORD_RESET": "User",
    "BATCH_ACTIVATED": "User", "BATCH_PASSWORD_RESET": "User",
    "PROJECT_CREATED": "Project", "PROJECT_UPDATED": "Project", "PROJECT_SUBMITTED": "Project",
    "PROJECT_APPROVED": "Project", "PROJECT_REJECTED": "Project",
    "PROJECT_DELETED": "Project", "PROJECT_RESTORED": "Project",
    "BATCH_APPROVED": "Project", "BATCH_REJECTED": "Project",
    "FILE_UPLOADED": "File", "FILE_DELETED": "File",
    "NOTIFICATION_SENT": "Communication",
    "BACKUP_CREATED": "System", "MAINTENANCE_ON": "System", "MAINTENANCE_OFF": "System",
    "EXPORT_DATA": "System", "SYSTEM_CONFIG_CHANGED": "System",
}


def log_action(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    target_user_id: Optional[int] = None,
    target_project_id: Optional[int] = None,
    severity: Optional[str] = None,
    category: Optional[str] = None,
) -> AuditLog:
    """Registra uma ação no log de auditoria."""
    entry = AuditLog(
        action=action,
        category=category or CATEGORY_MAP.get(action, "System"),
        severity=severity or SEVERITY_MAP.get(action, "low"),
        details=details,
        ip_address=ip_address,
        user_id=user_id,
        target_user_id=target_user_id,
        target_project_id=target_project_id,
        timestamp=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_client_ip(request) -> str:
    """Extrai o IP real do cliente da requisição."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
