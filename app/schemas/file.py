from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FileCreate(BaseModel):
    message_id: int
    file_path: str
    file_type: str

    class Config:
        from_attributes = True

class FileUpdate(BaseModel):
    message_id: Optional[int] = None
    file_path: Optional[str] = None
    file_type: Optional[str] = None

    class Config:
        from_attributes = True

class FileRead(BaseModel):
    id: int
    message_id: int
    file_path: str
    file_type: str
    created_at: datetime

    class Config:
        from_attributes = True
