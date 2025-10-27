# Use uma imagem oficial do Python como base (ajuste a versão se necessário)
FROM python:3.10-slim-buster

# Instala pacotes necessários (git, ffmpeg, etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ffmpeg libpq-dev gcc\
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho
WORKDIR /app

# Cria o diretório para bancos locais (SQLite, se necessário)
RUN mkdir -p /app/data

# Copia o arquivo de dependências
COPY requirements.txt .

# Instala as dependências do projeto (inclua watchgod ou watchdog se usar script watch)
RUN pip install --no-cache-dir --timeout=100 -r requirements.txt

# Copia o restante do projeto para o contêiner
COPY . .

# Exponha a porta em que o servidor do seu back-end irá rodar (ajuste conforme necessário)
EXPOSE 8000

# Comando que roda tudo de uma vez
# 1) Alembic (migração)
# 2) Roda script watch (em background, com &)
# 3) Sobrescreve com uvicorn (em foreground)
CMD ["/bin/bash", "-c", "alembic upgrade head && python watch_models.py & uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
