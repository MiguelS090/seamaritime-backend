from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import schemas
from app.controllers import chat as chat_controller
from app.core.database import get_db

router = APIRouter(
    prefix="/chats",
    tags=["chats"]
)

# 🚀 Rota para criar um novo chat
@router.post("/add_chat", response_model=schemas.ChatRead, status_code=status.HTTP_201_CREATED)
def add_chat(chat_create: schemas.ChatCreate, db: Session = Depends(get_db)):
    return chat_controller.create_chat(chat_create, db)

# 📃 Rota para obter mensagens de um chat pelo ID
@router.get("/get_messages/{chat_id}", response_model=List[schemas.MessageRead])
def get_messages(chat_id: int, db: Session = Depends(get_db)):
    return chat_controller.get_messages_by_chat_id(chat_id, db)

# 🗑️ Rota para deletar um chat pelo ID
@router.delete("/delete_chat/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(chat_id: int, db: Session = Depends(get_db)):
    return chat_controller.delete_chat(chat_id, db)

# 🔄 Rota para atualizar o título de um chat
@router.put("/update_chat_title/{chat_id}", response_model=schemas.ChatRead)
def update_chat_title(chat_id: int, request: schemas.UpdateChatTitleRequest, db: Session = Depends(get_db)):
    return chat_controller.update_chat_title(chat_id, request.title, db)

# 📃 Rota para obter chats por ID do usuário
@router.get("/get_chats/{user_id}", response_model=List[schemas.ChatRead])
def get_chats(user_id: int, db: Session = Depends(get_db)):
    return chat_controller.get_chats_by_user_id(db, user_id)

# 🕒 Rota para obter as últimas k mensagens de um chat
@router.get("/get_last_k_messages/{chat_id}", response_model=List[str])
def get_last_k_messages(chat_id: int, k: int, db: Session = Depends(get_db)):
    return chat_controller.get_last_k_messages(chat_id, k, db)
