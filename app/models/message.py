from sqlalchemy import Column, Integer, TIMESTAMP, ForeignKey, Enum, Text
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    sender = Column(Enum("user", "agent", name="message_senders"), nullable=False)
    content = Column(LONGTEXT, nullable=False)  
    created_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp()
    )

    chat = relationship("Chat", back_populates="messages")
    files = relationship(
        "File", 
        back_populates="message", 
        cascade="all, delete, delete-orphan"
    )
