from pydantic import BaseModel, constr
from typing import Optional, List
from datetime import datetime
from .message import MessageRead  

class ChatCreate(BaseModel):
    user_id: int
    title: constr(max_length=40)
    thread: Optional[str] = None  # Agora compatível com o modelo
    summary: Optional[str] = None

    class Config:
        from_attributes = True

class ChatUpdate(BaseModel):
    user_id: Optional[int] = None
    title: Optional[constr(max_length=40)] = None
    thread: Optional[str] = None  # Agora compatível com o modelo
    summary: Optional[str] = None

    class Config:
        from_attributes = True

class UpdateChatTitleRequest(BaseModel):
    title: constr(max_length=40)

    class Config:
        from_attributes = True

class ChatRead(BaseModel):
    id: int
    user_id: int
    title: str
    thread: Optional[str] = None  # Agora compatível com o modelo
    summary: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


    class Config:
        from_attributes = True
