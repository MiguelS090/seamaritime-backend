import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.core.config import settings

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context



from app.core.database import Base

# import modelos
from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message
from app.models.file import File
from app.models.configDB import ConfigDB
from app.models.q88 import Q88Form, Q88Section, Q88Field, Q88ProcessingLog, Q88ValidationResult

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url():
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL não está definido no .env!")
    return settings.DATABASE_URL

def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    print("Rodando Alembic no modo OFFLINE...")
    run_migrations_offline()
else:
    print("Rodando Alembic no modo ONLINE...")
    run_migrations_online()
