import logging
from langchain_core.messages import ToolMessage
from app.AI.chat_graph.state import State

logger = logging.getLogger(__name__)

def tool_node(state: State, tools_by_name):
    """
    Executa as chamadas de ferramentas solicitadas pelo LLM.
    Itera sobre os pedidos (tool_calls) contidos na última mensagem e invoca a ferramenta correspondente.
    """
    resultados = []
    try:
        last_msg_tool_calls = state["messages"][-1].tool_calls
    except (IndexError, KeyError, AttributeError) as e:
        logger.error("Erro ao acessar tool_calls: %s", e)
        return {"messages": []}
    
    for tool_call in last_msg_tool_calls:
        logger.info("Chamando ferramenta: %s com args: %s", tool_call["name"], tool_call["args"])
        tool = tools_by_name.get(tool_call["name"])
        if not tool:
            logger.error("Ferramenta '%s' não encontrada!", tool_call["name"])
            continue
        
        observacao = tool.invoke(tool_call["args"])
        if isinstance(observacao, dict):
            if "image" in observacao:
                message_content = observacao["image"]
            elif "error" in observacao:
                message_content = f"Erro ao gerar gráfico: {observacao['error']}"
            else:
                message_content = str(observacao)
        else:
            message_content = str(observacao)
        resultados.append(ToolMessage(content=message_content, tool_call_id=tool_call["id"]))
    
    logger.info("Enviando resposta final para o frontend")
    return {"messages": resultados}
