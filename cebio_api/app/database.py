"""
CEBIO Brasil - Configuração do Banco de Dados
SQLAlchemy com suporte a SQLite (teste) e MySQL (produção)
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import DATABASE_URL, DATABASE_URL_CLEAN

# Para SQLite: habilitar foreign keys (não ativo por padrão no SQLite)
connect_args = {}
if DATABASE_URL_CLEAN.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif "tidbcloud" in DATABASE_URL_CLEAN or "ssl" in DATABASE_URL_CLEAN:
    connect_args = {"ssl": {"rejectUnauthorized": False}}

engine = create_engine(
    DATABASE_URL_CLEAN,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Habilitar foreign keys no SQLite
if DATABASE_URL_CLEAN.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency para injetar sessão do banco nas rotas FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
