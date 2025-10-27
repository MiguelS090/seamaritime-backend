from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
from enum import Enum

# Mantemos o enum com "admin" e "user"
class AccessLevelEnum(str, Enum):
    admin = "admin"
    user = "user"

class UserCreate(BaseModel):
    username: str
    password: str
    # Aqui usamos "str" em vez de EmailStr, pois aceitamos "oiko" ou algo com "@"
    email: str
    organization: Optional[str] = None
    organization_user_id: Optional[str] = None
    access_level: Optional[AccessLevelEnum] = AccessLevelEnum.user

    # Validador: permite apenas strings que tenham '@' ou sejam "oiko"
    @validator("email")
    def validate_email(cls, value):
        if value != "oiko" and "@" not in value:
            raise ValueError("O email deve conter '@' ou ser 'oiko'.")
        return value

    class Config:
        from_attributes = True

# Se quiser permitir "oiko" no update,
# também troque EmailStr -> str e inclua validador (opcional).
class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    # Opcional trocar para "str" se quiser permitir "oiko" via update
    # email: Optional[EmailStr] = None
    email: Optional[str] = None
    organization: Optional[str] = None
    organization_user_id: Optional[str] = None
    access_level: Optional[AccessLevelEnum] = None

    class Config:
        from_attributes = True

# Aqui removemos EmailStr para permitir "oiko"
# e mantemos "str" para exibir qualquer valor que tenha sido salvo no DB.
class UserRead(BaseModel):
    id: int
    username: str
    email: str
    organization: Optional[str] = None
    organization_user_id: Optional[str] = None
    access_level: AccessLevelEnum
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    # Se login aceita de fato só e-mails "com @", mantenha EmailStr,
    # mas se quiser que "oiko" também faça login, trocar para "str" e validador.
    email: str
    password: str

class UserAzure(BaseModel):
    username: str
    password: str
    # Se quisermos permitir "oiko" via Azure, trocar EmailStr -> str e validador
    email: str
    organization: str
    organization_user_id: str
    access_level: Optional[AccessLevelEnum] = AccessLevelEnum.user

class Token(BaseModel):
    access_token: str
    token_type: str
