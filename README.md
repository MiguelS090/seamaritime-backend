--------------------------------------------------------------------------------
PROJETO BACK-END
--------------------------------------------------------------------------------

Este projeto é um back-end escrito em Python que utiliza:
 - FastAPI (rodando no Uvicorn)
 - Alembic para migrações de banco de dados
 - Pydantic para configurações e validações
 - (Opcional) um script de watch para detecção de mudanças nos modelos
 - Etc.

================================================================================
REQUISITOS
================================================================================
 - Python 3.10 ou superior instalado localmente
 - Banco de dados (MySQL, PostgreSQL, etc.), se não estiver usando SQLite
 - Pip (ou outro gerenciador de pacotes)
 - (Opcional) Biblioteca watchgod ou watchdog (caso use o script de “watch”)

================================================================================
EXEMPLO DE ARQUIVO .env
================================================================================

# ==============================
# 🌐 CONFIGURAÇÕES GERAIS
# ==============================
DEBUG=True

# ==============================
# 📂 BANCO DE DADOS (MySQL)
# ==============================
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/meu_banco
READ_ONLY_DATABASE_URL=
DATABASE_URL_NEXUN=
DATABASE_URL_AZURE=

# ==============================
# 🔐 AUTENTICAÇÃO
# ==============================
ADMIN_EMAIL=
ADMIN_PASSWORD=

SECRET_KEY=minha_chave_super_secreta
ALGORITHM=HS256

# ==============================
# 🌍 CORS (Cross-Origin Resource Sharing)
# ==============================
FRONT_END=http://localhost:3000,http://outro_frontend.com

# ==============================
# 🤖 AZURE OPENAI CONFIG
# ==============================
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_VERSION=
AZURE_OPENAI_DEPLOYMENT=
AZURE_OPENAI_DEPLOYMENT_EMAIL=

# ==============================
# 🛠️ SUPABASE CONFIG
# ==============================
SUPABASE_URL=
SUPABASE_KEY=

# ==============================
# 📂 GOOGLE DRIVE CONFIG
# ==============================
FOLDER_ID=

--------------------------------------------------------------------------------
COMO RODAR (LOCALMENTE, SEM DOCKER)
--------------------------------------------------------------------------------

1) CLONAR O REPOSITÓRIO
--------------------------------------------------------------------------------
( TERMINAL )
# ==============================
#  git clone https://github.com/seu-usuario/seu-repo.git
#  cd seu-repo
# ==============================


2) CRIAR E ATIVAR O VENV
--------------------------------------------------------------------------------
( TERMINAL )
# ==============================
#  python -m venv venv
#
#  :: Windows ::
#  venv\Scripts\activate
#
#  :: Linux/Mac ::
#  source venv/bin/activate
# ==============================


3) INSTALAR AS DEPENDÊNCIAS
--------------------------------------------------------------------------------
( TERMINAL )
# ==============================
#  pip install --upgrade | python.exe -m pip install --upgrade pip
#  pip install -r requirements.txt
# ==============================


4) CONFIGURAR O ARQUIVO .env
--------------------------------------------------------------------------------
Crie ou edite o arquivo .env na raiz do projeto. Use o exemplo acima, preenchendo 
as informações reais (credenciais, URLs etc.).


5) APLICAR MIGRAÇÕES DO ALEMBIC
--------------------------------------------------------------------------------
( TERMINAL )
# ==============================
#  aa
# ==============================

Caso faça alterações nos modelos e precise gerar uma migração:
# ==============================
#  alembic revision --autogenerate -m "Minha nova migração"
#  alembic upgrade head
# ==============================


6) OPCIONAL: INICIAR O WATCHDOG (MONITOR DE MODELOS)
--------------------------------------------------------------------------------
Se você possui um script, por exemplo watch_models.py, que observa alterações 
na pasta de modelos e gera/aplica migrações automaticamente, rode:

( TERMINAL )
# ==============================
#  python watch_models.py
# ==============================

*Certifique-se de ter instalado a biblioteca correspondente* (watchgod ou watchdog).
 - Ajuste o script conforme suas necessidades. 
 - Ao detectar mudanças, ele pode chamar "alembic revision --autogenerate" e
   "alembic upgrade head" automaticamente.


7) RODAR O SERVIDOR
--------------------------------------------------------------------------------
( TERMINAL )
# ==============================
#  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# ==============================

Abra o navegador em:
 - http://127.0.0.1:8000  (raiz da API)
 - http://127.0.0.1:8000/docs (Swagger, se FastAPI)
 - http://127.0.0.1:8000/redoc (Redoc, se FastAPI)


--------------------------------------------------------------------------------
OBSERVAÇÕES
--------------------------------------------------------------------------------
 - Em produção, normalmente não se usa --reload nem um script de watch automático.
 - Se usar MySQL ou PostgreSQL, verifique se o servidor está rodando e se a 
   DATABASE_URL no .env está correta.
 - Para limpar o banco, basta dropar as tabelas manualmente e rodar 
   alembic upgrade head novamente.
 - Este é um simples guia de como rodar o projeto localmente, sem Docker.
 
