from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AuditLogOut(BaseModel):
    id: int
    action: str
    category: Optional[str] = None
    severity: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    target_user_id: Optional[int] = None
    target_project_id: Optional[int] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class AuditLogFilter(BaseModel):
    search: Optional[str] = None
    severity: Optional[str] = None
    category: Optional[str] = None
    action: Optional[str] = None
    user_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = 1
    per_page: int = 20
