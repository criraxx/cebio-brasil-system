from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    email: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "admin@cebio.org.br",
                "password": "senha123"
            }
        }


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    name: str
    email: str
    role: str
    is_temp_password: bool
    requires_password_change: bool  # Alias para is_temp_password
    expires_in: int  # segundos
    
    @classmethod
    def from_user(cls, token: str, user, expires_in: int):
        return cls(
            access_token=token,
            token_type="bearer",
            user_id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            is_temp_password=user.is_temp_password,
            requires_password_change=user.is_temp_password,
            expires_in=expires_in
        )


class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "SenhaAtual@123",
                "new_password": "NovaSenha@456"
            }
        }
