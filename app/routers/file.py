from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from io import BytesIO
from fastapi.responses import StreamingResponse
import os
from uuid import uuid4

from app import schemas
from app.controllers import file as file_controller
from app.core.database import get_db
from app.utils.tools import Tools

router = APIRouter(
    prefix="/files",
    tags=["files"]
)

# 🚀 Rota para criar um novo arquivo
@router.post("/", response_model=schemas.FileRead, status_code=status.HTTP_201_CREATED)
def create_file(file_create: schemas.FileCreate, db: Session = Depends(get_db)):
    return file_controller.create_file(file_create, db)

# 🔍 Rota para obter um arquivo pelo ID
@router.get("/{file_id}", response_model=schemas.FileRead)
def get_file(file_id: int, db: Session = Depends(get_db)):
    return file_controller.get_file(file_id, db)

# 🔄 Rota para atualizar um arquivo pelo ID
@router.put("/{file_id}", response_model=schemas.FileRead)
def update_file(file_id: int, file_update: schemas.FileUpdate, db: Session = Depends(get_db)):
    return file_controller.update_file(file_id, file_update, db)

# 🗑️ Rota para deletar um arquivo pelo ID
@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(file_id: int, db: Session = Depends(get_db)):
    return file_controller.delete_file(file_id, db)

# 📃 Rota para listar todos os arquivos
@router.get("/", response_model=List[schemas.FileRead])
def list_files(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return file_controller.list_files(db, skip=skip, limit=limit)

# 🚀 Rota para upload de arquivo
@router.post("/upload", response_model=schemas.FileRead, status_code=status.HTTP_201_CREATED)
async def upload_file(
    message_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    tools = Tools()
    extension = file.filename.rsplit(".", 1)[-1].lower()
    file_stream = BytesIO(await file.read())
    text = tools.extract_text_from_file(file_stream, extension)
    print(text)
    uploads_dir = "uploads"
    os.makedirs(uploads_dir, exist_ok=True)
    file_id_val = uuid4().hex
    saved_file_path = os.path.join(uploads_dir, f"{file_id_val}_{file.filename}")
    with open(saved_file_path, "wb") as f:
        f.write(file_stream.getbuffer())
    file_create = schemas.FileCreate(
        message_id=message_id,
        file_path=saved_file_path,
        file_type=file.content_type
    )
    return file_controller.create_file(file_create, db)
