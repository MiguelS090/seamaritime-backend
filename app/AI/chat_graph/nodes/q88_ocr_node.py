import logging
import time
from typing import Dict, Any
from app.AI.chat_graph.q88_state import Q88State
from app.services.azure_ocr_service import AzureOCRService

logger = logging.getLogger(__name__)

def q88_ocr_node(state: Q88State) -> Q88State:
    """
    Node para processamento OCR de documentos Q88 usando a lógica atual.
    Mantém a funcionalidade existente mas integra com LangGraph.
    
    Args:
        state: Estado atual do processamento Q88
        
    Returns:
        Q88State: Estado atualizado com dados do OCR
    """
    try:
        logger.info(f"📄 [OCR] Iniciando processamento OCR para: {state['file_path']}")
        
        # Atualizar estado
        state["processing_step"] = "ocr"
        start_time = time.time()
        
        # Usar o serviço OCR atual (que funciona)
        ocr_service = AzureOCRService()
        ocr_result = ocr_service.process_q88_document(state["file_path"])
        
        # Extrair dados do resultado (mantendo estrutura atual)
        state["ocr_text"] = ocr_result.get("fullText", "")
        state["ocr_metadata"] = {
            "organizedLines": ocr_result.get("organizedLines", []),
            "tables": ocr_result.get("tables", []),
            "totalPages": ocr_result.get("totalPages", 0),
            "totalLines": ocr_result.get("totalLines", 0),
            "totalWords": ocr_result.get("totalWords", 0),
            "totalCharacters": ocr_result.get("totalCharacters", 0),
            "averageConfidence": ocr_result.get("averageConfidence", 0.0),
            "documentType": ocr_result.get("documentType", "Q88"),
            "processingTime": ocr_result.get("processingTime", 0),
            # Manter compatibilidade com dados existentes
            "q88Fields": ocr_result.get("q88Fields", {}),
            "paragraphs": ocr_result.get("paragraphs", []),
            "rawData": ocr_result.get("rawData", {})
        }
        
        # Calcular tempo de processamento
        state["ocr_processing_time"] = time.time() - start_time
        
        # Adicionar mensagem de sucesso
        from langchain_core.messages import SystemMessage
        state["messages"].append(
            SystemMessage(content=f"✅ OCR concluído com sucesso: {len(state['ocr_text'])} caracteres extraídos de {state['ocr_metadata']['totalPages']} página(s)")
        )
        
        logger.info(f"✅ [OCR] Processamento concluído: {len(state['ocr_text'])} caracteres, {state['ocr_metadata']['totalPages']} páginas")
        
        return state
        
    except Exception as e:
        logger.error(f"❌ [OCR] Erro inesperado: {str(e)}")
        state["processing_step"] = "error"
        state["error_message"] = f"Erro inesperado no OCR: {str(e)}"
        return state
