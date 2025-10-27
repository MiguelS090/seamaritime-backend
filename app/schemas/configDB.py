from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ConfigCreate(BaseModel):
    description_db: str
    database_url: str

    class Config:
        from_attributes = True

class ConfigUpdate(BaseModel):
    description_db: Optional[str] = None
    database_url: Optional[str] = None

    class Config:
        from_attributes = True

class ConfigRead(BaseModel):
    id: int
    description_db: str
    database_url: str
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
