"""
Router de Categorias e Níveis Acadêmicos - CEBIO Brasil
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.category import Category, AcademicLevel
from ..schemas.category import (
    CategoryCreate, CategoryUpdate, CategoryOut,
    AcademicLevelCreate, AcademicLevelUpdate, AcademicLevelOut
)
from ..utils.security import get_current_user
from ..models.user import User

router = APIRouter(prefix="/api", tags=["categories"])


# ─── CATEGORIES ───────────────────────────────────────────────────────────────

@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(
    db: Session = Depends(get_db),
    active_only: bool = True
):
    """Lista todas as categorias."""
    query = db.query(Category)
    if active_only:
        query = query.filter(Category.is_active == True)
    return query.order_by(Category.name).all()


@router.get("/categories/{category_id}", response_model=CategoryOut)
async def get_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    """Obtém uma categoria específica."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    return category


@router.post("/categories", response_model=CategoryOut, status_code=201)
async def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria uma nova categoria (apenas admin)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins podem criar categorias")
    
    # Verificar se já existe
    existing = db.query(Category).filter(
        (Category.name == data.name) | (Category.slug == data.slug)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Categoria já existe")
    
    category = Category(
        name=data.name,
        description=data.description,
        slug=data.slug,
        color=data.color,
        icon=data.icon,
        is_active=data.is_active,
        created_by=current_user.id
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualiza uma categoria (apenas admin)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins podem atualizar categorias")
    
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    # Atualizar apenas os campos fornecidos
    for field, value in data.dict(exclude_unset=True).items():
        setattr(category, field, value)
    
    db.commit()
    db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deleta uma categoria (apenas admin)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins podem deletar categorias")
    
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    db.delete(category)
    db.commit()


# ─── ACADEMIC LEVELS ──────────────────────────────────────────────────────────

@router.get("/academic-levels", response_model=list[AcademicLevelOut])
async def list_academic_levels(
    db: Session = Depends(get_db),
    active_only: bool = True
):
    """Lista todos os níveis acadêmicos."""
    query = db.query(AcademicLevel)
    if active_only:
        query = query.filter(AcademicLevel.is_active == True)
    return query.order_by(AcademicLevel.order, AcademicLevel.name).all()


@router.get("/academic-levels/{level_id}", response_model=AcademicLevelOut)
async def get_academic_level(
    level_id: int,
    db: Session = Depends(get_db)
):
    """Obtém um nível acadêmico específico."""
    level = db.query(AcademicLevel).filter(AcademicLevel.id == level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="Nível acadêmico não encontrado")
    return level


@router.post("/academic-levels", response_model=AcademicLevelOut, status_code=201)
async def create_academic_level(
    data: AcademicLevelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria um novo nível acadêmico (apenas admin)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins podem criar níveis acadêmicos")
    
    # Verificar se já existe
    existing = db.query(AcademicLevel).filter(
        (AcademicLevel.name == data.name) | (AcademicLevel.slug == data.slug)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Nível acadêmico já existe")
    
    level = AcademicLevel(
        name=data.name,
        description=data.description,
        slug=data.slug,
        order=data.order,
        is_active=data.is_active,
        created_by=current_user.id
    )
    db.add(level)
    db.commit()
    db.refresh(level)
    return level


@router.put("/academic-levels/{level_id}", response_model=AcademicLevelOut)
async def update_academic_level(
    level_id: int,
    data: AcademicLevelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualiza um nível acadêmico (apenas admin)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins podem atualizar níveis acadêmicos")
    
    level = db.query(AcademicLevel).filter(AcademicLevel.id == level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="Nível acadêmico não encontrado")
    
    # Atualizar apenas os campos fornecidos
    for field, value in data.dict(exclude_unset=True).items():
        setattr(level, field, value)
    
    db.commit()
    db.refresh(level)
    return level


@router.delete("/academic-levels/{level_id}", status_code=204)
async def delete_academic_level(
    level_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deleta um nível acadêmico (apenas admin)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins podem deletar níveis acadêmicos")
    
    level = db.query(AcademicLevel).filter(AcademicLevel.id == level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="Nível acadêmico não encontrado")
    
    db.delete(level)
    db.commit()
