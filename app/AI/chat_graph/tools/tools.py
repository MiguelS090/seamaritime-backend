import logging
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import text
from langchain.tools import tool
import io
import base64
from app.core.database import get_read_only_db as get_db
import seaborn as sns

# Configuração do logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def classify_columns(df):
    """
    Classifica as colunas de um DataFrame em numéricas (medidas) e categóricas (dimensões).
    Heurística: se a coluna puder ser convertida para numérico com poucos NaNs (≥ 80% valores válidos),
    ela é considerada numérica; caso contrário, é categórica.
    """
    numeric_cols = []
    cat_cols = []
    for col in df.columns:
        try:
            converted = pd.to_numeric(df[col], errors='coerce')
            not_na_ratio = 1 - (converted.isna().sum() / len(converted))
            if not_na_ratio >= 0.8:
                numeric_cols.append(col)
            else:
                cat_cols.append(col)
        except Exception:
            cat_cols.append(col)
    return numeric_cols, cat_cols

@tool
def consult_database(query: str) -> str:
    """Consulta o banco de dados, apenas leitura."""
    db = next(get_db())
    try:
        forbidden = ["DELETE", "ALTER", "CREATE", "DROP", "UPDATE", "INSERT", "TRUNCATE", "REPLACE"]
        if any(cmd in query.upper() for cmd in forbidden):
            return "❌ Apenas consultas de leitura são permitidas."
        result = db.execute(text(query))
        if result.returns_rows:
            return "\n".join(str(row) for row in result.fetchall())
        else:
            return f"ℹ️ Linhas afetadas: {result.rowcount}"
    except Exception as e:
        logger.error("Erro ao executar consulta: %s", e)
        return f"⚠️ Erro ao executar consulta: {str(e)}"
    finally:
        db.close()

@tool
def show_tables() -> str:
    """Lista as tabelas do BD."""
    db = next(get_db())
    try:
        result = db.execute(text("SHOW TABLES;"))
        if result.returns_rows:
            return "\n".join(row[0] for row in result.fetchall())
        return "ℹ️ Nenhuma tabela encontrada."
    except Exception as e:
        logger.error("Erro ao buscar tabelas: %s", e)
        return f"⚠️ Erro ao buscar tabelas: {str(e)}"
    finally:
        db.close()

@tool
def get_table_columns(table_name: str) -> str:
    """Retorna as colunas de uma tabela."""
    db = next(get_db())
    try:
        result = db.execute(text(f"SHOW COLUMNS FROM {table_name};"))
        columns = [row[0] for row in result.fetchall()]
        return ", ".join(columns)
    except Exception as e:
        logger.error("Erro ao buscar colunas da tabela %s: %s", table_name, e)
        return f"⚠️ Erro ao buscar colunas da tabela '{table_name}': {str(e)}"
    finally:
        db.close()

