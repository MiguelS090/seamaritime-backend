from sqlalchemy import Column, Integer, Text, String, TIMESTAMP, text
from sqlalchemy.sql import func
from app.core.database import Base

class ConfigDB(Base):
    __tablename__ = "configDB"

    id = Column(Integer, primary_key=True, index=True)
    description_db = Column(Text, nullable=False)
    database_url = Column(String(255), nullable=False)
    
    updated_at = Column(
        TIMESTAMP,
        onupdate=func.current_timestamp()
    )
