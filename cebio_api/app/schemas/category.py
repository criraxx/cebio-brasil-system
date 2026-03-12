"""
Schemas de Categoria e Nível Acadêmico - CEBIO Brasil
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ─── CATEGORY ─────────────────────────────────────────────────────────────────

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    slug: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#1a9a4a", pattern=r"^#[0-9a-fA-F]{6}$")
    icon: Optional[str] = None
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    slug: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryOut(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


# ─── ACADEMIC LEVEL ───────────────────────────────────────────────────────────

class AcademicLevelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    slug: str = Field(..., min_length=1, max_length=100)
    order: int = 0
    is_active: bool = True


class AcademicLevelCreate(AcademicLevelBase):
    pass


class AcademicLevelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    slug: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None


class AcademicLevelOut(AcademicLevelBase):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None

    class Config:
        from_attributes = True