@tool
def generate_chart(query: str, chart_type: str, title: str = "") -> dict:
    """
    Gera gráficos 2D de forma genérica a partir de uma consulta SQL, interpretando as colunas
    retornadas (categóricas vs. numéricas) e aplicando regras específicas para cada tipo de gráfico.
    
    Parâmetros:
      - query: instrução SQL para obter dados.
      - chart_type: 'bar', 'line', 'pie', 'scatter', 'heatmap'.
      - title: título opcional do gráfico.
    
    Retorno:
      - dict com:
          - "image": imagem em Base64,
          - "message": mensagem de sucesso,
          - "error": mensagem de erro, se houver.
    """
    db = next(get_db())
    try:
        logger.info("Executando Query:\n%s", query)
        result = db.execute(text(query))
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        if df.empty:
            return {"error": "Nenhum dado encontrado pela consulta."}
        
        numeric_cols, cat_cols = classify_columns(df)
        logger.info("Colunas numéricas: %s", numeric_cols)
        logger.info("Colunas categóricas: %s", cat_cols)
        
        plt.figure(figsize=(10, 6))
        
        if chart_type == "pie":
            # Gráfico de pizza: usa os rótulos do próprio pie e não precisa de rotação.
            if len(cat_cols) < 1 or len(numeric_cols) < 1:
                return {"error": "Para gráfico de pizza, é necessário pelo menos 1 coluna categórica e 1 numérica."}
            cat_col = cat_cols[0]
            measure_col = numeric_cols[0]
            df[measure_col] = pd.to_numeric(df[measure_col], errors='coerce')
            if df[measure_col].isna().all():
                return {"error": f"A coluna '{measure_col}' não pôde ser interpretada como numérica."}
            
            # Cálculo de porcentagens
            total = df[measure_col].sum()
            df['porcentagem'] = (df[measure_col] / total) * 100
            
            plt.pie(df[measure_col], labels=df[cat_col], autopct='%1.1f%%')
            plt.title(title if title else f"Distribuição de {measure_col} por {cat_col}")
            plt.ylabel("")
        
        elif chart_type in ["bar", "line"]:
            if len(cat_cols) == 0 and len(numeric_cols) >= 1:
                # Apenas dados numéricos: plota índice vs. valores
                df_numeric = df.copy().apply(pd.to_numeric, errors='coerce')
                df_numeric.index = range(len(df_numeric))
                if chart_type == "bar":
                    ax = df_numeric.plot(kind="bar")
                else:
                    ax = df_numeric.plot(kind="line")
                # Rotaciona os rótulos se houver muitos índices
                if len(df_numeric.index) > 5:
                    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
                plt.xlabel("Índice")
                plt.ylabel("Valores")
                if not title:
                    title = f"{chart_type.capitalize()} - colunas numéricas"
            elif len(cat_cols) == 1 and len(numeric_cols) >= 1:
                # 1 coluna categórica e 1 ou mais numéricas
                cat_col = cat_cols[0]
                df_temp = df.copy()
                for c in numeric_cols:
                    df_temp[c] = pd.to_numeric(df_temp[c], errors='coerce')
                if chart_type == "bar":
                    ax = df_temp.plot(kind="bar", x=cat_col, y=numeric_cols)
                else:
                    ax = df_temp.plot(kind="line", x=cat_col, y=numeric_cols)
                # Rotaciona os rótulos se houver mais de 5 categorias distintas
                if df_temp[cat_col].nunique() > 5:
                    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
                if not title:
                    title = f"{chart_type.capitalize()} de {numeric_cols} por {cat_col}"
            elif len(cat_cols) >= 2 and len(numeric_cols) >= 1:
                # Quando há duas ou mais categorias: pivot
                cat1, cat2 = cat_cols[0], cat_cols[1]
                measure_col = numeric_cols[0]
                df_pivot = df.pivot_table(index=cat1, columns=cat2, values=measure_col, aggfunc='sum').fillna(0)
                if chart_type == "bar":
                    ax = df_pivot.plot(kind="bar")
                else:
                    ax = df_pivot.plot(kind="line")
                # Rotaciona os rótulos do índice se houver muitos valores
                if df_pivot.index.nunique() > 5:
                    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
                plt.xlabel(cat1)
                plt.legend(title=cat2, bbox_to_anchor=(1.02, 1), loc='upper left')
                if not title:
                    title = f"{chart_type.capitalize()} - {measure_col}, {cat1} vs. {cat2}"
            else:
                return {"error": (
                    f"Não foi possível gerar gráfico '{chart_type}' com {len(cat_cols)} colunas categóricas e {len(numeric_cols)} colunas numéricas."
                )}
            plt.title(title)
        
        elif chart_type == "scatter":
            if len(numeric_cols) < 2:
                return {"error": "Scatter requer pelo menos 2 colunas numéricas (para X e Y)."}
            df_scatter = df.copy()
            for c in numeric_cols:
                df_scatter[c] = pd.to_numeric(df_scatter[c], errors='coerce')
            x_col = numeric_cols[0]
            y_col = numeric_cols[1]
            if len(numeric_cols) >= 3:
                c_col = numeric_cols[2]
                scatter = plt.scatter(x=df_scatter[x_col], y=df_scatter[y_col],
                                      c=df_scatter[c_col], cmap="viridis")
                plt.colorbar(scatter, label=c_col)
                if not title:
                    title = f"Scatter - X={x_col}, Y={y_col}, Cor={c_col}"
            else:
                plt.scatter(x=df_scatter[x_col], y=df_scatter[y_col])
                if not title:
                    title = f"Scatter - X={x_col}, Y={y_col}"
            plt.xlabel(x_col)
            plt.ylabel(y_col)
            plt.title(title)
        
        elif chart_type == "heatmap":
            if len(cat_cols) < 2 or len(numeric_cols) < 1:
                return {"error": "Heatmap requer pelo menos 2 colunas categóricas e 1 coluna numérica."}
            cat1, cat2 = cat_cols[0], cat_cols[1]
            measure_col = numeric_cols[0]
            df_pivot = df.pivot_table(index=cat1, columns=cat2, values=measure_col, aggfunc='sum').fillna(0)
            sns.heatmap(df_pivot, annot=True, cmap="Blues", fmt=".0f", linewidths=0.5)
            plt.xlabel(cat2)
            plt.ylabel(cat1)
            if not title:
                title = f"Heatmap de {measure_col} | {cat1} vs {cat2}"
            plt.title(title)
        
        else:
            return {"error": (
                f"Tipo de gráfico '{chart_type}' não reconhecido. Use: bar, line, pie, scatter, heatmap."
            )}
        
        # Converter a figura para Base64
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close()
        return {
            "image": f"data:image/png;base64,{img_base64}",
            "message": f"Gráfico '{chart_type}' gerado com sucesso."
        }
    
    except Exception as e:
        logger.exception("Erro ao gerar gráfico:")
        return {"error": str(e)}
    
    finally:
        db.close()

