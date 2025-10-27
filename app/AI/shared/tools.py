from sqlalchemy import text
from app.core.database import get_db 
from langchain.tools import BaseTool
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field


# ACESSO AO BANCO DE DADOS
class ArgsConsultDatabase(BaseModel):
    tool_input: str = Field(..., description="Query to be executed on the database.")

class ConsultDatabaseTool(BaseTool):
    name: str = "ConsultDatabase"  # ✅ Adicionando anotação de tipo explícita
    description: str = "Consulta o banco de dados, permitindo apenas operações de leitura."

    def _run(self, tool_input: str):
        db = next(get_db())  # Obtenha a sessão do banco de dados
        try:
            query_str = tool_input

            # Lista de comandos proibidos
            forbidden_commands = [
                "DELETE", "ALTER", "CREATE", "DROP", "UPDATE", "INSERT", "TRUNCATE", "REPLACE",
            ]

            # Verificar se a consulta contém algum comando proibido
            if any(command in query_str.upper() for command in forbidden_commands):
                return {"error": "Apenas operações de leitura são permitidas."}

            result = db.execute(text(query_str))

            if result.returns_rows:
                rows = result.fetchall()
                result_str = "\n".join(str(row) for row in rows)
                return result_str

            return {"rows_affected": result.rowcount}

        except Exception as e:
            return {"error": str(e)}

        finally:
            db.close()  # Fecha a sessão


# CONSULTA AS TABELAS DO BANCO DE DADOS
class ArgsShowTables(BaseModel):
    tool_input: str

class ShowTablesTool(BaseTool):
    name: str = "ShowTables"  # ✅ Adicionando anotação de tipo explícita
    description: str = "Exibe todas as tabelas do banco de dados."

    def _run(self, tool_input: str):
        db = next(get_db())  # Obtenha a sessão do banco de dados
        try:
            result = db.execute(text("SHOW TABLES;"))

            if result.returns_rows:
                rows = result.fetchall()
                result_str = "\n".join(str(row) for row in rows)
                return result_str

            return {"rows_affected": result.rowcount}

        except Exception:
            try:
                # Tenta consultar tabelas em bancos de dados SQLite
                result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))

                if result.returns_rows:
                    rows = result.fetchall()
                    result_str = "\n".join(str(row) for row in rows)
                    return result_str

                return {"rows_affected": result.rowcount}

            except Exception as e:
                return {"error": str(e)}

        finally:
            db.close()  # Fecha a sessão
