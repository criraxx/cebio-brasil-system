"""
CEBIO Brasil - Aplicação FastAPI Principal
Registra todos os roteadores e configura middlewares.
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from .config import (
    APP_TITLE, APP_DESCRIPTION, APP_VERSION,
    CORS_ORIGINS, UPLOAD_DIR,
)
from .database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cria as tabelas no banco ao iniciar a aplicação."""
    # Importa todos os modelos para garantir que sejam registrados no Base
    from .models import User, Project, ProjectVersion, ProjectComment
    from .models import ProjectAuthor, ProjectLink, ProjectFile
    from .models import AuditLog, Notification, SystemConfig
    from .models.category import Category, AcademicLevel

    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas criadas/verificadas com sucesso.")

    # Cria o usuário admin padrão se não existir
    from .database import SessionLocal
    from .utils.security import hash_password, generate_temp_password
    import secrets
    
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@cebio.org.br").first()
        if not admin:
            # Gerar senha aleatória segura
            admin_password = secrets.token_urlsafe(16)  # 16 bytes = ~21 caracteres
            
            admin_user = User(
                name="Administrador CEBIO",
                email="admin@cebio.org.br",
                hashed_password=hash_password(admin_password),
                role="admin",
                is_active=True,
                is_temp_password=True,
                must_change_password=True,
                institution="CEBIO Brasil",
            )
            db.add(admin_user)
            db.commit()
            
            print("="*70)
            print("✅ Usuário admin padrão criado com sucesso!")
            print("="*70)
            print(f"📧 Email: admin@cebio.org.br")
            print(f"🔑 Senha: {admin_password}")
            print("="*70)
            print("⚠️  IMPORTANTE:")
            print("   1. SALVE ESTA SENHA IMEDIATAMENTE!")
            print("   2. Esta senha NÃO será mostrada novamente")
            print("   3. Você será forçado a trocar a senha no primeiro login")
            print("   4. Não compartilhe esta senha por email ou mensagem")
            print("="*70)
            
            # Salvar senha em arquivo temporário (apenas em desenvolvimento)
            import os
            if os.getenv("ENV", "development") == "development":
                with open("ADMIN_PASSWORD.txt", "w") as f:
                    f.write(f"Admin Email: admin@cebio.org.br\n")
                    f.write(f"Admin Password: {admin_password}\n")
                    f.write(f"Generated at: {datetime.utcnow()}\n")
                    f.write("\n⚠️  DELETE THIS FILE AFTER SAVING THE PASSWORD!\n")
                print("📄 Senha também salva em: ADMIN_PASSWORD.txt")
                print("   (DELETE este arquivo após salvar a senha!)")
                print("="*70)
    except Exception as e:
        print(f"⚠️  Erro ao criar admin padrão: {e}")
    finally:
        db.close()

    yield
    print("🔴 Aplicação encerrada.")


# ─── Instância da aplicação ───────────────────────────────────────────────────
_is_production = os.getenv("ENV", "development") == "production"

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    # Desabilita docs em produção para não expor a API publicamente
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
# Permite qualquer subdomínio *.manus.computer (hospedagem temporária) + localhost
import re as _cors_re

class DynamicCORSMiddleware(BaseHTTPMiddleware):
    """Aceita qualquer origem *.manus.computer e localhost para desenvolvimento."""
    ALLOWED_PATTERN = _cors_re.compile(
        r'^https?://(localhost|127\.0\.0\.1)(:\d+)?$'
        r'|^https://[\w-]+-[\w-]+\.us2\.manus\.computer$'
        r'|^https://[\w.-]+\.manus\.space$'
    )

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin", "")
        if request.method == "OPTIONS":
            response = JSONResponse({}, status_code=200)
        else:
            response = await call_next(request)
        if origin and (self.ALLOWED_PATTERN.match(origin) or origin in CORS_ORIGINS):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, X-Requested-With"
            response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
            response.headers["Access-Control-Max-Age"] = "600"
        return response

app.add_middleware(DynamicCORSMiddleware)

# ─── Headers de Segurança HTTP ────────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if _is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# ─── Arquivos estáticos (uploads) ─────────────────────────────────────────────
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# ─── Middleware de manutenção ─────────────────────────────────────────────────
@app.middleware("http")
async def maintenance_middleware(request: Request, call_next):
    """Bloqueia requisições quando o sistema está em modo manutenção (exceto admin e health)."""
    # Rotas que sempre passam (health check, login, docs, admin)
    bypass_paths = [
        "/api/admin/health",
        "/api/admin/maintenance",
        "/api/auth/login",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    if any(request.url.path.startswith(p) for p in bypass_paths):
        return await call_next(request)

    # Verifica modo manutenção no banco
    try:
        from .database import SessionLocal
        from .models.system import SystemConfig
        db = SessionLocal()
        try:
            config = db.query(SystemConfig).filter(SystemConfig.key == "maintenance_mode").first()
            if config and config.value == "true":
                msg_config = db.query(SystemConfig).filter(SystemConfig.key == "maintenance_message").first()
                message = msg_config.value if msg_config else "Sistema em manutenção."

                # Permite admins mesmo em manutenção
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    from .utils.security import decode_token
                    try:
                        payload = decode_token(auth_header.split(" ")[1])
                        if payload.get("role") == "admin":
                            return await call_next(request)
                    except Exception:
                        pass

                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "maintenance",
                        "message": message,
                        "status": "maintenance",
                    },
                )
        finally:
            db.close()
    except Exception:
        pass

    return await call_next(request)


# ─── Registro de Roteadores ───────────────────────────────────────────────────
from .routers.auth import router as auth_router
from .routers.users import router as users_router
from .routers.projects import router as projects_router
from .routers.audit import router as audit_router
from .routers.notifications import router as notifications_router
from .routers.reports import router as reports_router
from .routers.admin import router as admin_router
from .routers.files import router as files_router
from .routers.categories import router as categories_router

API_PREFIX = "/api"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(projects_router, prefix=API_PREFIX)
app.include_router(audit_router, prefix=API_PREFIX)
app.include_router(notifications_router, prefix=API_PREFIX)
app.include_router(reports_router, prefix=API_PREFIX)
app.include_router(admin_router, prefix=API_PREFIX)
app.include_router(files_router, prefix=API_PREFIX)
app.include_router(categories_router, prefix=API_PREFIX)


# ─── Rota raiz ────────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
def root():
    return {
        "app": APP_TITLE,
        "version": APP_VERSION,
        "docs": "/docs",
        "status": "online",
    }


# ─── Health Check para UptimeRobot ────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    """Endpoint simples de health check para monitoramento."""
    return {"status": "ok", "service": "cebio-brasil"}


@app.head("/health", tags=["Health"])
def health_check_head():
    """HEAD request para health check."""
    return {}
