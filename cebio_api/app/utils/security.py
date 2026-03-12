"""
CEBIO Brasil - Utilitários de Segurança
Hash de senhas e geração/validação de tokens JWT.

SEGURANÇA:
- Senhas com bcrypt (rounds=12)
- JWT com expiração e validação de tipo
- Rate limiting por EMAIL (não por IP) — evita bloquear usuários legítimos
  que compartilham o mesmo IP (NAT, proxy corporativo, etc.)
- Validação de complexidade de senha
"""
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="passlib")

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ..config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from ..database import get_db

# bcrypt com custo 12 (mais seguro que o padrão 10)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
bearer_scheme = HTTPBearer(auto_error=False)

# ─── Rate Limiting por USUÁRIO (email) ───────────────────────────────────────
# Lógica: rastreia tentativas falhas por EMAIL, não por IP.
# Isso evita bloquear usuários legítimos que compartilham o mesmo IP
# (ex: 100 funcionários de uma empresa atrás do mesmo NAT/proxy).
# Apenas o usuário que errou a senha repetidamente é bloqueado.
#
# Estrutura: {email: [timestamps_de_tentativas_falhas]}
_failed_attempts: dict[str, list[float]] = defaultdict(list)

MAX_FAILED_ATTEMPTS = 5        # tentativas falhas antes do bloqueio
ATTEMPT_WINDOW_SECONDS = 300   # janela de 5 minutos para contar tentativas
LOCKOUT_SECONDS = 900          # bloqueio de 15 minutos após exceder


def check_user_rate_limit(email: str) -> None:
    """
    Verifica se o usuário (por email) excedeu o limite de tentativas falhas.
    Lança HTTP 429 se bloqueado.

    IMPORTANTE: O bloqueio é por email, não por IP.
    Isso garante que outros usuários no mesmo IP não sejam afetados.
    """
    now = time.time()
    email_key = email.lower().strip()

    # Remove tentativas antigas fora da janela de tempo
    _failed_attempts[email_key] = [
        t for t in _failed_attempts[email_key]
        if now - t < ATTEMPT_WINDOW_SECONDS
    ]

    if len(_failed_attempts[email_key]) >= MAX_FAILED_ATTEMPTS:
        oldest = _failed_attempts[email_key][0]
        wait = int(LOCKOUT_SECONDS - (now - oldest))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Conta temporariamente bloqueada por excesso de tentativas de login. "
                f"Aguarde {max(wait, 0)} segundos ou contate o administrador."
            ),
            headers={"Retry-After": str(max(wait, 0))},
        )


def record_failed_login(email: str) -> None:
    """Registra uma tentativa de login falha para o email."""
    email_key = email.lower().strip()
    _failed_attempts[email_key].append(time.time())


def clear_failed_logins(email: str) -> None:
    """Limpa as tentativas falhas após login bem-sucedido."""
    email_key = email.lower().strip()
    _failed_attempts.pop(email_key, None)


def get_remaining_attempts(email: str) -> int:
    """Retorna quantas tentativas restam antes do bloqueio."""
    now = time.time()
    email_key = email.lower().strip()
    recent = [t for t in _failed_attempts.get(email_key, []) if now - t < ATTEMPT_WINDOW_SECONDS]
    return max(0, MAX_FAILED_ATTEMPTS - len(recent))


# ─── Validação de Senha ───────────────────────────────────────────────────────

def validate_password_strength(password: str) -> None:
    """
    Valida a complexidade da senha.
    Lança ValueError se não atender os requisitos.
    """
    if len(password) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres.")
    if not any(c.isupper() for c in password):
        raise ValueError("A senha deve conter ao menos uma letra maiúscula.")
    if not any(c.islower() for c in password):
        raise ValueError("A senha deve conter ao menos uma letra minúscula.")
    if not any(c.isdigit() for c in password):
        raise ValueError("A senha deve conter ao menos um número.")


# ─── Senhas ───────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Gera o hash bcrypt (rounds=12) de uma senha."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha plana corresponde ao hash armazenado."""
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def generate_temp_password(length: int = 12) -> str:
    """
    Gera uma senha temporária aleatória com alta entropia.
    Garante ao menos 1 maiúscula, 1 minúscula, 1 dígito e 1 especial.
    """
    import secrets
    import string
    upper = string.ascii_uppercase
    lower = string.ascii_lowercase
    digits = string.digits
    special = "!@#$%^&*"
    all_chars = upper + lower + digits + special

    password = [
        secrets.choice(upper),
        secrets.choice(lower),
        secrets.choice(digits),
        secrets.choice(special),
    ]
    password += [secrets.choice(all_chars) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


# ─── JWT ──────────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria um token JWT com os dados fornecidos."""
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access",
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decodifica e valida um token JWT.
    Lança JWTError se inválido ou expirado.
    """
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Tipo de token inválido.")
    return payload


# ─── Dependências FastAPI ─────────────────────────────────────────────────────

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """Dependency: retorna o usuário autenticado a partir do token Bearer."""
    from ..models.user import User

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado. Faça login novamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        user_id_int = int(user_id)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    user = db.query(User).filter(
        User.id == user_id_int,
        User.is_active == True,
    ).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo.",
        )
    return user


def require_admin(current_user=Depends(get_current_user)):
    """Dependency: exige que o usuário autenticado seja admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores.",
        )
    return current_user


def require_pesquisador_or_admin(current_user=Depends(get_current_user)):
    """Dependency: exige pesquisador ou admin."""
    if current_user.role not in ("admin", "pesquisador"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a pesquisadores e administradores.",
        )
    return current_user
