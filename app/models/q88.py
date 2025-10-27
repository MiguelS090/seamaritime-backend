# app/models/q88.py
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, TIMESTAMP, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Q88Form(Base):
    """Modelo para armazenar formulários Q88 processados"""
    __tablename__ = "q88_forms"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(String(255), unique=True, nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    processing_status = Column(String(50), default="pending")  
    # processing_progress = Column(String(500), nullable=True)  # TEMPORÁRIO: Removido até criar migração
    ocr_model_version = Column(String(100), nullable=True)
    total_confidence_score = Column(Float, nullable=True)
    form_data = Column(JSON, nullable=True)  
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relacionamento com seções
    sections = relationship("Q88Section", back_populates="form", cascade="all, delete-orphan")

class Q88Section(Base):
    """Modelo para armazenar seções do formulário Q88"""
    __tablename__ = "q88_sections"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("q88_forms.id"), nullable=False)
    name = Column(String(255), nullable=False)
    order = Column(Integer, nullable=False)
    is_required = Column(Boolean, default=True)
    section_data = Column(JSON, nullable=True) 
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relacionamentos
    form = relationship("Q88Form", back_populates="sections")
    fields = relationship("Q88Field", back_populates="section", cascade="all, delete-orphan")

class Q88Field(Base):
    """Modelo para armazenar campos individuais do formulário Q88"""
    __tablename__ = "q88_fields"

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("q88_sections.id"), nullable=False)
    field_index = Column(Integer, nullable=False)
    label = Column(String(255), nullable=False)
    field_type = Column(String(50), nullable=False)  
    values = Column(JSON, nullable=True)  
    confidence_scores = Column(JSON, nullable=True)  
    need_confirmation = Column(Boolean, default=False)
    coordinates = Column(JSON, nullable=True)  
    validation_rules = Column(JSON, nullable=True)  
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relacionamento
    section = relationship("Q88Section", back_populates="fields")

class Q88ProcessingLog(Base):
    """Modelo para log de processamento OCR"""
    __tablename__ = "q88_processing_logs"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("q88_forms.id"), nullable=False)
    processing_step = Column(String(100), nullable=False)  
    status = Column(String(50), nullable=False) 
    message = Column(Text, nullable=True)
    processing_time = Column(Float, nullable=True) 
    processing_metadata = Column(JSON, nullable=True)  
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # Relacionamento
    form = relationship("Q88Form")

class Q88ValidationResult(Base):
    """Modelo para resultados de validação de campos"""
    __tablename__ = "q88_validation_results"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("q88_fields.id"), nullable=False)
    validation_type = Column(String(100), nullable=False) 
    is_valid = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    corrected_value = Column(JSON, nullable=True)  
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # Relacionamento
    field = relationship("Q88Field")