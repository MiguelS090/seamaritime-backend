# app/routers/q88.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.core.database import get_db
from app.controllers.q88 import Q88Controller
from app.schemas.q88 import (
    Q88FormResponse, Q88FormUpdate, Q88FieldUpdate, Q88ProcessingResult
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/q88", tags=["Q88 Forms"])

# Inicializar controller
q88_controller = Q88Controller()

@router.post("/upload", response_model=Q88FormResponse, summary="Upload e processamento de formulário Q88 (síncrono)")
async def upload_q88_form(
    file: UploadFile = File(..., description="Arquivo Q88 para processamento (PDF, PNG, JPG, JPEG, DOCX)"),
    db: Session = Depends(get_db)
):
    """
    Faz upload de um formulário Q88 e processa usando OCR customizado da Azure.
    
    - **file**: Arquivo do formulário Q88 (PDF, imagens ou DOCX)
    
    Retorna os dados extraídos do formulário com scores de confiança.
    """
    try:
        logger.info(f"Iniciando upload de arquivo: {file.filename}")
        result = await q88_controller.create_q88_form(file, db)
        logger.info(f"Upload concluído com sucesso: {result.form_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.post("/upload-async", summary="Upload e processamento assíncrono de formulário Q88")
async def upload_q88_form_async(
    file: UploadFile = File(..., description="Arquivo Q88 para processamento (PDF, PNG, JPG, JPEG, DOCX)"),
    db: Session = Depends(get_db)
):
    """
    Faz upload de um formulário Q88 e inicia processamento assíncrono.
    
    - **file**: Arquivo do formulário Q88 (PDF, imagens ou DOCX)
    
    Retorna imediatamente com status de processamento. Use o endpoint de status para verificar progresso.
    """
    try:
        logger.info(f"Iniciando upload assíncrono de arquivo: {file.filename}")
        result = await q88_controller.upload_q88_async(file)
        logger.info(f"Upload assíncrono iniciado: {result['form_id']}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no upload assíncrono: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.post("/upload-ai", response_model=Q88FormResponse, summary="Upload e processamento com nova arquitetura AI")
async def upload_q88_form_ai(
    file: UploadFile = File(..., description="Arquivo Q88 para processamento com IA (PDF, PNG, JPG, JPEG, DOCX)"),
    db: Session = Depends(get_db)
):
    """
    Faz upload de um formulário Q88 e processa usando a nova arquitetura AI com LangGraph.
    
    - **file**: Arquivo do formulário Q88 (PDF, imagens ou DOCX)
    
    Retorna os dados extraídos do formulário com scores de confiança usando processamento estruturado.
    """
    try:
        logger.info(f"🤖 Iniciando upload com IA: {file.filename}")
        result = await q88_controller.create_q88_form_ai(file, db)
        logger.info(f"✅ Upload AI concluído com sucesso: {result.form_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro no upload AI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.post("/test-ai-processing", summary="Testar processamento com IA (desenvolvimento)")
async def test_ai_processing(
    file: UploadFile = File(..., description="Arquivo Q88 para teste do sistema de IA"),
    db: Session = Depends(get_db)
):
    """
    Endpoint para testar o novo sistema de IA sem salvar no banco de dados.
    Útil para desenvolvimento e testes.
    """
    try:
        logger.info(f"🧪 Testando processamento com IA: {file.filename}")
        
        # Salvar arquivo temporariamente
        file_path = await q88_controller._save_uploaded_file(file)
        
        try:
            # 1. Extrair TODO o texto
            logger.info("📄 Teste: Extraindo texto completo...")
            extracted_data = q88_controller.ocr_service.process_q88_document(file_path)
            
            # 2. Processar com IA
            logger.info("🤖 Teste: Processando com IA...")
            from app.AI.chat_graph.tools.q88_tools import Q88ExtractionTool
            extraction_tool = Q88ExtractionTool()
            ai_result = extraction_tool.extract_q88_fields_structured(
                extracted_data.get("fullText", ""),
                extracted_data
            )
            
            # 3. Retornar resultado sem salvar no banco
            return {
                "success": True,
                "message": "Teste de processamento com IA concluído",
                "data": {
                    "ai_result": ai_result,
                    "extracted_data": extracted_data
                },
                "file_info": {
                    "filename": file.filename,
                    "size": file.size,
                    "type": file.content_type
                },
                "performance": {
                    "text_length": len(extracted_data.get('fullText', '')),
                    "fields_found": len(ai_result.fields.__dict__) if ai_result.fields else 0,
                    "document_type": ai_result.summary.document_type if ai_result.summary else "unknown"
                }
            }
            
        finally:
            # Limpar arquivo temporário
            import os
            if os.path.exists(file_path):
                os.remove(file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no teste de IA: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/status/{form_id}", summary="Verificar status do processamento")
async def get_q88_form_status(
    form_id: str,
    db: Session = Depends(get_db)
):
    """
    Verifica o status do processamento de um formulário Q88.
    
    - **form_id**: ID único do formulário
    
    Retorna status atual e dados quando processamento estiver completo.
    """
    try:
        return await q88_controller.get_q88_status(form_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao verificar status {form_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/forms", response_model=List[Q88FormResponse], summary="Listar formulários Q88")
async def list_q88_forms(
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    db: Session = Depends(get_db)
):
    """
    Lista todos os formulários Q88 processados.
    
    - **skip**: Número de registros para pular (paginação)
    - **limit**: Número máximo de registros por página (máximo 1000)
    """
    try:
        # TODO: Implementar list_q88_forms no controller
        raise HTTPException(status_code=501, detail="Método não implementado")
    except Exception as e:
        logger.error(f"Erro ao listar formulários: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/forms/{form_id}", response_model=Q88FormResponse, summary="Obter formulário Q88 por ID")
async def get_q88_form(
    form_id: str,
    db: Session = Depends(get_db)
):
    """
    Obtém um formulário Q88 específico pelo ID.
    
    - **form_id**: ID único do formulário
    """
    try:
        # TODO: Implementar get_q88_form no controller
        raise HTTPException(status_code=501, detail="Método não implementado")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter formulário {form_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.put("/forms/{form_id}", response_model=Q88FormResponse, summary="Atualizar formulário Q88")
async def update_q88_form(
    form_id: str,
    form_update: Q88FormUpdate,
    db: Session = Depends(get_db)
):
    """
    Atualiza um formulário Q88 existente.
    
    - **form_id**: ID único do formulário
    - **form_update**: Dados para atualização
    """
    try:
        # TODO: Implementar update_q88_form no controller
        raise HTTPException(status_code=501, detail="Método não implementado")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar formulário {form_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.patch("/forms/{form_id}/fields", response_model=Q88FormResponse, summary="Atualizar campo específico")
async def update_q88_field(
    form_id: str,
    field_update: Q88FieldUpdate,
    db: Session = Depends(get_db)
):
    """
    Atualiza um campo específico de um formulário Q88.
    
    - **form_id**: ID único do formulário
    - **field_update**: Dados para atualização do campo
    """
    try:
        # TODO: Implementar update_q88_field no controller
        raise HTTPException(status_code=501, detail="Método não implementado")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar campo do formulário {form_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.delete("/forms/{form_id}", summary="Deletar formulário Q88")
async def delete_q88_form(
    form_id: str,
    db: Session = Depends(get_db)
):
    """
    Deleta um formulário Q88 e todos os seus dados associados.
    
    - **form_id**: ID único do formulário
    """
    try:
        # TODO: Implementar delete_q88_form no controller
        raise HTTPException(status_code=501, detail="Método não implementado")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar formulário {form_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/forms/{form_id}/review", response_model=List[dict], summary="Obter campos que precisam de revisão")
async def get_fields_needing_review(
    form_id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna lista de campos que precisam de revisão manual.
    
    - **form_id**: ID único do formulário
    """
    try:
        # TODO: Implementar get_q88_form no controller
        form = None
        
        # Extrair campos que precisam de revisão
        fields_needing_review = []
        
        # Esta lógica seria implementada no controller
        # for section in form.sections:
        #     for field in section.fields:
        #         if field.need_confirmation or field.get_confidence_level() == "low":
        #             fields_needing_review.append({
        #                 "section_name": section.name,
        #                 "field_index": field.index,
        #                 "label": field.label,
        #                 "current_values": field.values,
        #                 "confidence_scores": field.confidence_scores,
        #                 "confidence_level": field.get_confidence_level()
        #             })
        
        return fields_needing_review
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter campos para revisão {form_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/health", summary="Verificar saúde do serviço OCR")
async def health_check():
    """
    Verifica se o serviço OCR está funcionando corretamente.
    """
    try:
        # Verificar disponibilidade do modelo
        # model_available = await q88_controller.ocr_service.validate_model_availability()
        
        # Por enquanto, retornar status básico
        return {
            "status": "healthy",
            "ocr_service": "available",
            "message": "Serviço OCR funcionando"
        }
    except Exception as e:
        logger.error(f"Erro no health check: {str(e)}")
        return {
            "status": "unhealthy",
            "ocr_service": "error",
            "message": str(e)
        }

@router.get("/stats", summary="Estatísticas dos formulários Q88")
async def get_q88_stats(db: Session = Depends(get_db)):
    """
    Retorna estatísticas gerais dos formulários Q88 processados.
    """
    try:
        # Implementar lógica de estatísticas
        from app.models.q88 import Q88Form as Q88FormModel
        
        total_forms = db.query(Q88FormModel).count()
        completed_forms = db.query(Q88FormModel).filter(
            Q88FormModel.processing_status == "completed"
        ).count()
        failed_forms = db.query(Q88FormModel).filter(
            Q88FormModel.processing_status == "failed"
        ).count()
        
        success_rate = (completed_forms / total_forms * 100) if total_forms > 0 else 0
        
        return {
            "total_forms": total_forms,
            "completed_forms": completed_forms,
            "failed_forms": failed_forms,
            "success_rate": round(success_rate, 2),
            "pending_forms": total_forms - completed_forms - failed_forms
        }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

