"""
CEBIO Brasil - Configuração Central
SQLite para testes locais; troque DATABASE_URL para MySQL em produção.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Banco de Dados ───────────────────────────────────────────────────────────
# Para TESTES: SQLite (sem precisar de servidor)
# Para PRODUÇÃO MySQL/TiDB: variável de ambiente DATABASE_URL
# NOTA: Usando SQLite para hospedagem simplificada
_raw_db_url = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/cebio_brasil.db")

# Normaliza a URL para uso com SQLAlchemy
# Remove parâmetros SSL inline (ex: ?ssl={...}) que o SQLAlchemy não entende
import re as _re
_db_url_clean = _re.sub(r'\?ssl=.*$', '', _raw_db_url)
if _db_url_clean.startswith("mysql://") and not _db_url_clean.startswith("sqlite"):
    _db_url_clean = _db_url_clean.replace("mysql://", "mysql+pymysql://", 1)

DATABASE_URL = _raw_db_url
DATABASE_URL_CLEAN = _db_url_clean

# ─── Segurança JWT ────────────────────────────────────────────────────────────
# IMPORTANTE: Em produção, defina SECRET_KEY como variável de ambiente com valor aleatório de 32+ bytes
# Gerar: python3 -c "import secrets; print(secrets.token_hex(32))"
import secrets as _secrets
_env_secret = os.getenv("SECRET_KEY", "")
if os.getenv("ENV", "development") == "production" and not _env_secret:
    raise RuntimeError("SECRET_KEY não definida em produção! Defina a variável de ambiente SECRET_KEY.")
# Em desenvolvimento, gera uma chave aleatória por sessão se não definida
SECRET_KEY = _env_secret if _env_secret else _secrets.token_hex(32)

ALGORITHM = "HS256"
# Token expira em 4 horas (redução de 8h para 4h por segurança)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "240"))

# ─── Uploads ──────────────────────────────────────────────────────────────────
UPLOAD_DIR = BASE_DIR / "app" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "fotos").mkdir(exist_ok=True)
(UPLOAD_DIR / "documentos").mkdir(exist_ok=True)

MAX_FOTO_SIZE_MB = 5
MAX_DOC_SIZE_MB = 20
ALLOWED_FOTO_TYPES = {"image/jpeg", "image/png", "image/jpg"}
ALLOWED_DOC_TYPES = {"application/pdf"}

# ─── CORS ─────────────────────────────────────────────────────────────────────
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5500,http://127.0.0.1:5500,http://localhost:8080,http://127.0.0.1:8080"
).split(",")

# ─── App ──────────────────────────────────────────────────────────────────────
APP_TITLE = "CEBIO Brasil API"
APP_DESCRIPTION = """
## API Backend do CEBIO Brasil

Sistema de gerenciamento de projetos de pesquisa, ensino e extensão.

### Funcionalidades
- **Autenticação JWT**: Admin cria usuários; login verifica no banco de dados
- **Gestão de Usuários**: CRUD completo com funções administrativas
- **Gestão de Projetos**: Submissão, revisão, aprovação/rejeição em lote
- **Auditoria**: Log completo de todas as ações do sistema
- **Notificações**: Sistema de notificações com envio em massa
- **Relatórios**: Exportação CSV/JSON de dados
- **Administração**: Modo manutenção, backup, configurações do sistema

### Roles
- `admin`: Acesso total ao sistema
- `pesquisador`: Gerencia seus próprios projetos
- `bolsista`: Acesso básico
"""
APP_VERSION = "1.0.0"
