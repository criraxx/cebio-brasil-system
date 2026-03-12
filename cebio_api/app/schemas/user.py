from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
import re


class UserAdminCreate(BaseModel):
    """Schema para admin criar um novo usuário (com senha temporária gerada automaticamente)."""
    name: str
    email: str
    cpf: Optional[str] = None
    role: str = "bolsista"
    institution: Optional[str] = None
    password: Optional[str] = None  # Se não informado, gera automaticamente

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        allowed = {"admin", "pesquisador", "bolsista"}
        if v not in allowed:
            raise ValueError(f"Role deve ser um de: {', '.join(allowed)}")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v:
            raise ValueError("Email inválido")
        return v.lower().strip()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Prof. Dr. João Carlos Oliveira",
                "email": "joao.oliveira@cebio.org.br",
                "cpf": "234.567.890-11",
                "role": "pesquisador",
                "institution": "CEBIO Brasil"
            }
        }


class UserCreate(BaseModel):
    """Schema genérico de criação de usuário."""
    name: str
    email: str
    password: str
    role: str = "bolsista"
    institution: Optional[str] = None
    cpf: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema para atualização de dados do próprio usuário."""
    name: Optional[str] = None
    institution: Optional[str] = None
    cpf: Optional[str] = None


class UserAdminUpdate(BaseModel):
    """Schema para admin atualizar qualquer usuário."""
    name: Optional[str] = None
    email: Optional[str] = None
    cpf: Optional[str] = None
    role: Optional[str] = None
    institution: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v is not None:
            allowed = {"admin", "pesquisador", "bolsista"}
            if v not in allowed:
                raise ValueError(f"Role deve ser um de: {', '.join(allowed)}")
        return v


class PasswordChange(BaseModel):
    """Schema para troca de senha."""
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 6:
            raise ValueError("A nova senha deve ter pelo menos 6 caracteres")
        return v


class UserOut(BaseModel):
    """Schema de saída de usuário (sem senha)."""
    id: int
    name: str
    email: str
    cpf: Optional[str] = None
    role: str
    institution: Optional[str] = None
    is_active: bool
    is_temp_password: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None

    class Config:
        from_attributes = True
        # Garantir que hashed_password NUNCA seja incluído
        fields = {'hashed_password': {'exclude': True}}


class UserList(BaseModel):
    """Schema de listagem de usuários com paginação."""
    items: List[UserOut]
    total: int
    page: int
    per_page: int
    pages: int


class BatchActivateRequest(BaseModel):
    """Schema para ativar/desativar múltiplos usuários."""
    user_ids: List[int]
    activate: bool = True

    class Config:
        json_schema_extra = {
            "example": {"user_ids": [2, 3, 4], "activate": True}
        }


class BatchPasswordResetRequest(BaseModel):
    """Schema para reset de senha em lote."""
    user_ids: List[int]

    class Config:
        json_schema_extra = {
            "example": {"user_ids": [2, 3]}
        }
