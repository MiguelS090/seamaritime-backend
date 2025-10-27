from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# 🚀 Importando configurações e banco de dados corretamente
from app.core.config import settings
from app.core.database import get_db
from app.routers import user, chat, message, file, configDB, auth, postgres, q88, q88_documents, business_central, bc_integration
from app.controllers import user as user_controller

# 🎯 Inicializa a API
app = FastAPI(
    title="Sistema de Chat baseado no ChatGPT",
    description="API para gerenciar usuários, chats, mensagens, arquivos e configurações.",
    version="1.0.0"
)

# 🌍 Configuração do CORS
origins = settings.FRONT_END if settings.FRONT_END else []

# Adicionar domínios do Business Central
bc_origins = [
    "https://businesscentral.dynamics.com",
    "https://*.businesscentral.dynamics.com",
    "https://businesscentral.dynamics.com/*",
]

# Combinar todas as origens
all_origins = origins + bc_origins if origins else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=all_origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 🚀 Incluir todas as rotas automaticamente
app.include_router(user.router)
app.include_router(chat.router)
app.include_router(message.router)
app.include_router(file.router)
app.include_router(configDB.router)
app.include_router(auth.router)
app.include_router(postgres.router)
app.include_router(q88.router)
app.include_router(q88_documents.router)
app.include_router(business_central.router)
app.include_router(bc_integration.router)

# 🎯 Evento de inicialização para criar o usuário admin
@app.on_event("startup")
def startup_event():
    db = next(get_db())
    try:
        user_controller.create_admin_user(db)
    finally:
        db.close()  # ✅ Fecha a conexão com o banco corretamente
