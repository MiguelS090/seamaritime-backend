from langchain_core.messages import AnyMessage
from typing import Annotated, TypedDict, List, Dict, Any, Optional, Union
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime

class FieldType(str, Enum):
    """Tipos de campos Q88"""
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"

class Q88FieldData(BaseModel):
    """Estrutura de um campo individual extraído pela LLM"""
    value: Optional[str] = Field(description="Valor extraído do campo")
    confidence: float = Field(ge=0.0, le=1.0, description="Confiança da extração (0-1)")
    source: str = Field(description="Fonte da extração (linha, seção, etc.)")
    raw_text: Optional[str] = Field(description="Texto original extraído")

class Q88LLMFields(BaseModel):
    """Campos extraídos pela LLM - OTIMIZADO para Business Central Integration"""
    
    # ===== VESSEL INFORMATION (Essencial para BC) =====
    VesselName: Optional[Q88FieldData] = None
    IMONumber: Optional[Q88FieldData] = None
    Flag: Optional[Q88FieldData] = None
    CallSign: Optional[Q88FieldData] = None
    VesselType: Optional[Q88FieldData] = None
    MMSI: Optional[Q88FieldData] = None
    PortOfRegistry: Optional[Q88FieldData] = None
    DateUpdated: Optional[Q88FieldData] = None
    PreviousName: Optional[Q88FieldData] = None
    
    # ===== OWNERSHIP (Crítico para BC) =====
    RegisteredOwner: Optional[Q88FieldData] = None
    TechnicalOperator: Optional[Q88FieldData] = None
    CommercialOperator: Optional[Q88FieldData] = None
    DisponentOwner: Optional[Q88FieldData] = None
    
    # ===== DIMENSIONS & TONNAGES (Relevante para BC) =====
    LOA: Optional[Q88FieldData] = None
    Beam: Optional[Q88FieldData] = None
    GrossTonnage: Optional[Q88FieldData] = None
    NetTonnage: Optional[Q88FieldData] = None
    SummerDWT: Optional[Q88FieldData] = None
    WinterDWT: Optional[Q88FieldData] = None
    TropicalDWT: Optional[Q88FieldData] = None
    
    # ===== CONTACT DETAILS (Melhorado para BC) =====
    ContactDetails: Optional[Q88FieldData] = None
    MasterEmail: Optional[Q88FieldData] = None
    MasterPhone: Optional[Q88FieldData] = None
    InmarsatNumber: Optional[Q88FieldData] = None
    MasterPIC: Optional[Q88FieldData] = None
    
    # ===== CLASSIFICATION (Importante para compliance) =====
    ClassificationSociety: Optional[Q88FieldData] = None
    ClassNotation: Optional[Q88FieldData] = None
    ClassConditions: Optional[Q88FieldData] = None
    LastDryDock: Optional[Q88FieldData] = None
    NextDryDockDue: Optional[Q88FieldData] = None
    NextAnnualSurveyDue: Optional[Q88FieldData] = None
    
    # ===== INSURANCE (Relevante para operações) =====
    PIClub: Optional[Q88FieldData] = None
    HullMachineryInsurer: Optional[Q88FieldData] = None
    HullMachineryValue: Optional[Q88FieldData] = None
    ExpirationDate: Optional[Q88FieldData] = None
    
    # ===== CONSTRUCTION (Informação básica) =====
    Builder: Optional[Q88FieldData] = None
    DateDelivered: Optional[Q88FieldData] = None
    
    # ===== CERTIFICATES ESSENCIAIS (Compliance) =====
    ISM: Optional[Q88FieldData] = None
    DOC: Optional[Q88FieldData] = None
    IOPPC: Optional[Q88FieldData] = None
    ISSC: Optional[Q88FieldData] = None
    MLC: Optional[Q88FieldData] = None
    IAPP: Optional[Q88FieldData] = None
    
    # ===== CREW (Informação operacional) =====
    CrewNationality: Optional[Q88FieldData] = None
    NumberOfOfficers: Optional[Q88FieldData] = None
    NumberOfCrew: Optional[Q88FieldData] = None
    WorkingLanguage: Optional[Q88FieldData] = None
    ManningAgency: Optional[Q88FieldData] = None
    
    # ===== CARGO CAPABILITIES (Relevante para operações) =====
    DoubleHullVessel: Optional[Q88FieldData] = None
    MaxLoadingRate: Optional[Q88FieldData] = None
    CargoRestrictions: Optional[Q88FieldData] = None
    MaxCargoTemp: Optional[Q88FieldData] = None
    
    # ===== PROPULSION (Informação técnica básica) =====
    MainEngineType: Optional[Q88FieldData] = None
    MainEngineHP: Optional[Q88FieldData] = None
    BallastSpeed: Optional[Q88FieldData] = None
    LadenSpeed: Optional[Q88FieldData] = None
    FuelType: Optional[Q88FieldData] = None
    
    # ===== RECENT HISTORY (Operacional) =====
    LastThreeCargoes: Optional[Q88FieldData] = None
    SIREDate: Optional[Q88FieldData] = None
    PortStateDeficiencies: Optional[Q88FieldData] = None
    AdditionalInfo: Optional[Q88FieldData] = None

class Q88LLMSummary(BaseModel):
    """Summary retornado pela LLM - OTIMIZADO para Business Central"""
    total_fields_found: int = Field(description="Total de campos encontrados")
    total_fields_expected: int = Field(default=50, description="Total de campos esperados (otimizado para BC)")
    completion_percentage: float = Field(ge=0.0, le=100.0, description="Percentagem de preenchimento")
    document_type: str = Field(description="Tipo de documento identificado")
    processing_notes: Optional[str] = Field(description="Notas sobre o processamento")
    bc_relevant_fields: int = Field(description="Campos relevantes para Business Central")
    extraction_quality: str = Field(description="Qualidade da extração: excellent/good/fair/poor")

class Q88LLMResult(BaseModel):
    """Resultado completo da LLM - estrutura exata do JSON"""
    fields: Q88LLMFields = Field(description="Campos extraídos")
    summary: Q88LLMSummary = Field(description="Resumo do processamento")

class Q88State(TypedDict):
    """State para processamento Q88 - desenhado para a estrutura JSON da LLM"""
    
    # Dados de entrada
    file_path: str
    file_name: str
    file_type: str
    file_size: int
    
    # Dados de processamento OCR
    ocr_text: str
    ocr_metadata: Dict[str, Any]  # páginas, linhas, tabelas, etc.
    ocr_processing_time: float
    
    # Resultado da LLM (estrutura exata do JSON)
    llm_result: Optional[Q88LLMResult]
    llm_processing_time: float
    
    # Estado do processamento
    processing_step: str  # "ocr", "llm", "validation", "completed", "error"
    error_message: Optional[str]
    
    # Metadados
    total_processing_time: float
    confidence_scores: List[float]
    
    # Messages para o LangGraph
    messages: Annotated[List[AnyMessage], add_messages]
    
    # Dados de contexto (opcional)
    examples_used: Optional[List[Dict[str, Any]]]
    processing_method: str  # "ai-powered-extraction", "fallback-to-raw-text"



