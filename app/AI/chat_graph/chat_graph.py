import logging
from langgraph.graph import StateGraph, START, END
from langgraph.errors import GraphRecursionError
from langchain_core.messages import SystemMessage, HumanMessage
from app.AI.chat_graph.state import State
from app.AI.chat_graph.nodes.llm_call import llm_call as llm_call_node
from app.AI.chat_graph.nodes.analyze_need_chart import determine_chart_needed
from app.AI.chat_graph.nodes.tool_node import tool_node as tool_node_node
from app.AI.shared.models.azure_open_ai import get_model
from app.AI.chat_graph.tools.tools import get_tools

logger = logging.getLogger(__name__)

class ChatGraph:
    def __init__(self, max_iterations: int = 5):
        self.erros_consecutivos = 0
        # LLM principal e com tools
        self.llm = get_model(model_name="gpt-4o-mini", temperature=0.3)
        self.tools = get_tools()
        self.tools_by_name = {tool.name: tool for tool in self.tools}
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.max_iterations = max_iterations

    def workflow(self):
        graph = StateGraph(State)

        # 1) Decidir se precisamos de gráfico (true/false)
        graph.add_node("decide_chart", self.determine_chart_needed_wrapper)

        # 2) Fluxo de gráfico: usa llm_call_node (gera SQL + chart)
        graph.add_node("llm_call", self.llm_call_wrapper)

        # 3) Fluxo genérico/DB: responde ou usa DB tools, mas sem gráficos
        graph.add_node("generic_llm", self.generic_llm_call_wrapper)

        # 4) Ambiente: executa chamadas de ferramenta (tanto chart quanto DB)
        graph.add_node("environment", self.tool_node_wrapper)

        # Início
        graph.add_edge(START, "decide_chart")
        # Da decisão, vai para chart ou generic
        graph.add_conditional_edges(
            "decide_chart",
            lambda s: "chart" if s.get("needs_chart") else "generic",
            {"chart": "llm_call", "generic": "generic_llm"},
        )
        # Fluxo de gráfico: após llm_call → environment ou END
        graph.add_conditional_edges(
            "llm_call",
            self.should_continue_wrapper,
            {"Action": "environment", END: END},
        )
        # Ambiente (chart): volta pra llm_call ou END
        graph.add_conditional_edges(
            "environment",
            self.should_end_after_environment,
            {END: END, "Action": "llm_call"},
        )
        # Fluxo genérico: após resposta do generic_llm encerra
        graph.add_edge("generic_llm", END)

        return graph.compile()

    def determine_chart_needed_wrapper(self, state):
        return determine_chart_needed(state, self.llm_with_tools)

    def llm_call_wrapper(self, state):
        # chart flow: SQL + chart instructions
        state["iterations"] = state.get("iterations", 0) + 1
        result = llm_call_node(state, self.llm_with_tools)
        state.setdefault("messages", []).extend(result.get("messages", []))
        return state

    def generic_llm_call_wrapper(self, state):
        # generic flow: sem instruções de gráfico, mas permite DB tools
        instruction = (
            "Você é um assistente geral. Responda à pergunta do usuário.\n"
            "Se precisar acessar o banco de dados, use apenas as ferramentas: "
            "show_tables, get_table_columns ou consult_database;\n"
            "NÃO gere gráficos (ignore generate_chart e generate_generic_heatmap).\n"
        )
        prompt = [
            SystemMessage(content=instruction),
            HumanMessage(content=state.get("user_question", "")),
        ]
        response = self.llm_with_tools.invoke(prompt)
        state.setdefault("messages", []).append(response)
        return state

    def tool_node_wrapper(self, state):
        result = tool_node_node(state, self.tools_by_name)
        state.setdefault("messages", []).extend(result.get("messages", []))
        return state

    def should_continue_wrapper(self, state):
        decision = self.should_continue(state)
        logger.info("Decisão de continuidade: %s", decision)
        return decision

    def should_continue(self, state):
        # limite de iterações
        if state.get("iterations", 0) >= self.max_iterations:
            return END
        msgs = state.get("messages", [])
        if not msgs:
            return "Action"
        last = msgs[-1]
        if self.count_errors_consecutivos(last) > 3:
            return END
        if last.content and last.content.startswith("data:image/png;base64"):
            return END
        return "Action"

    def should_end_after_environment(self, state):
        # no chart flow: encerra se imagem gerada, senão continua
        msgs = state.get("messages", [])
        if not msgs:
            return "Action"
        last = msgs[-1]
        if last.content and last.content.startswith("data:image/png;base64"):
            logger.info("Interrompendo fluxo por imagem em base64.")
            return END
        return "Action"

    def count_errors_consecutivos(self, ultima_mensagem):
        content = ultima_mensagem.content or ""
        if "ProgrammingError" in content or "Unknown column" in content:
            self.erros_consecutivos += 1
        else:
            self.erros_consecutivos = 0
        return self.erros_consecutivos

    def invoke(self, chat_id: str, user_question: str, file: str = None):
        state = {
            "chat_id":       chat_id,
            "user_question": user_question,
            "file":          file,
            "iterations":    0,
            "messages":      []
        }
        graph = self.workflow()
        try:
            return graph.invoke(state)
        except GraphRecursionError as e:
            logger.error("Limite de recursão atingido: %s", e)
            return {
                "messages": [{
                    "sender": "agent",
                    "content": (
                        "O fluxo excedeu o limite de iterações. "
                        "Por favor, refine sua consulta ou tente novamente."
                    )
                }]
            }
