import logging
from langchain_core.messages import SystemMessage, HumanMessage
from app.AI.shared.memory.k_messages import get_k_messages_formatted
from app.AI.chat_graph.state import State

logger = logging.getLogger(__name__)

def llm_call(state: State, llm_with_tools):
    """
    Constrói o prompt para o LLM com instruções detalhadas para:
      - Garantir consultas seguras ao BD.
      - Gerar a consulta SQL apropriada para o gráfico solicitado.
      - Mapear corretamente as colunas retornadas para o gráfico.
      - E, caso a resposta seja um relatório (ou seja, uma análise textual dos dados),
        incluir a flag [REPORT_FLAG] no início da resposta.
    
    Utilize uma abordagem de Chain-of-Thought para decompor a tarefa em etapas:
      1. Identificar as colunas disponíveis.
      2. Gerar a consulta SQL.
      3. Configurar o gráfico com base no mapeamento.
    
    **Instruções específicas para gráficos:**
    - **Gráfico de Pizza:**  
      Gere uma consulta SQL que retorne pelo menos uma coluna categórica e uma numérica.  
      A coluna numérica determinará o tamanho de cada fatia, enquanto a categórica servirá como rótulo.  
      Se necessário, calcule a porcentagem de cada categoria em relação ao total.
    
    - **Gráficos de Barras e Linhas:**  
      Se houver uma coluna categórica e uma ou mais numéricas, utilize a coluna categórica para o eixo X  
      e as numéricas para os valores do eixo Y. Caso não haja uma coluna categórica, utilize o índice dos dados.  
      Se houver mais de 5 categorias, rotacione os rótulos do eixo X para melhor visualização.
    
    - **Gráfico de Dispersão (Scatter):**  
      Requer pelo menos duas colunas numéricas.  
      Utilize a primeira coluna numérica para o eixo X e a segunda para o eixo Y.  
      Se uma terceira coluna numérica estiver disponível, ela pode ser usada para definir a cor dos pontos,  
      possibilitando uma análise mais detalhada.
    
    - **Mapa de Calor (Heatmap):**  
      Necessita de pelo menos duas colunas categóricas e uma numérica.  
      A primeira coluna será utilizada como índice (linhas) e a segunda como colunas,  
      enquanto a coluna numérica representará os valores agregados (por padrão, utilizando a soma).
    
    **Relatórios:**  
    Se o usuário solicitar um relatório, elabore um texto claro e detalhado, iniciando a resposta com [REPORT_FLAG]  
    e utilizando marcação HTML estruturada com as tags <h1>, <h2>, <p>, <table>, <tr>, <th> e <td> para organizar as informações.
    
    Utilize uma abordagem passo a passo (Chain-of-Thought) para decompor a tarefa e garantir precisão na resposta.
    """
    # Recupera o histórico da conversa
    conversation_history = "\n".join(message.content for message in get_k_messages_formatted(state['chat_id'], 5))
    file_info = "" if state.get("file") is None else "\n📂 Arquivo enviado: " + state["file"]
    
    # Monta as instruções detalhadas
    instructions = (
        "Você é um assistente especializado em análise de dados, geração de gráficos e elaboração de relatórios. "
        "Seu objetivo é responder de forma precisa e segura, estruturando consultas SQL apenas para leitura, "
        "gerando gráficos quando necessário e, quando solicitado, produzindo relatórios analíticos a partir dos dados, responder a anexos (arquivos) quando houver.\n\n"
        "⚠️ **REGRAS PARA CONSULTAS E GERAÇÃO DE GRÁFICOS:**\n"
        "1. Antes de consultar qualquer tabela, chame `show_tables` para listar as tabelas disponíveis.\n"
        "2. Ao acessar uma tabela, chame `get_table_columns` para obter sua estrutura.\n"
        "3. Use `consult_database` para executar consultas somente de leitura.\n"
        "4. Para gerar gráficos, utilize `generate_chart` com os parâmetros adequados.\n\n"
        "**Instruções específicas para gráficos:**\n"
        "- **Gráfico de Pizza:** Gere uma consulta SQL que retorne pelo menos uma coluna categórica e uma numérica. "
            "A coluna numérica determinará o tamanho de cada fatia, enquanto a categórica servirá como rótulo. "
            "Se necessário, calcule a porcentagem de cada categoria em relação ao total.\n"
        "- **Gráficos de Barras e Linhas:** Se houver uma coluna categórica e uma ou mais numéricas, utilize a coluna "
            "categórica para o eixo X e as numéricas para os valores do eixo Y. Caso não haja uma coluna categórica, utilize o índice. "
            "Se o número de categorias for superior a 5, rotacione os rótulos do eixo X para melhor visualização.\n"
        "- **Gráfico de Dispersão (Scatter):** Requer pelo menos duas colunas numéricas. Use a primeira coluna para o eixo X e a segunda para o eixo Y. "
            "Se houver uma terceira coluna, ela pode definir a cor dos pontos.\n"
        "- **Mapa de Calor (Heatmap):** Necessita de pelo menos duas colunas categóricas e uma numérica. "
            "A primeira coluna será usada como índice (linhas), a segunda como colunas e a numérica para os valores agregados (soma por padrão).\n\n"
        "**Relatórios:** Se o usuário solicitar um relatório, elabore um texto claro e detalhado iniciando com [REPORT_FLAG] e "
        "utilize HTML estruturado (<h1>, <h2>, <p>, <table>, <tr>, <th>, <td>) para formatar a resposta.\n\n"
        "Utilize uma abordagem passo a passo (Chain-of-Thought) para decompor a tarefa e garantir a precisão na resposta.\n\n"
        "📜 **Histórico da conversa:**\n" + conversation_history + "\n 📜 **Arquivo do usuário anexado (Pode ser vazio):**\n"  + file_info
    )
    
    # Cria as mensagens para o prompt
    prompt_messages = [
        SystemMessage(content=instructions),
        HumanMessage(content="🗣️ Pergunta do usuário: " + state["user_question"])
    ] + state.get("messages", [])
    
    # Invoca o LLM com o prompt montado
    resposta = llm_with_tools.invoke(prompt_messages)
    logger.info("Resposta do LLM: %s", resposta)
    return {"messages": [resposta]}
