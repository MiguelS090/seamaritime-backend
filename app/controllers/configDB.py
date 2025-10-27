from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import List

from app.models.configDB import ConfigDB
from app.schemas.configDB import ConfigCreate, ConfigRead, ConfigUpdate

from app.core.config import settings
from app.core.database import refresh_read_only_engine

# 🚀 Função para criar uma nova configuração
def create_config(config_create: ConfigCreate, db: Session) -> ConfigRead:
    new_config = ConfigDB(
        description_db=config_create.description_db,
        database_url=config_create.database_url
    )
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    return ConfigRead.from_orm(new_config)

# 🔍 Função para obter uma configuração pelo ID
def get_config(config_id: int, db: Session) -> ConfigRead:
    config = db.query(ConfigDB).filter(ConfigDB.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found 🚫")
    return ConfigRead.from_orm(config)

# 🔄 Função para atualizar uma configuração pelo ID
def update_config(config_id: int, config_update: ConfigUpdate, db: Session) -> ConfigRead:
    config = db.query(ConfigDB).filter(ConfigDB.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found 🚫")
    if config_update.description_db is not None:
        config.description_db = config_update.description_db
    if config_update.database_url is not None:
        config.database_url = config_update.database_url
    db.commit()
    db.refresh(config)
    
    refresh_read_only_engine(config.database_url)
    
    return ConfigRead.from_orm(config)

# 🗑️ Função para deletar uma configuração pelo ID
def delete_config(config_id: int, db: Session):
    config = db.query(ConfigDB).filter(ConfigDB.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found 🚫")
    db.delete(config)
    db.commit()
    return {"detail": "Config deleted successfully ✅"}

# 📃 Função para listar todas as configurações
def list_configs(db: Session, skip: int = 0, limit: int = 100) -> List[ConfigRead]:
    configs = db.query(ConfigDB).offset(skip).limit(limit).all()
    return [ConfigRead.from_orm(config) for config in configs]
