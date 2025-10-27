from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
from app import schemas
from app.controllers import message as message_controller
from app.core.database import get_db

router = APIRouter(
    prefix="/messages",
    tags=["messages"]
)

# 🚀 Nova Rota para Criar uma Mensagem com Arquivo Opcional
@router.post("/with-file", response_model=schemas.IAResponse, status_code=status.HTTP_201_CREATED)
async def create_message_with_file(
    chat_id: int = Form(...),
    content: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    return await message_controller.create_message_with_file(chat_id, content, file, db)  # ✅ Agora usamos await corretamente

# 🚀 Rota para criar uma nova mensagem
@router.post("/", response_model=schemas.IAResponse, status_code=status.HTTP_201_CREATED)
async def create_message(message_create: schemas.MessageCreate, db: Session = Depends(get_db)):
    return message_controller.create_message(message_create, db)  # ✅ Agora usamos await corretamente

# 🔍 Rota para obter uma mensagem pelo ID
@router.get("/{message_id}", response_model=schemas.MessageRead)
def get_message(message_id: int, db: Session = Depends(get_db)):
    return message_controller.get_message(message_id, db)

# 🔄 Rota para atualizar uma mensagem pelo ID
@router.put("/{message_id}", response_model=schemas.MessageRead)
def update_message(message_id: int, message_update: schemas.MessageUpdate, db: Session = Depends(get_db)):
    return message_controller.update_message(message_id, message_update, db)

# 🗑️ Rota para deletar uma mensagem pelo ID
@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(message_id: int, db: Session = Depends(get_db)):
    return message_controller.delete_message(message_id, db)

# 📃 Rota para listar todas as mensagens
@router.get("/", response_model=List[schemas.MessageRead])
def list_messages(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return message_controller.list_messages(db, skip=skip, limit=limit)
