"""
Modelo de Usuário - CEBIO Brasil
Mapeado para a tabela 'users' existente no banco TiDB/MySQL.
Roles: admin | pesquisador | bolsista
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column("id", Integer, primary_key=True, index=True)
    # Coluna openId existente no banco - usamos email como identificador principal no CEBIO
    open_id = Column("openId", String(64), nullable=True, unique=True)
    name = Column("name", Text, nullable=True)
    email = Column("email", String(320), unique=True, index=True, nullable=True)
    login_method = Column("loginMethod", String(64), nullable=True)

    # Role: admin | pesquisador | bolsista
    # O banco original tem enum('user','admin') - expandimos via coluna separada
    # Usamos a coluna role original para compatibilidade
    role = Column("role", String(30), nullable=False, default="bolsista")

    # Colunas adicionadas pela migração CEBIO
    cpf = Column("cpf", String(20), nullable=True)
    hashed_password = Column("hashed_password", String(255), nullable=False, default="")
    institution = Column("institution", String(300), nullable=True)
    is_active = Column("is_active", Boolean, default=True)
    is_temp_password = Column("is_temp_password", Boolean, default=True)
    must_change_password = Column("must_change_password", Boolean, default=False)
    last_login = Column("last_login", DateTime, nullable=True)
    created_by = Column("created_by", Integer, nullable=True)

    # Colunas originais do banco (camelCase)
    created_at = Column("createdAt", DateTime, default=datetime.utcnow)
    updated_at = Column("updatedAt", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_signed_in = Column("lastSignedIn", DateTime, default=datetime.utcnow)

    # Relacionamentos
    projects = relationship("Project", back_populates="owner", foreign_keys="Project.owner_id")
    audit_logs = relationship("AuditLog", back_populates="user")
    notifications = relationship("Notification", back_populates="user")

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"
