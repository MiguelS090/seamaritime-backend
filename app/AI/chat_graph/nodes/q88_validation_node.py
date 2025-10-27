import logging
import time
from typing import Dict, Any
from app.AI.chat_graph.q88_state import Q88State

logger = logging.getLogger(__name__)

def q88_validation_node(state: Q88State) -> Q88State:
    """
    Node para validação dos dados extraídos do documento Q88.
    Verifica qualidade, completude e consistência dos dados.
    
    Args:
        state: Estado atual do processamento Q88
        
    Returns:
        Q88State: Estado atualizado com resultado da validação
    """
    try:
        logger.info("🔍 [VALIDATION] Iniciando validação dos dados...")
        
        # Verificar se temos resultado da IA
        if not state.get("llm_result"):
            logger.error("❌ [VALIDATION] Nenhum resultado da IA disponível")
            state["processing_step"] = "error"
            state["error_message"] = "Nenhum resultado da IA disponível para validação"
            return state
        
        # Atualizar estado
        state["processing_step"] = "validation"
        start_time = time.time()
        
        # Extrair dados para validação
        llm_result = state["llm_result"]
        fields = llm_result.get("fields", {})
        summary = llm_result.get("summary", {})
        
        # Métricas de validação
        validation_results = {
            "total_fields": len(fields),
            "fields_with_values": 0,
            "fields_with_high_confidence": 0,
            "fields_with_low_confidence": 0,
            "average_confidence": 0.0,
            "completion_percentage": summary.get("completion_percentage", 0),
            "validation_warnings": [],
            "validation_errors": [],
            "is_valid": True
        }
        
        # Validar cada campo
        confidence_sum = 0.0
        confidence_count = 0
        
        for field_name, field_data in fields.items():
            if field_data and isinstance(field_data, dict):
                # Verificar se tem valor
                value = field_data.get("value")
                confidence = field_data.get("confidence", 0.0)
                
                if value is not None and str(value).strip():
                    validation_results["fields_with_values"] += 1
                    
                    # Contar confiança
                    if confidence > 0:
                        confidence_sum += confidence
                        confidence_count += 1
                        
                        if confidence >= 0.7:
                            validation_results["fields_with_high_confidence"] += 1
                        elif confidence < 0.5:
                            validation_results["fields_with_low_confidence"] += 1
                            validation_results["validation_warnings"].append(
                                f"Campo '{field_name}' tem confiança baixa ({confidence:.2f})"
                            )
        
        # Calcular média de confiança
        if confidence_count > 0:
            validation_results["average_confidence"] = confidence_sum / confidence_count
        
        # Verificar completude mínima
        if validation_results["completion_percentage"] < 20:
            validation_results["validation_errors"].append(
                f"Completude muito baixa: {validation_results['completion_percentage']}%"
            )
            validation_results["is_valid"] = False
        
        # Verificar se há campos com valores
        if validation_results["fields_with_values"] == 0:
            validation_results["validation_errors"].append(
                "Nenhum campo com valor foi encontrado"
            )
            validation_results["is_valid"] = False
        
        # Armazenar resultado da validação
        state["validation_result"] = validation_results
        
        # Calcular tempo total de processamento
        validation_time = time.time() - start_time
        state["total_processing_time"] = (
            state.get("ocr_processing_time", 0) + 
            state.get("llm_processing_time", 0) + 
            validation_time
        )
        
        # Adicionar mensagem de resultado
        from langchain_core.messages import SystemMessage
        
        if validation_results["is_valid"]:
            state["processing_step"] = "completed"
            message = (
                f"✅ Validação concluída com sucesso: "
                f"{validation_results['fields_with_values']}/{validation_results['total_fields']} campos válidos, "
                f"confiança média: {validation_results['average_confidence']:.2%}, "
                f"completude: {validation_results['completion_percentage']}%"
            )
            state["messages"].append(SystemMessage(content=message))
            logger.info(f"✅ [VALIDATION] {message}")
        else:
            state["processing_step"] = "completed_with_warnings"
            errors = "; ".join(validation_results["validation_errors"])
            message = f"⚠️ Validação concluída com problemas: {errors}"
            state["messages"].append(SystemMessage(content=message))
            logger.warning(f"⚠️ [VALIDATION] {message}")
        
        # Adicionar warnings se houver
        if validation_results["validation_warnings"]:
            warnings = "; ".join(validation_results["validation_warnings"][:3])  # Limitar a 3
            state["messages"].append(SystemMessage(content=f"⚠️ Avisos: {warnings}"))
        
        return state
        
    except Exception as e:
        logger.error(f"❌ [VALIDATION] Erro inesperado: {str(e)}")
        state["processing_step"] = "error"
        state["error_message"] = f"Erro inesperado na validação: {str(e)}"
        return state
















