import logging
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from app.AI.chat_graph.state import State

logger = logging.getLogger(__name__)

class ChartDecision(BaseModel):
    """Define se a pergunta do usuário requer a geração de um gráfico."""
    needs_chart: bool = Field(..., description="True se for necessário gerar um gráfico, False caso contrário")

def determine_chart_needed(state: State, llm_with_tools):
    """
    Decide, via saída estruturada (ChartDecision), se será necessário gerar um gráfico
    para responder à pergunta do usuário.
    """
    # 1. Cria o modelo com saída estruturada
    structured_model = llm_with_tools.with_structured_output(ChartDecision)

    # 2. Monta as instruções
    user_question = state.get("user_question", "")
    instructions = (
        "Você deve responder estritamente com um JSON que obedeça ao esquema ChartDecision:\n"
        "{ \"needs_chart\": <boolean> }\n\n"
        f"Pergunta do usuário: \"{user_question}\""
    )
    prompt_messages = [
        SystemMessage(content=instructions),
        HumanMessage(content="Retorne apenas o JSON com needs_chart.")
    ]

    # 3. Invoca o LLM e recebe o objeto validado
    chart_decision: ChartDecision = structured_model.invoke(prompt_messages)
    logger.info("Decisão de geração de gráfico (estruturada): %s", chart_decision.json())

    # 4. Armazena no state
    state["needs_chart"] = chart_decision.needs_chart
    return state
