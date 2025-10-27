from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
from .file import FileRead  

class SenderEnum(str, Enum):
    user = "user"
    agent = "agent"

class MessageCreate(BaseModel):
    chat_id: int
    content: str

    class Config:
        from_attributes = True

class MessageUpdate(BaseModel):
    chat_id: Optional[int] = None
    sender: Optional[SenderEnum] = None  
    content: Optional[str] = None

    class Config:
        from_attributes = True

class MessageRead(BaseModel):
    id: int
    chat_id: int
    sender: SenderEnum
    content: str
    created_at: datetime
    files: List[FileRead] = []

    class Config:
        from_attributes = True

class IAResponse(BaseModel):
    user: str
    ia: str
    
    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    message: str
