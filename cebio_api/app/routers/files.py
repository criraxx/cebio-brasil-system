"""
CEBIO Brasil - Rotas de Download de Arquivos
Permite download seguro de arquivos anexados a projetos.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from ..database import get_db
from ..models.user import User
from ..models.project import Project, ProjectFile
from ..utils.security import get_current_user
from ..utils.audit import log_action

router = APIRouter(prefix="/files", tags=["Arquivos"])


@router.get("/{file_id}", summary="Download de arquivo")
async def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Faz download de um arquivo anexado a um projeto.
    Valida permissões: usuário deve ter acesso ao projeto do arquivo.
    """
    # Buscar arquivo
    file = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo não encontrado."
        )
    
    # Buscar projeto para validar permissões
    project = db.query(Project).filter(Project.id == file.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projeto não encontrado."
        )
    
    # Validar permissões: admin vê tudo, outros só seus projetos
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar este arquivo."
        )
    
    # Verificar se arquivo existe no sistema de arquivos
    file_path = Path(file.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo não encontrado no servidor."
        )
    
    # Registrar download na auditoria
    log_action(
        db, "FILE_DOWNLOADED",
        user_id=current_user.id,
        target_project_id=project.id,
        details=f"Download do arquivo '{file.original_name}'"
    )
    
    # Retornar arquivo com nome original
    return FileResponse(
        path=str(file_path),
        filename=file.original_name,
        media_type=file.mime_type or "application/octet-stream"
    )
