# app/models/file.py
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    file_path = Column(String(255), nullable=False)  # Caminho do arquivo
    file_type = Column(String(50), nullable=False)   # Ex: "application/pdf", etc.

    created_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp()
    )

    message = relationship("Message", back_populates="files")
