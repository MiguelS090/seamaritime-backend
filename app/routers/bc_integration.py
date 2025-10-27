"""
Router para integração com Business Central
Permite upload de documentos Q88 e retorna dados estruturados para criação de Shipments
"""

import logging
import tempfile
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.controllers.q88 import Q88Controller
from app.AI.chat_graph.tools.q88_tools import Q88ExtractionTool
from app.services.azure_ocr_service import AzureOCRService
from app.AI.chat_graph.q88_state import Q88LLMResult
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bc-integration", tags=["Business Central Integration"])

class BCIntegrationService:
    """Serviço para integração com Business Central"""
    
    def __init__(self):
        self.ocr_service = AzureOCRService()
        self.extraction_tool = Q88ExtractionTool()
    
    async def process_document_for_bc(self, file: UploadFile) -> Dict[str, Any]:
        """
        Processa documento Q88 para integração com Business Central
        
        Args:
            file: Arquivo Q88 enviado pelo BC
            
        Returns:
            Dict com dados estruturados para criação de Shipment
        """
        try:
            logger.info(f"📄 [BC Integration] Processando documento: {file.filename}")
            
            # 1. Salvar arquivo temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # 2. Processar OCR
                logger.info("🔍 [BC Integration] Iniciando OCR...")
                ocr_result = self.ocr_service.process_q88_document(temp_file_path)
                
                # 3. Extrair campos com IA
                logger.info("🤖 [BC Integration] Iniciando extração IA...")
                ocr_text = ocr_result.get("fullText", "")
                
                # 4. Usar ferramenta de extração estruturada
                llm_result = self.extraction_tool.extract_q88_fields_structured(
                    ocr_text, ocr_result
                )
                
                # 5. Converter para formato BC
                bc_data = self._convert_to_bc_format(llm_result, ocr_result)
                
                logger.info(f"✅ [BC Integration] Documento processado com sucesso: {file.filename}")
                return bc_data
                
            finally:
                # Limpar arquivo temporário
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"❌ [BC Integration] Erro ao processar documento: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Erro ao processar documento: {str(e)}")
    
    def _convert_to_bc_format(self, llm_result: Q88LLMResult, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converte resultado da IA para formato compatível com Business Central
        
        Args:
            llm_result: Resultado estruturado da IA
            ocr_result: Resultado do OCR
            
        Returns:
            Dict formatado para BC
        """
        try:
            # Extrair campos principais
            fields = llm_result.fields
            summary = llm_result.summary
            
            # Mapear campos para estrutura BC
            bc_shipment_data = {
                "vessel_information": {
                    "vessel_name": self._extract_field_value(fields.VesselName),
                    "imo_number": self._extract_field_value(fields.IMONumber),
                    "flag": self._extract_field_value(fields.Flag),
                    "call_sign": self._extract_field_value(fields.CallSign),
                    "vessel_type": self._extract_field_value(fields.VesselType),
                    "mmsi": self._extract_field_value(fields.MMSI),
                    "port_of_registry": self._extract_field_value(fields.PortOfRegistry),
                    "date_updated": self._extract_field_value(fields.DateUpdated),
                    "previous_name": self._extract_field_value(fields.PreviousName)
                },
                "ownership": {
                    "registered_owner": self._extract_field_value(fields.RegisteredOwner),
                    "technical_operator": self._extract_field_value(fields.TechnicalOperator),
                    "commercial_operator": self._extract_field_value(fields.CommercialOperator),
                    "disponent_owner": self._extract_field_value(fields.DisponentOwner)
                },
                "dimensions": {
                    "loa": self._extract_field_value(fields.LOA),
                    "beam": self._extract_field_value(fields.Beam),
                    "gross_tonnage": self._extract_field_value(fields.GrossTonnage),
                    "net_tonnage": self._extract_field_value(fields.NetTonnage),
                    "summer_dwt": self._extract_field_value(fields.SummerDWT),
                    "winter_dwt": self._extract_field_value(fields.WinterDWT),
                    "tropical_dwt": self._extract_field_value(fields.TropicalDWT)
                },
                "contact_details": {
                    "contact_details": self._extract_field_value(fields.ContactDetails),
                    "master_email": self._extract_field_value(fields.MasterEmail),
                    "master_phone": self._extract_field_value(fields.MasterPhone),
                    "inmarsat_number": self._extract_field_value(fields.InmarsatNumber),
                    "master_pic": self._extract_field_value(fields.MasterPIC)
                },
                "classification": {
                    "classification_society": self._extract_field_value(fields.ClassificationSociety),
                    "class_notation": self._extract_field_value(fields.ClassNotation),
                    "class_conditions": self._extract_field_value(fields.ClassConditions),
                    "last_dry_dock": self._extract_field_value(fields.LastDryDock),
                    "next_dry_dock_due": self._extract_field_value(fields.NextDryDockDue),
                    "next_annual_survey_due": self._extract_field_value(fields.NextAnnualSurveyDue)
                },
                "insurance": {
                    "pi_club": self._extract_field_value(fields.PIClub),
                    "hull_machinery_insurer": self._extract_field_value(fields.HullMachineryInsurer),
                    "hull_machinery_value": self._extract_field_value(fields.HullMachineryValue),
                    "expiration_date": self._extract_field_value(fields.ExpirationDate)
                },
                "construction": {
                    "builder": self._extract_field_value(fields.Builder),
                    "date_delivered": self._extract_field_value(fields.DateDelivered)
                },
                "certificates": {
                    "ism": self._extract_field_value(fields.ISM),
                    "doc": self._extract_field_value(fields.DOC),
                    "ioppc": self._extract_field_value(fields.IOPPC),
                    "issc": self._extract_field_value(fields.ISSC),
                    "mlc": self._extract_field_value(fields.MLC),
                    "iapp": self._extract_field_value(fields.IAPP)
                },
                "crew": {
                    "crew_nationality": self._extract_field_value(fields.CrewNationality),
                    "number_of_officers": self._extract_field_value(fields.NumberOfOfficers),
                    "number_of_crew": self._extract_field_value(fields.NumberOfCrew),
                    "working_language": self._extract_field_value(fields.WorkingLanguage),
                    "manning_agency": self._extract_field_value(fields.ManningAgency)
                },
                "cargo_capabilities": {
                    "double_hull_vessel": self._extract_field_value(fields.DoubleHullVessel),
                    "max_loading_rate": self._extract_field_value(fields.MaxLoadingRate),
                    "cargo_restrictions": self._extract_field_value(fields.CargoRestrictions),
                    "max_cargo_temp": self._extract_field_value(fields.MaxCargoTemp)
                },
                "propulsion": {
                    "main_engine_type": self._extract_field_value(fields.MainEngineType),
                    "main_engine_hp": self._extract_field_value(fields.MainEngineHP),
                    "ballast_speed": self._extract_field_value(fields.BallastSpeed),
                    "laden_speed": self._extract_field_value(fields.LadenSpeed),
                    "fuel_type": self._extract_field_value(fields.FuelType)
                },
                "recent_history": {
                    "last_three_cargoes": self._extract_field_value(fields.LastThreeCargoes),
                    "sire_date": self._extract_field_value(fields.SIREDate),
                    "port_state_deficiencies": self._extract_field_value(fields.PortStateDeficiencies),
                    "additional_info": self._extract_field_value(fields.AdditionalInfo)
                }
            }
            
            # Adicionar metadados
            bc_shipment_data["metadata"] = {
                "processing_summary": {
                    "total_fields_found": summary.total_fields_found,
                    "completion_percentage": summary.completion_percentage,
                    "document_type": summary.document_type,
                    "extraction_quality": summary.extraction_quality,
                    "bc_relevant_fields": summary.bc_relevant_fields
                },
                "ocr_metadata": {
                    "total_pages": ocr_result.get("totalPages", 0),
                    "total_lines": ocr_result.get("totalLines", 0),
                    "total_words": ocr_result.get("totalWords", 0),
                    "document_type": ocr_result.get("documentType", "Unknown"),
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S')
                }
            }
            
            return bc_shipment_data
            
        except Exception as e:
            logger.error(f"❌ [BC Integration] Erro ao converter para formato BC: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Erro ao converter dados: {str(e)}")
    
    def _extract_field_value(self, field_data) -> Dict[str, Any]:
        """Extrai valor de um campo Q88FieldData"""
        if field_data is None:
            return {"value": None, "confidence": 0.0, "source": "not_found"}
        
        return {
            "value": field_data.value,
            "confidence": field_data.confidence,
            "source": field_data.source,
            "raw_text": field_data.raw_text
        }

# Instância do serviço
bc_service = BCIntegrationService()

@router.post("/upload-document")
async def upload_document_for_bc(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint para upload de documentos Q88 para integração com Business Central
    
    Args:
        file: Arquivo Q88 (PDF, DOCX, etc.)
        db: Sessão do banco de dados
        current_user: Usuário autenticado via Azure AD (opcional em modo dev)
        
    Returns:
        JSON com dados estruturados para criação de Shipment no BC
    """
    try:
        # Modo desenvolvimento - sem autenticação
        logger.warning(f"⚠️ [BC Integration] Upload SEM autenticação (modo dev/BC)")
        
        logger.info(f"📥 [BC Integration] Recebendo upload de: {file.filename}")
        logger.info(f"📋 [BC Integration] Content-Type: {file.content_type}")
        
        # Validar tipo de arquivo
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nome do arquivo não fornecido")
        
        allowed_extensions = ['.pdf', '.docx', '.doc', '.png', '.jpg', '.jpeg']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Tipo de arquivo não suportado. Tipos permitidos: {', '.join(allowed_extensions)}"
            )
        
        # Processar documento
        logger.info(f"🔄 [BC Integration] Iniciando processamento de: {file.filename}")
        result = await bc_service.process_document_for_bc(file)
        
        logger.info(f"✅ [BC Integration] Processamento concluído com sucesso")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Documento processado com sucesso",
                "data": result,
                "filename": file.filename
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [BC Integration] Erro no endpoint upload: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check para o serviço de integração BC"""
    return {
        "status": "healthy",
        "service": "Business Central Integration",
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S')
    }

@router.get("/supported-formats")
async def get_supported_formats():
    """Retorna formatos de arquivo suportados"""
    return {
        "supported_formats": ['.pdf', '.docx', '.doc', '.png', '.jpg', '.jpeg'],
        "max_file_size": "50MB",
        "description": "Formatos suportados para documentos Q88"
    }
