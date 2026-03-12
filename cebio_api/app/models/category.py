"""
Modelos de Categoria e Nível Acadêmico - CEBIO Brasil
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from ..database import Base


class Category(Base):
    """Categorias de projetos."""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    slug = Column(String(100), nullable=False, unique=True)  # URL-friendly name
    color = Column(String(7), default="#1a9a4a")  # Cor para exibição
    icon = Column(String(50), nullable=True)  # Nome do ícone
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<Category id={self.id} name={self.name}>"


class AcademicLevel(Base):
    """Níveis acadêmicos."""
    __tablename__ = "academic_levels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    slug = Column(String(100), nullable=False, unique=True)  # URL-friendly name
    order = Column(Integer, default=0)  # Para ordenação
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<AcademicLevel id={self.id} name={self.name}>"
