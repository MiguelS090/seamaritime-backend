import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.errors import GraphRecursionError
from app.AI.chat_graph.q88_state import Q88State
from app.AI.chat_graph.nodes.q88_ocr_node import q88_ocr_node
from app.AI.chat_graph.nodes.q88_ai_node import q88_ai_node
from app.AI.chat_graph.nodes.q88_validation_node import q88_validation_node

logger = logging.getLogger(__name__)

class Q88ChatGraph:
    """Chat Graph específico para processamento de documentos Q88"""
    
    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations
    
    def workflow(self):
        """Define o fluxo de processamento Q88"""
        graph = StateGraph(Q88State)
        
        # Adicionar nodes
        graph.add_node("ocr_processing", q88_ocr_node)
        graph.add_node("ai_processing", q88_ai_node)
        graph.add_node("validation", q88_validation_node)
        
        # Definir fluxo
        graph.add_edge(START, "ocr_processing")
        graph.add_edge("ocr_processing", "ai_processing")
        graph.add_edge("ai_processing", "validation")
        graph.add_edge("validation", END)
        
        return graph.compile()
    
    def invoke(self, file_path: str, file_name: str, file_type: str, file_size: int = 0):
        """
        Processa um documento Q88 através do fluxo completo.
        
        Args:
            file_path: Caminho para o ficheiro
            file_name: Nome do ficheiro
            file_type: Tipo do ficheiro (PDF, PNG, etc.)
            file_size: Tamanho do ficheiro em bytes
            
        Returns:
            Q88State: Estado final com resultado do processamento
        """
        # Estado inicial
        initial_state = {
            "file_path": file_path,
            "file_name": file_name,
            "file_type": file_type,
            "file_size": file_size,
            "processing_step": "starting",
            "messages": [],
            "confidence_scores": [],
            "ocr_processing_time": 0.0,
            "llm_processing_time": 0.0,
            "total_processing_time": 0.0,
            "processing_method": "ai-powered-extraction"
        }
        
        try:
            logger.info(f"🚀 Iniciando processamento Q88: {file_name}")
            
            # Executar fluxo
            graph = self.workflow()
            result = graph.invoke(initial_state)
            
            logger.info(f"✅ Processamento Q88 concluído: {result['processing_step']}")
            return result
            
        except GraphRecursionError as e:
            logger.error(f"❌ Limite de recursão atingido: {e}")
            initial_state["processing_step"] = "error"
            initial_state["error_message"] = "Limite de recursão atingido no processamento"
            return initial_state
        except Exception as e:
            logger.error(f"❌ Erro inesperado no processamento Q88: {e}")
            initial_state["processing_step"] = "error"
            initial_state["error_message"] = f"Erro inesperado: {str(e)}"
            return initial_state
    
    def get_processing_status(self, state: Q88State) -> Dict[str, Any]:
        """
        Retorna status atual do processamento.
        
        Args:
            state: Estado atual do processamento
            
        Returns:
            Dict com informações de status
        """
        return {
            "processing_step": state.get("processing_step", "unknown"),
            "file_name": state.get("file_name", ""),
            "error_message": state.get("error_message"),
            "ocr_processing_time": state.get("ocr_processing_time", 0),
            "llm_processing_time": state.get("llm_processing_time", 0),
            "total_processing_time": state.get("total_processing_time", 0),
            "confidence_scores": state.get("confidence_scores", []),
            "processing_method": state.get("processing_method", "unknown"),
            "has_ocr_data": bool(state.get("ocr_text")),
            "has_ai_data": bool(state.get("llm_result")),
            "completion_percentage": state.get("llm_result", {}).get("summary", {}).get("completion_percentage", 0) if state.get("llm_result") else 0,
            "total_fields_found": state.get("llm_result", {}).get("summary", {}).get("total_fields_found", 0) if state.get("llm_result") else 0
        }
