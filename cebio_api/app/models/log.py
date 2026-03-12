"""
Modelo de Log de Auditoria - CEBIO Brasil
Registra todas as ações relevantes do sistema.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Tipo de ação: LOGIN | LOGIN_FAILED | LOGOUT | USER_CREATED | USER_UPDATED |
    # USER_DELETED | USER_ACTIVATED | USER_DEACTIVATED | PASSWORD_RESET |
    # PROJECT_CREATED | PROJECT_UPDATED | PROJECT_SUBMITTED | PROJECT_APPROVED |
    # PROJECT_REJECTED | PROJECT_DELETED | PROJECT_RESTORED |
    # BATCH_APPROVED | BATCH_REJECTED | BATCH_ACTIVATED | BATCH_PASSWORD_RESET |
    # NOTIFICATION_SENT | BACKUP_CREATED | MAINTENANCE_ON | MAINTENANCE_OFF |
    # EXPORT_DATA | FILE_UPLOADED | FILE_DELETED | SYSTEM_CONFIG_CHANGED
    action = Column(String(60), nullable=False, index=True)

    # Categoria: Login | Project | User | File | System | Communication
    category = Column(String(30), nullable=True, default="System")

    # Severidade: low | medium | high | critical
    severity = Column(String(20), nullable=False, default="low")

    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    target_user_id = Column(Integer, nullable=True)   # usuário afetado pela ação
    target_project_id = Column(Integer, nullable=True)  # projeto afetado pela ação

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog id={self.id} action={self.action} user_id={self.user_id}>"
