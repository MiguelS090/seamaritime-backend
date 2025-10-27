from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.schemas.user import UserRead, UserCreate, UserUpdate, UserLogin, UserAzure, Token
from app.schemas.message import MessageResponse
from app.controllers import user as user_controller
from app.core.database import get_db

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

# 🚀 Rota para registrar um novo usuário
@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(user_create: UserCreate, db: Session = Depends(get_db)):
    return user_controller.create_user(user_create, db)

# 🔄 Rota para executar o serviço de recuperação
@router.post("/retrieval_service", response_model=MessageResponse)
def retrieval_service(db: Session = Depends(get_db)):
    return user_controller.retrieval_service(db)

# 🔄 Rota para atualizar informações do usuário
@router.put("/update_user/{user_id}", response_model=UserRead)
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    return user_controller.update_user(user_id, user_update, db)

# 📃 Rota para listar todos os usuários
@router.get("/", response_model=List[UserRead])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return user_controller.list_users(db, skip=skip, limit=limit)

# 🔍 Rota para obter um usuário pelo ID
@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    return user_controller.get_user(user_id, db)

# 🗑️ Rota para deletar um usuário pelo ID
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    return user_controller.delete_user(user_id, db)
