from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SystemConfigOut(BaseModel):
    key: str
    value: Optional[str] = None
    description: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class SystemConfigUpdate(BaseModel):
    value: str


class MaintenanceToggle(BaseModel):
    enabled: bool
    message: Optional[str] = "Sistema em manutenção. Tente novamente em breve."
