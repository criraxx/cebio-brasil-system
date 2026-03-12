"""
CEBIO Brasil - Rota de Autenticação
O admin cria o usuário no sistema; o login apenas verifica no banco de dados.

Rate limiting por EMAIL (não por IP):
- Bloqueia apenas o usuário que errou a senha repetidamente
- Não afeta outros usuários no mesmo IP (NAT, proxy corporativo, etc.)
- Até 5 tentativas falhas em 5 minutos → bloqueio de 15 minutos
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..schemas.auth import LoginRequest, TokenResponse, ChangePasswordRequest
from ..utils.security import (
    verify_password, create_access_token, get_current_user,
    check_user_rate_limit, record_failed_login, clear_failed_logins,
    get_remaining_attempts, validate_password_strength, hash_password,
)
from ..utils.audit import log_action, get_client_ip
from ..config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=TokenResponse, summary="Login do usuário")
def login(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    """
    Autentica o usuário verificando email e senha no banco de dados.
    O admin deve ter criado o usuário previamente.

    Rate limiting: por EMAIL — bloqueia apenas o usuário que errou a senha,
    sem afetar outros usuários no mesmo IP (NAT, proxy, etc.).
    """
    email = data.email.lower().strip()
    ip = get_client_ip(request)

    # Rate limiting por EMAIL: verifica se este usuário está bloqueado
    # (não bloqueia o IP, apenas o email específico)
    check_user_rate_limit(email)

    # Busca o usuário pelo email
    user = db.query(User).filter(User.email == email).first()

    # Usuário não encontrado — mensagem genérica (não revela se email existe)
    if not user:
        # Registra tentativa falha para o email tentado
        record_failed_login(email)
        log_action(
            db, "LOGIN_FAILED",
            details="Tentativa de login com credenciais inválidas",
            ip_address=ip,
            severity="medium",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos.",
        )

    # Senha incorreta
    if not verify_password(data.password, user.hashed_password):
        record_failed_login(email)
        remaining = get_remaining_attempts(email)
        log_action(
            db, "LOGIN_FAILED",
            user_id=user.id,
            details=f"Senha incorreta ({remaining} tentativas restantes)",
            ip_address=ip,
            severity="medium",
        )
        detail = "Email ou senha incorretos."
        if remaining <= 2:
            detail += f" Atenção: {remaining} tentativa(s) restante(s) antes do bloqueio temporário."
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )

    # Usuário inativo
    if not user.is_active:
        log_action(
            db, "LOGIN_FAILED",
            user_id=user.id,
            details="Tentativa de login de usuário inativo",
            ip_address=ip,
            severity="medium",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo. Contate o administrador.",
        )

    # Login bem-sucedido: limpa tentativas falhas deste email
    clear_failed_logins(email)

    # Atualiza último login
    user.last_login = datetime.utcnow()
    db.commit()

    # Gera token JWT
    token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    log_action(
        db, "LOGIN_SUCCESS",
        user_id=user.id,
        details="Login realizado com sucesso",
        ip_address=ip,
    )

    return TokenResponse.from_user(
        token=token,
        user=user,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout", summary="Logout do usuário")
def logout(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registra o logout do usuário no log de auditoria."""
    log_action(
        db, "LOGOUT",
        user_id=current_user.id,
        details="Logout realizado",
        ip_address=get_client_ip(request),
    )
    return {"message": "Logout realizado com sucesso."}


@router.get("/me", summary="Dados do usuário autenticado")
def get_me(current_user: User = Depends(get_current_user)):
    """Retorna os dados do usuário autenticado (sem hashed_password)."""
    from ..schemas.user import UserOut
    return UserOut.model_validate(current_user)


@router.post("/change-password", summary="Trocar senha")
def change_password(
    request: Request,
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Permite ao usuário trocar sua própria senha.
    Obrigatório quando is_temp_password=True.
    """
    if not data.current_password or not data.new_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe a senha atual e a nova senha.",
        )

    # Valida complexidade da nova senha
    try:
        validate_password_strength(data.new_password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta.",
        )

    current_user.hashed_password = hash_password(data.new_password)
    current_user.is_temp_password = False
    current_user.updated_at = datetime.utcnow()
    db.commit()

    log_action(
        db, "PASSWORD_CHANGED",
        user_id=current_user.id,
        details="Usuário alterou a própria senha",
        ip_address=get_client_ip(request),
    )

    return {"message": "Senha alterada com sucesso."}
