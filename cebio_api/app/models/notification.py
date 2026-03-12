"""
Modelos de Notificação e Configuração do Sistema - CEBIO Brasil
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    # Tipo: info | success | warning | error
    notification_type = Column(String(20), default="info")
    is_read = Column(Boolean, default=False)
    # Categoria: project | user | system | admin
    category = Column(String(30), default="system")
    related_project_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification id={self.id} user_id={self.user_id} title={self.title[:30]}>"
