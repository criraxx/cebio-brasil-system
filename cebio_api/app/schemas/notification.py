from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class NotificationCreate(BaseModel):
    user_id: int
    title: str
    message: str
    notification_type: str = "info"
    category: str = "system"
    related_project_id: Optional[int] = None


class NotificationOut(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    notification_type: str
    is_read: bool
    category: str
    related_project_id: Optional[int] = None
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MassNotificationRequest(BaseModel):
    """Schema para envio de notificações em massa."""
    title: str
    message: str
    notification_type: str = "info"
    # target_roles: lista de roles a receber. Ex: ["pesquisador", "bolsista"]
    # Se vazio, envia para todos.
    target_roles: Optional[List[str]] = []
    target_user_ids: Optional[List[int]] = []

    @field_validator("target_roles")
    @classmethod
    def validate_roles(cls, v):
        allowed = {"admin", "pesquisador", "bolsista"}
        for role in v:
            if role not in allowed:
                raise ValueError(f"Role inválida: {role}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Manutenção programada",
                "message": "O sistema estará em manutenção das 22h às 23h.",
                "notification_type": "warning",
                "target_roles": ["pesquisador", "bolsista"]
            }
        }
