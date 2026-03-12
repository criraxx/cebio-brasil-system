from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class ProjectAuthorCreate(BaseModel):
    name: str
    cpf: Optional[str] = None
    institution: Optional[str] = None
    academic_level: Optional[str] = "graduacao"
    role: Optional[str] = "Coautor"
    is_main: bool = False
    order_index: int = 0


class ProjectAuthorOut(BaseModel):
    id: int
    name: str
    cpf: Optional[str] = None
    institution: Optional[str] = None
    academic_level: Optional[str] = None
    role: Optional[str] = None
    is_main: bool
    order_index: int

    class Config:
        from_attributes = True


class ProjectLinkCreate(BaseModel):
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    link_type: str = "outro"

    @field_validator("link_type")
    @classmethod
    def validate_link_type(cls, v):
        allowed = {"github", "artigo", "documentacao", "outro"}
        if v not in allowed:
            raise ValueError(f"Tipo deve ser: {', '.join(allowed)}")
        return v


class ProjectLinkOut(BaseModel):
    id: int
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    link_type: str

    class Config:
        from_attributes = True


class ProjectCommentCreate(BaseModel):
    content: str


class ProjectCommentOut(BaseModel):
    id: int
    project_id: int
    user_id: int
    content: str
    is_admin_comment: bool
    created_at: datetime
    author_name: Optional[str] = None

    class Config:
        from_attributes = True


class ProjectFileOut(BaseModel):
    id: int
    filename: str
    original_name: str
    file_type: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectVersionOut(BaseModel):
    id: int
    version_number: int
    change_type: str
    description: Optional[str] = None
    changes_detail: Optional[str] = None
    changed_by: int
    author_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    title: str
    summary: Optional[str] = None
    target_audience: Optional[str] = None
    category: str = "projetos_pesquisa"
    academic_level: Optional[str] = "graduacao"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    authors: Optional[List[ProjectAuthorCreate]] = []
    links: Optional[List[ProjectLinkCreate]] = []

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        allowed = {"projetos_pesquisa", "artigos", "projetos_ensino", "disciplinas", "cursos", "orientacoes"}
        if v not in allowed:
            raise ValueError(f"Categoria inválida. Permitidas: {', '.join(allowed)}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Biodiversidade da Mata Atlântica",
                "summary": "Estudo comparativo de espécies endêmicas...",
                "category": "projetos_pesquisa",
                "academic_level": "doutorado",
                "authors": [{"name": "Prof. Dr. João", "is_main": True, "role": "Autor Principal"}]
            }
        }


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    target_audience: Optional[str] = None
    category: Optional[str] = None
    academic_level: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ProjectStatusUpdate(BaseModel):
    """Schema para admin alterar status de um projeto."""
    status: str
    comment: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        allowed = {"rascunho", "em_submissao", "em_revisao", "aprovado", "rejeitado"}
        if v not in allowed:
            raise ValueError(f"Status inválido. Permitidos: {', '.join(allowed)}")
        return v


class ProjectOut(BaseModel):
    id: int
    title: str
    summary: Optional[str] = None
    target_audience: Optional[str] = None
    category: str
    academic_level: Optional[str] = None
    status: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_deleted: bool
    owner_id: int
    owner_name: Optional[str] = None
    reviewed_by: Optional[int] = None
    review_comment: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    authors: List[ProjectAuthorOut] = []
    links: List[ProjectLinkOut] = []
    files: List[ProjectFileOut] = []
    comments_count: int = 0

    class Config:
        from_attributes = True


class ProjectList(BaseModel):
    items: List[ProjectOut]
    total: int
    page: int
    per_page: int
    pages: int


class BatchProjectAction(BaseModel):
    """Schema para aprovação/rejeição em lote."""
    project_ids: List[int]
    comment: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {"project_ids": [1, 2, 3], "comment": "Aprovados após revisão"}
        }
