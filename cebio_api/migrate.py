"""
CEBIO Brasil - Script de Migração
Cria tabelas novas e adiciona colunas faltantes nas tabelas existentes.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine, Base
from app.models import *  # Importa todos os modelos
from sqlalchemy import text, inspect

def column_exists(conn, table_name, column_name):
    """Verifica se uma coluna existe em uma tabela (compatível com SQLite e MySQL)."""
    try:
        # Tenta com SQLite primeiro (PRAGMA table_info)
        result = conn.execute(text(f"PRAGMA table_info({table_name})"))
        columns = [row[1] for row in result.fetchall()]
        return column_name in columns
    except Exception:
        # Se falhar, tenta com MySQL
        try:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = :table_name "
                "AND COLUMN_NAME = :column_name"
            ), {"table_name": table_name, "column_name": column_name})
            return result.scalar() > 0
        except Exception:
            return False

def table_exists(conn, table_name):
    """Verifica se uma tabela existe (compatível com SQLite e MySQL)."""
    try:
        # Tenta com SQLite primeiro
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"), {"table_name": table_name})
        return result.fetchone() is not None
    except Exception:
        # Se falhar, tenta com MySQL
        try:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = :table_name"
            ), {"table_name": table_name})
            return result.scalar() > 0
        except Exception:
            return False

def run_migration():
    print("🔄 Iniciando migração do banco de dados CEBIO Brasil...")
    
    with engine.connect() as conn:
        # ─── Tabela users ─────────────────────────────────────────────────────
        if table_exists(conn, "users"):
            print("📋 Tabela 'users' existe. Verificando colunas...")
            
            migrations_users = [
                ("cpf", "ALTER TABLE users ADD COLUMN cpf VARCHAR(20) NULL"),
                ("hashed_password", "ALTER TABLE users ADD COLUMN hashed_password VARCHAR(255) NOT NULL DEFAULT ''"),
                ("institution", "ALTER TABLE users ADD COLUMN institution VARCHAR(300) NULL"),
                ("is_active", "ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"),
                ("is_temp_password", "ALTER TABLE users ADD COLUMN is_temp_password BOOLEAN NOT NULL DEFAULT TRUE"),
                ("last_login", "ALTER TABLE users ADD COLUMN last_login DATETIME NULL"),
                ("created_by", "ALTER TABLE users ADD COLUMN created_by INT NULL"),
            ]
            
            for col_name, sql in migrations_users:
                if not column_exists(conn, "users", col_name):
                    try:
                        conn.execute(text(sql))
                        conn.commit()
                        print(f"  ✅ Coluna 'users.{col_name}' adicionada.")
                    except Exception as e:
                        print(f"  ⚠️  Erro ao adicionar 'users.{col_name}': {e}")
                else:
                    print(f"  ✓ Coluna 'users.{col_name}' já existe.")
        else:
            print("📋 Criando tabela 'users'...")
        
        # ─── Cria todas as tabelas novas ──────────────────────────────────────
        print("\n📋 Criando tabelas novas (se não existirem)...")
        Base.metadata.create_all(bind=engine, checkfirst=True)
        print("  ✅ Tabelas criadas/verificadas.")
        
        # ─── Cria usuário admin padrão ────────────────────────────────────────
        print("\n👤 Verificando usuário admin padrão...")
        try:
            result = conn.execute(text("SELECT id FROM users WHERE email = 'admin@cebio.org.br' LIMIT 1"))
            admin = result.fetchone()
            
            if not admin:
                import warnings
                warnings.filterwarnings("ignore")
                from app.utils.security import hash_password
                hashed = hash_password("Admin@2024!")
                conn.execute(text("""
                    INSERT INTO users (openId, name, email, hashed_password, role, is_active, is_temp_password, institution, createdAt, updatedAt, lastSignedIn)
                    VALUES ('cebio-admin-001', 'Administrador CEBIO', 'admin@cebio.org.br', :pwd, 'admin', TRUE, TRUE, 'CEBIO Brasil', NOW(), NOW(), NOW())
                """), {"pwd": hashed})
                conn.commit()
                print("  ✅ Admin padrão criado: admin@cebio.org.br / Admin@2024!")
                print("  ⚠️  ALTERE A SENHA DO ADMIN IMEDIATAMENTE APÓS O PRIMEIRO LOGIN!")
            else:
                print(f"  ✓ Admin já existe (id={admin[0]}). Verificando senha...")
                # Garante que o admin tem hashed_password definida
                admin_row = conn.execute(text("SELECT hashed_password, role FROM users WHERE email = 'admin@cebio.org.br' LIMIT 1")).fetchone()
                if admin_row and (not admin_row[0] or admin_row[0] == ''):
                    import warnings
                    warnings.filterwarnings("ignore")
                    from app.utils.security import hash_password
                    hashed = hash_password("Admin@2024!")
                    conn.execute(text("UPDATE users SET hashed_password = :pwd, role = 'admin', is_active = TRUE WHERE email = 'admin@cebio.org.br'"), {"pwd": hashed})
                    conn.commit()
                    print("  ✅ Senha do admin configurada: Admin@2024!")
                else:
                    print("  ✓ Admin já tem senha configurada.")
        except Exception as e:
            print(f"  ⚠️  Erro ao criar admin: {e}")
    
    print("\n✅ Migração concluída com sucesso!")

if __name__ == "__main__":
    run_migration()
