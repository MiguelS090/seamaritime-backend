from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import List

from app.models.user import User
from app.schemas.user import UserCreate, UserAzure, UserLogin, UserUpdate, UserRead, Token
from app.schemas.message import MessageResponse
from app.core.security import hash_password, verify_password, create_jwt_token
import os
from app.services.retrieval import RetrievalService

from app.core.config import settings

admin_email = settings.ADMIN_EMAIL
admin_password = settings.ADMIN_PASSWORD
admin_username = settings.ADMIN_USERNAME or "admin"

# 🚀 Função para criar um novo usuário
def create_user(user_create: UserCreate, db: Session) -> UserRead:
    existing_user = db.query(User).filter(User.email == user_create.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists 🚫")
    hashed_pw = hash_password(user_create.password)
    new_user = User(
        username=user_create.username,
        password=hashed_pw,
        email=user_create.email,
        organization=user_create.organization,
        organization_user_id=user_create.organization_user_id,
        access_level=user_create.access_level or "user"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserRead.from_orm(new_user)

# 🔑 Função para login de usuário
def login_user(user_login: UserLogin, db: Session) -> Token:
    db_user = db.query(User).filter(User.email == user_login.email).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="User not found 🚫")
    if not verify_password(user_login.password, db_user.password):
        raise HTTPException(status_code=400, detail="Incorrect password 🚫")
    token = create_jwt_token(
        user_id=db_user.id,
        username=db_user.username,
        access_level=db_user.access_level
    )
    return Token(access_token=token, token_type="bearer")

# 🔑 Função para login via Azure
def login_azure(user_azure: UserAzure, db: Session) -> Token:
    db_user = db.query(User).filter(User.email == user_azure.email).first()
    if not db_user:
        db_user = create_user_azure(user_azure, db)
    else:
        if not db_user.organization:
            db_user.organization = user_azure.organization
            db_user.organization_user_id = user_azure.organization_user_id
            db.commit()
            db.refresh(db_user)
    token = create_jwt_token(
        user_id=db_user.id,
        username=db_user.username,
        access_level=db_user.access_level
    )
    return Token(access_token=token, token_type="bearer")

# 🚀 Função para criar um novo usuário via Azure
def create_user_azure(user_azure: UserAzure, db: Session) -> UserRead:
    existing_user = db.query(User).filter(User.email == user_azure.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists 🚫")
    hashed_pw = hash_password(user_azure.password)
    new_user = User(
        username=user_azure.username,
        password=hashed_pw,
        email=user_azure.email,
        organization=user_azure.organization,
        organization_user_id=user_azure.organization_user_id,
        access_level=user_azure.access_level or "user"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserRead.from_orm(new_user)

# 🔄 Função para executar o serviço de recuperação
def retrieval_service(db: Session) -> MessageResponse:
    retrieval = RetrievalService()
    retrieval.delete_all_documents()
    retrieval.load_and_add_documents()
    return MessageResponse(message="Retrieval service executed successfully ✅")

# 🔄 Função para atualizar informações do usuário
def update_user(user_id: int, user_update: UserUpdate, db: Session) -> UserRead:
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found 🚫")
    if user_update.password:
        db_user.password = hash_password(user_update.password)
    if user_update.username:
        db_user.username = user_update.username
    if user_update.email:
        db_user.email = user_update.email
    if user_update.organization:
        db_user.organization = user_update.organization
    if user_update.organization_user_id:
        db_user.organization_user_id = user_update.organization_user_id
    if user_update.access_level:
        db_user.access_level = user_update.access_level
    db.commit()
    db.refresh(db_user)
    return UserRead.from_orm(db_user)

# 📃 Função para listar todos os usuários
def list_users(db: Session, skip: int = 0, limit: int = 100) -> List[UserRead]:
    users = db.query(User).offset(skip).limit(limit).all()
    return [UserRead.from_orm(user) for user in users]

# 🔍 Função para obter um usuário pelo ID
def get_user(user_id: int, db: Session) -> UserRead:
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found 🚫")
    return UserRead.from_orm(db_user)

# 🗑️ Função para deletar um usuário pelo ID
def delete_user(user_id: int, db: Session):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found 🚫")
    db.delete(db_user)
    db.commit()
    return {"detail": "User deleted successfully ✅"}

# 🔑 Função para criar usuário admin
def create_admin_user(db: Session):
    if not admin_email or not admin_password:
        print("ADMIN_EMAIL e ADMIN_PASSWORD devem ser definidos no .env")
        return
    db_user = db.query(User).filter(User.email == admin_email).first()
    if not db_user:
        user_create = UserCreate(
            username=admin_username,
            password=admin_password,
            email=admin_email,
            access_level="admin"
        )
        create_user(user_create, db)
        print(f"Admin user created with email: {admin_email} ✅")
    else:
        print(f"Admin user with email {admin_email} already exists. ⚠️")
