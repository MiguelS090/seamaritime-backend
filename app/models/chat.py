# app/models/chat.py
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(40), nullable=False)
    thread = Column(Text)
    summary = Column(Text, nullable=True)  # Renomeado de 'thread' para 'summary'

    created_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP")
    )

    updated_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP")
    )
    deleted_at = Column(TIMESTAMP, nullable=True)

    user = relationship("User", back_populates="chats")
    messages = relationship(
        "Message", 
        back_populates="chat", 
        cascade="all, delete, delete-orphan"
    )
