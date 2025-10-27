from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import schemas
from app.controllers import configDB as config_controller
from app.core.database import get_db

router = APIRouter(
    prefix="/configDB",
    tags=["configDB"]
)

# 🚀 Rota para criar uma nova configuração
@router.post("/", response_model=schemas.ConfigRead, status_code=status.HTTP_201_CREATED)
def create_config(config_create: schemas.ConfigCreate, db: Session = Depends(get_db)):
    return config_controller.create_config(config_create, db)

# 🔍 Rota para obter uma configuração pelo ID
@router.get("/{config_id}", response_model=schemas.ConfigRead)
def get_config(config_id: int, db: Session = Depends(get_db)):
    return config_controller.get_config(config_id, db)

# 🔄 Rota para atualizar uma configuração pelo ID
@router.put("/{config_id}", response_model=schemas.ConfigRead)
def update_config(config_id: int, config_update: schemas.ConfigUpdate, db: Session = Depends(get_db)):
    return config_controller.update_config(config_id, config_update, db)

# 🗑️ Rota para deletar uma configuração pelo ID
@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_config(config_id: int, db: Session = Depends(get_db)):
    return config_controller.delete_config(config_id, db)

# 📃 Rota para listar todas as configurações
@router.get("/", response_model=List[schemas.ConfigRead])
def list_configs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return config_controller.list_configs(db, skip=skip, limit=limit)
