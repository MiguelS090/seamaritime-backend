from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import schemas
from app.controllers import user as user_controller
from app.core.database import get_db

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

# 🔑 Rota para login de usuário
@router.post("/login", response_model=schemas.Token)
def login(user_login: schemas.UserLogin, db: Session = Depends(get_db)):
    return user_controller.login_user(user_login, db)

# 🔑 Rota para login via Azure
@router.post("/login_azure", response_model=schemas.Token)
def login_azure(user_azure: schemas.UserAzure, db: Session = Depends(get_db)):
    return user_controller.login_azure(user_azure, db)
