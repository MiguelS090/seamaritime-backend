from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_jwt_token(user_id: int, username: str, access_level: str) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "access_level": access_level,
        "exp": datetime.utcnow() + timedelta(hours=24)  # Token válido por 24 horas
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
