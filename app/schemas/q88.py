# app/schemas/q88.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime

class FieldType(str, Enum):
    """Tipos de campos suportados no formulário Q88"""
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    TABLE = "table"

class ConfidenceLevel(str, Enum):
    """Níveis de confiança para validação OCR"""
    HIGH = "high"      
    MEDIUM = "medium" 
    LOW = "low"       

class Q88Field(BaseModel):
    """Classe para representar um campo individual do formulário Q88"""
    index: int = Field(..., description="Índice sequencial do campo")
    label: str = Field(..., description="Rótulo/nome do campo")
    field_type: FieldType = Field(..., description="Tipo do campo")
    values: List[Union[str, int, float, bool]] = Field(default_factory=list, description="Valores extraídos")
    confidence_scores: List[float] = Field(default_factory=list, description="Scores de confiança para cada valor")
    need_confirmation: bool = Field(default=False, description="Se o campo precisa de confirmação manual")
    coordinates: Optional[Dict[str, float]] = Field(None, description="Coordenadas do campo na imagem (x, y, width, height)")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Regras de validação específicas")
    
    @validator('confidence_scores')
    def validate_confidence_scores(cls, v, values):
        """Valida se os scores de confiança estão entre 0 e 1"""
        if v:
            for score in v:
                if not 0 <= score <= 1:
                    raise ValueError("Confidence scores devem estar entre 0 e 1")
        return v
    
    @validator('values')
    def validate_values_count(cls, v, values):
        """Valida se o número de valores corresponde ao número de confidence scores"""
        if 'confidence_scores' in values and values['confidence_scores']:
            if len(v) != len(values['confidence_scores']):
                raise ValueError("Número de valores deve corresponder ao número de confidence scores")
        return v
    
    def get_confidence_level(self) -> ConfidenceLevel:
        """Retorna o nível de confiança baseado na média dos scores"""
        if not self.confidence_scores:
            return ConfidenceLevel.LOW
        
        avg_confidence = sum(self.confidence_scores) / len(self.confidence_scores)
        if avg_confidence >= 0.9:
            return ConfidenceLevel.HIGH
        elif avg_confidence >= 0.7:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def needs_manual_review(self) -> bool:
        """Determina se o campo precisa de revisão manual"""
        return self.need_confirmation or self.get_confidence_level() == ConfidenceLevel.LOW

class Q88Section(BaseModel):
    """Classe para representar uma seção do formulário Q88"""
    name: str = Field(..., description="Nome da seção")
    fields: List[Q88Field] = Field(default_factory=list, description="Lista de campos da seção")
    order: int = Field(..., description="Ordem da seção no formulário")
    is_required: bool = Field(default=True, description="Se a seção é obrigatória")
    
    def get_fields_needing_review(self) -> List[Q88Field]:
        """Retorna campos que precisam de revisão manual"""
        return [field for field in self.fields if field.needs_manual_review()]
    
    def get_completion_percentage(self) -> float:
        """Calcula a porcentagem de preenchimento da seção"""
        if not self.fields:
            return 0.0
        
        filled_fields = sum(1 for field in self.fields if field.values)
        return (filled_fields / len(self.fields)) * 100

class Q88Form(BaseModel):
    """Classe principal para representar o formulário Q88 completo"""
    form_id: Optional[str] = Field(None, description="ID único do formulário")
    sections: List[Q88Section] = Field(default_factory=list, description="Lista de seções do formulário")
    processing_status: str = Field(default="pending", description="Status do processamento")
    created_at: Optional[datetime] = Field(None, description="Data de criação")
    updated_at: Optional[datetime] = Field(None, description="Data da última atualização")
    file_path: Optional[str] = Field(None, description="Caminho do arquivo original")
    ocr_model_version: Optional[str] = Field(None, description="Versão do modelo OCR utilizado")
    total_confidence_score: Optional[float] = Field(None, description="Score de confiança geral")
    
    def get_section_by_name(self, name: str) -> Optional[Q88Section]:
        """Retorna uma seção pelo nome"""
        for section in self.sections:
            if section.name.lower() == name.lower():
                return section
        return None
    
    def get_all_fields_needing_review(self) -> List[Q88Field]:
        """Retorna todos os campos que precisam de revisão manual"""
        fields_needing_review = []
        for section in self.sections:
            fields_needing_review.extend(section.get_fields_needing_review())
        return fields_needing_review
    
    def calculate_total_confidence(self) -> float:
        """Calcula o score de confiança geral do formulário"""
        all_scores = []
        for section in self.sections:
            for field in section.fields:
                all_scores.extend(field.confidence_scores)
        
        if not all_scores:
            return 0.0
        
        return sum(all_scores) / len(all_scores)
    
    def get_completion_percentage(self) -> float:
        """Calcula a porcentagem de preenchimento do formulário"""
        if not self.sections:
            return 0.0
        
        total_percentage = sum(section.get_completion_percentage() for section in self.sections)
        return total_percentage / len(self.sections)

# Schemas para requests e responses da API
class Q88FormCreate(BaseModel):
    """Schema para criação de um novo formulário Q88"""
    file_path: str = Field(..., description="Caminho do arquivo para processamento")
    ocr_model_version: Optional[str] = Field(None, description="Versão do modelo OCR a utilizar")

class Q88FormUpdate(BaseModel):
    """Schema para atualização de um formulário Q88"""
    sections: Optional[List[Q88Section]] = None
    processing_status: Optional[str] = None
    total_confidence_score: Optional[float] = None

class Q88FormResponse(BaseModel):
    """Schema para resposta da API com dados do formulário Q88"""
    form_id: str
    sections: List[Q88Section]
    processing_status: str
    created_at: datetime
    updated_at: datetime
    file_path: str
    ocr_model_version: Optional[str]
    total_confidence_score: Optional[float]
    completion_percentage: float
    fields_needing_review: int
    
    class Config:
        from_attributes = True

class Q88ProcessingResult(BaseModel):
    """Schema para resultado do processamento OCR"""
    success: bool
    form_data: Optional[Q88Form] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    confidence_score: Optional[float] = None

class Q88FieldUpdate(BaseModel):
    """Schema para atualização de um campo específico"""
    field_index: int
    section_name: str
    values: List[Union[str, int, float, bool]]
    confidence_scores: Optional[List[float]] = None
    need_confirmation: Optional[bool] = None