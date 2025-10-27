from sqlalchemy import Column, Integer, String, Enum, TIMESTAMP, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    organization = Column(String(255), nullable=True)  
    organization_user_id = Column(String(255), nullable=True)  
    access_level = Column(
        Enum("admin", "user", name="access_levels"),
        default="user",
        nullable=False
    )

    created_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp()
    )
    updated_at = Column(
        TIMESTAMP,
        onupdate=func.current_timestamp()
    )
    deleted_at = Column(TIMESTAMP, nullable=True)

    chats = relationship("Chat", back_populates="user")
