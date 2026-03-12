"""
CEBIO Brasil - Rotas Administrativas do Sistema
Modo manutenção, backup, configurações, status do sistema.
"""
import json
import shutil
import zipfile
import io
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.system import SystemConfig
from ..schemas.system import SystemConfigOut, SystemConfigUpdate, MaintenanceToggle
from ..utils.security import require_admin
from ..utils.audit import log_action, get_client_ip
from ..config import BASE_DIR

router = APIRouter(prefix="/admin", tags=["Administração do Sistema"])


def _get_or_create_config(db: Session, key: str, default_value: str = "", description: str = "") -> SystemConfig:
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        config = SystemConfig(key=key, value=default_value, description=description)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


# ─── Status do Sistema ────────────────────────────────────────────────────────

@router.get("/status", summary="Status geral do sistema")
def system_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Retorna o status atual do sistema (manutenção, versão, último backup)."""
    maintenance = _get_or_create_config(db, "maintenance_mode", "false", "Modo manutenção ativo/inativo")
    maintenance_msg = _get_or_create_config(db, "maintenance_message", "Sistema em manutenção.", "Mensagem de manutenção")
    last_backup = _get_or_create_config(db, "last_backup", "", "Data do último backup")
    app_version = _get_or_create_config(db, "app_version", "1.0.0", "Versão da aplicação")

    from ..models.user import User as UserModel
    from ..models.project import Project
    from sqlalchemy import func
    total_users = db.query(func.count(UserModel.id)).scalar()
    total_projects = db.query(func.count(Project.id)).filter(Project.is_deleted == False).scalar()

    return {
        "status": "maintenance" if maintenance.value == "true" else "operational",
        "maintenance_mode": maintenance.value == "true",
        "maintenance_message": maintenance_msg.value,
        "last_backup": last_backup.value or None,
        "app_version": app_version.value,
        "database": "connected",
        "total_users": total_users,
        "total_projects": total_projects,
        "server_time": datetime.utcnow().isoformat(),
    }


# ─── Modo Manutenção ──────────────────────────────────────────────────────────

@router.post("/maintenance", summary="Ativar/desativar modo manutenção (admin)")
def toggle_maintenance(
    request: Request,
    data: MaintenanceToggle,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Ativa ou desativa o modo de manutenção do sistema."""
    maintenance = _get_or_create_config(db, "maintenance_mode", "false")
    maintenance.value = "true" if data.enabled else "false"
    maintenance.updated_by = current_user.id
    maintenance.updated_at = datetime.utcnow()

    msg_config = _get_or_create_config(db, "maintenance_message")
    if data.message:
        msg_config.value = data.message
        msg_config.updated_at = datetime.utcnow()

    db.commit()

    action = "MAINTENANCE_ON" if data.enabled else "MAINTENANCE_OFF"
    state = "ativado" if data.enabled else "desativado"

    log_action(
        db, action,
        user_id=current_user.id,
        details=f"Modo manutenção {state}. Mensagem: {data.message or 'N/A'}",
        ip_address=get_client_ip(request),
        severity="high",
    )

    return {
        "message": f"Modo manutenção {state} com sucesso.",
        "maintenance_mode": data.enabled,
        "maintenance_message": msg_config.value,
    }


@router.get("/maintenance", summary="Status do modo manutenção")
def get_maintenance_status(db: Session = Depends(get_db)):
    """Endpoint público para verificar se o sistema está em manutenção."""
    maintenance = db.query(SystemConfig).filter(SystemConfig.key == "maintenance_mode").first()
    msg = db.query(SystemConfig).filter(SystemConfig.key == "maintenance_message").first()

    is_maintenance = maintenance.value == "true" if maintenance else False
    message = msg.value if msg else "Sistema em manutenção."

    return {
        "maintenance_mode": is_maintenance,
        "message": message if is_maintenance else None,
    }


# ─── Backup ───────────────────────────────────────────────────────────────────

@router.post("/backup", summary="Criar backup do sistema (admin)")
def create_backup(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Cria um backup do banco de dados SQLite e dos arquivos de upload.
    Para MySQL em produção, use mysqldump via cron job.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_name = f"cebio_backup_{timestamp}.zip"

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Banco de dados SQLite
        db_path = BASE_DIR / "cebio_brasil.db"
        if db_path.exists():
            zf.write(db_path, "cebio_brasil.db")

        # Arquivos de upload
        upload_dir = BASE_DIR / "app" / "uploads"
        if upload_dir.exists():
            for file_path in upload_dir.rglob("*"):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(BASE_DIR))
                    zf.write(file_path, arcname)

    zip_buffer.seek(0)

    # Registra data do backup
    last_backup = _get_or_create_config(db, "last_backup")
    last_backup.value = datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")
    last_backup.updated_at = datetime.utcnow()
    db.commit()

    log_action(
        db, "BACKUP_CREATED",
        user_id=current_user.id,
        details=f"Backup criado: {backup_name}",
        ip_address=get_client_ip(request),
    )

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={backup_name}"},
    )


# ─── Configurações do Sistema ─────────────────────────────────────────────────

@router.get("/config", summary="Listar configurações do sistema (admin)")
def list_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Lista todas as configurações do sistema."""
    configs = db.query(SystemConfig).all()
    return [SystemConfigOut.model_validate(c) for c in configs]


@router.put("/config/{key}", summary="Atualizar configuração do sistema (admin)")
def update_config(
    key: str,
    request: Request,
    data: SystemConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        config = SystemConfig(key=key, value=data.value)
        db.add(config)
    else:
        config.value = data.value
        config.updated_at = datetime.utcnow()
        config.updated_by = current_user.id

    db.commit()
    db.refresh(config)

    log_action(
        db, "SYSTEM_CONFIG_CHANGED",
        user_id=current_user.id,
        details=f"Configuração '{key}' alterada para '{data.value}'",
        ip_address=get_client_ip(request),
        severity="high",
    )

    return SystemConfigOut.model_validate(config)


# ─── Middleware check (para o frontend verificar manutenção) ──────────────────

@router.get("/health", summary="Health check público")
def health_check(db: Session = Depends(get_db)):
    """Endpoint de health check para monitoramento."""
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    maintenance = db.query(SystemConfig).filter(SystemConfig.key == "maintenance_mode").first()
    is_maintenance = maintenance.value == "true" if maintenance else False

    return {
        "status": "maintenance" if is_maintenance else "ok",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }
