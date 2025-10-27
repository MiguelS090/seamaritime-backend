# app/core/database.py
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

Base = declarative_base()

def create_db_engine(db_url: str):
    if not db_url:
        raise ValueError("DATABASE_URL não está definido ou está vazio.")
    return create_engine(db_url, pool_pre_ping=True)

# Engine principal (leitura/escrita)
engine = create_db_engine(settings.DATABASE_URL)

# Variáveis globais para o engine e session do read-only
read_only_engine = None
ReadOnlySessionLocal = None

def fetch_config_db_url():
    """
    Tenta buscar a URL de conexão na tabela de configuração (configDB).
    Retorna o valor encontrado ou None se não houver registro.
    """
    from app.models.configDB import ConfigDB  # Certifique-se de que o caminho está correto
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        # Seleciona a database_url do registro mais recente (ou o primeiro registro)
        result = db.execute(
            text('SELECT "database_url" FROM "configDB" LIMIT 1')
        ).fetchone()
        if result and result[0]:
            return result[0]
        return None
    finally:
        db.close()

def get_read_only_engine():
    """
    Cria (ou recria) o engine read-only buscando sempre a URL de conexão na tabela configDB.
    Se nenhum registro for encontrado, utiliza o engine principal.
    """
    global read_only_engine, ReadOnlySessionLocal
    config_db_url = fetch_config_db_url()
    if config_db_url:
        read_only_engine = create_db_engine(config_db_url)
    else:
        read_only_engine = engine
    ReadOnlySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=read_only_engine)
    return read_only_engine

# Inicializa o read-only engine na carga do módulo (sempre usando a URL do configDB)
get_read_only_engine()

# Session para leitura/escrita
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def refresh_read_only_engine(new_url: str):
    """
    Recria o read-only engine usando a nova URL.
    Deve ser chamado após uma atualização de configDB.
    """
    global read_only_engine, ReadOnlySessionLocal
    read_only_engine = create_db_engine(new_url)
    ReadOnlySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=read_only_engine)
    print("Read-only engine atualizado para:", new_url)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_read_only_db():
    if ReadOnlySessionLocal is None:
        raise RuntimeError("⚠️ Banco de dados somente leitura não configurado.")
    db = ReadOnlySessionLocal()
    try:
        yield db
    finally:
        db.close()
