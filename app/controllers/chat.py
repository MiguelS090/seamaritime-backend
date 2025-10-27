from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import List
import uuid

from app.models.chat import Chat
from app.schemas.chat import ChatCreate, ChatRead, UpdateChatTitleRequest
from app.schemas.message import MessageRead
from app.models.message import Message
from app.models.user import User

# 🚀 Função para criar um novo chat
def create_chat(chat_create: ChatCreate, db: Session) -> ChatRead:
    user = db.query(User).filter(User.id == chat_create.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found 🚫")
    thread_id = str(uuid.uuid4())
    new_chat = Chat(
        user_id=chat_create.user_id,
        title=chat_create.title,
        summary=chat_create.summary,
        thread=thread_id
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return ChatRead.from_orm(new_chat)

# 📃 Função para obter mensagens de um chat pelo ID
def get_messages_by_chat_id(chat_id: int, db: Session) -> List[MessageRead]:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found 🚫")
    messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.id.asc()).all()
    return [MessageRead.from_orm(message) for message in messages]

# 🗑️ Função para deletar um chat pelo ID
def delete_chat(chat_id: int, db: Session):
    chat_instance = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat_instance:
        raise HTTPException(status_code=404, detail="Chat not found 🚫")
    # Apenas apaga a instância do chat; os relacionamentos em cascade cuidarão do resto
    db.delete(chat_instance)
    db.commit()
    return {"detail": "Chat deleted successfully ✅"}

# 🔄 Função para atualizar o título de um chat
def update_chat_title(chat_id: int, title: str, db: Session) -> ChatRead:
    chat_instance = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat_instance:
        raise HTTPException(status_code=404, detail="Chat not found 🚫")
    chat_instance.title = title
    db.commit()
    db.refresh(chat_instance)
    return ChatRead.from_orm(chat_instance)

# 📃 Função para obter chats por ID do usuário
def get_chats_by_user_id(db: Session, user_id: int) -> List[ChatRead]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found 🚫")
    chats = db.query(Chat).filter(Chat.user_id == user_id).order_by(Chat.id.desc()).all()
    return [ChatRead.from_orm(chat) for chat in chats]

# 🕒 Função para obter as últimas k mensagens de um chat
def get_last_k_messages(chat_id: int, k: int, db: Session) -> List[str]:
    if k <= 0:
        return []
    messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.id.desc()).limit(k).all()
    return messages