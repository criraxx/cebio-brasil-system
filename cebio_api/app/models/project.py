"""
Modelos de Projeto - CEBIO Brasil
Inclui: Project, ProjectVersion, ProjectComment, ProjectAuthor, ProjectLink, ProjectFile
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from ..database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    target_audience = Column(String(300), nullable=True)

    # Categorias: projetos_pesquisa | artigos | projetos_ensino | disciplinas | cursos | orientacoes
    category = Column(String(50), nullable=False, default="projetos_pesquisa")

    # Nível: graduacao | mestrado | doutorado | pos_doutorado
    academic_level = Column(String(30), nullable=True, default="graduacao")

    # Status: rascunho | em_submissao | em_revisao | aprovado | rejeitado
    status = Column(String(30), nullable=False, default="rascunho")

    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # Soft delete
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, nullable=True)

    # Metadados
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_comment = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)

    # Relacionamentos
    owner = relationship("User", back_populates="projects", foreign_keys=[owner_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    versions = relationship("ProjectVersion", back_populates="project", cascade="all, delete-orphan")
    comments = relationship("ProjectComment", back_populates="project", cascade="all, delete-orphan")
    authors = relationship("ProjectAuthor", back_populates="project", cascade="all, delete-orphan")
    links = relationship("ProjectLink", back_populates="project", cascade="all, delete-orphan")
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project id={self.id} title={self.title[:40]} status={self.status}>"


class ProjectVersion(Base):
    """Histórico de versões de um projeto (controle de alterações)."""
    __tablename__ = "project_versions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    version_number = Column(Integer, nullable=False, default=1)
    # Tipo: criacao | conteudo | arquivos | status
    change_type = Column(String(30), nullable=False, default="conteudo")
    description = Column(Text, nullable=True)
    changes_detail = Column(Text, nullable=True)  # JSON com detalhes das mudanças
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="versions")
    author = relationship("User", foreign_keys=[changed_by])


class ProjectComment(Base):
    """Comentários de revisão em projetos."""
    __tablename__ = "project_comments"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_admin_comment = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="comments")
    author = relationship("User", foreign_keys=[user_id])


class ProjectAuthor(Base):
    """Autores/colaboradores de um projeto."""
    __tablename__ = "project_authors"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(200), nullable=False)
    cpf = Column(String(20), nullable=True)
    institution = Column(String(300), nullable=True)
    academic_level = Column(String(30), nullable=True)
    role = Column(String(100), nullable=True, default="Coautor")
    is_main = Column(Boolean, default=False)
    order_index = Column(Integer, default=0)

    project = relationship("Project", back_populates="authors")


class ProjectLink(Base):
    """Links externos associados a um projeto."""
    __tablename__ = "project_links"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    url = Column(String(1000), nullable=False)
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    # Tipo: github | artigo | documentacao | outro
    link_type = Column(String(30), default="outro")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="links")


class ProjectFile(Base):
    """Arquivos (fotos e documentos PDF) de um projeto."""
    __tablename__ = "project_files"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)  # foto | documento
    mime_type = Column(String(100), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="files")
    uploader = relationship("User", foreign_keys=[uploaded_by])
