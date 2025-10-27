import logging
import time
from typing import Dict, Any
from app.AI.chat_graph.q88_state import Q88State
from app.AI.chat_graph.tools.q88_tools import Q88ExtractionTool

logger = logging.getLogger(__name__)

def q88_ai_node(state: Q88State) -> Q88State:
    """
    Node para processamento com IA dos dados extraídos pelo OCR.
    Usa a lógica atual do AIQ88Processor mas integra com LangGraph.
    
    Args:
        state: Estado atual do processamento Q88
        
    Returns:
        Q88State: Estado atualizado com dados da IA
    """
    try:
        logger.info("🤖 [AI] Iniciando processamento com IA...")
        
        # Verificar se temos dados do OCR
        if not state.get("ocr_text"):
            logger.error("❌ [AI] Nenhum texto OCR disponível")
            state["processing_step"] = "error"
            state["error_message"] = "Nenhum texto OCR disponível para processamento"
            return state
        
        # Atualizar estado
        state["processing_step"] = "ai"
        start_time = time.time()
        
        # Criar tool de extração
        extraction_tool = Q88ExtractionTool()
        
        # Processar com IA
        llm_result = extraction_tool.extract_q88_fields_structured(
            state["ocr_text"], 
            state["ocr_metadata"]
        )
        
        # Armazenar resultado
        state["llm_result"] = llm_result
        
        # Calcular tempo de processamento
        state["llm_processing_time"] = time.time() - start_time
        
        # Calcular scores de confiança
        confidence_scores = []
        if state["llm_result"] and "fields" in state["llm_result"]:
            for field_name, field_data in state["llm_result"]["fields"].items():
                if field_data and isinstance(field_data, dict) and "confidence" in field_data:
                    confidence_scores.append(field_data["confidence"])
        
        state["confidence_scores"] = confidence_scores
        
        # Adicionar mensagem de sucesso
        from langchain_core.messages import SystemMessage
        fields_found = len(state["llm_result"].get("fields", {})) if state["llm_result"] else 0
        state["messages"].append(
            SystemMessage(content=f"✅ IA processou com sucesso: {fields_found} campos identificados")
        )
        
        logger.info(f"✅ [AI] Processamento concluído: {fields_found} campos identificados")
        
        return state
        
    except Exception as e:
        logger.error(f"❌ [AI] Erro inesperado: {str(e)}")
        state["processing_step"] = "error"
        state["error_message"] = f"Erro inesperado na IA: {str(e)}"
        return state