@tool
def generate_generic_heatmap(
    query: str,
    row: str = None,
    column: str = None,
    value: str = None,
    aggfunc: str = 'sum',
    title: str = "Heatmap"
) -> dict:
    """
    Gera um heatmap de forma genérica a partir de uma consulta SQL.
    
    Parâmetros:
      - query: instrução SQL para obter os dados.
      - row: coluna a ser utilizada como índice do pivot (linhas). Se não informado, será inferido.
      - column: coluna a ser utilizada como colunas do pivot. Se não informado, será inferido.
      - value: coluna cujos valores serão agregados. Se não informado, será inferido.
      - aggfunc: função de agregação (padrão: 'sum').
      - title: título do heatmap.
      
    Retorno:
      - dict com:
          - "image": imagem em Base64,
          - "message": mensagem de sucesso,
          - "error": mensagem de erro, se houver.
    """
    db = next(get_db())
    try:
        logger.info("Executando Query para heatmap:\n%s", query)
        result = db.execute(text(query))
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        if df.empty:
            return {"error": "Nenhum dado encontrado pela consulta."}
        
        # Se os parâmetros não forem informados, tenta inferir automaticamente
        if not row or not column or not value:
            numeric_cols, cat_cols = classify_columns(df)
            if len(cat_cols) >= 2 and len(numeric_cols) >= 1:
                if not row:
                    row = cat_cols[0]
                if not column:
                    column = cat_cols[1]
                if not value:
                    value = numeric_cols[0]
            else:
                return {"error": "Não foi possível inferir as colunas para o heatmap. Informe 'row', 'column' e 'value' manualmente."}
        
        df_pivot = df.pivot_table(index=row, columns=column, values=value, aggfunc=aggfunc).fillna(0)
        plt.figure(figsize=(10, 6))
        sns.heatmap(df_pivot, annot=True, cmap="Blues", fmt=".0f", linewidths=0.5)
        plt.xlabel(column)
        plt.ylabel(row)
        plt.title(title)
        
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close()
        
        return {
            "image": f"data:image/png;base64,{img_base64}",
            "message": f"Heatmap gerado com sucesso utilizando {aggfunc}."
        }
    except Exception as e:
        logger.exception("Erro ao gerar heatmap:")
        return {"error": str(e)}
    finally:
        db.close()

def get_tools():
    return [consult_database, show_tables, get_table_columns, generate_chart, generate_generic_heatmap]
