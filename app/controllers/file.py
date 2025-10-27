from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import List

from app.models.file import File
from app.schemas.file import FileCreate, FileRead, FileUpdate
from app.models.message import Message

# 🚀 Função para criar um novo arquivo
def create_file(file_create: FileCreate, db: Session) -> FileRead:
    message = db.query(Message).filter(Message.id == file_create.message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found 🚫")
    new_file = File(
        message_id=file_create.message_id,
        file_path=file_create.file_path,
        file_type=file_create.file_type
    )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    return FileRead.from_orm(new_file)

# 🔍 Função para obter um arquivo pelo ID
def get_file(file_id: int, db: Session) -> FileRead:
    db_file = db.query(File).filter(File.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found 🚫")
    return FileRead.from_orm(db_file)

# 🔄 Função para atualizar um arquivo pelo ID
def update_file(file_id: int, file_update: FileUpdate, db: Session) -> FileRead:
    db_file = db.query(File).filter(File.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found 🚫")
    if file_update.message_id:
        message = db.query(Message).filter(Message.id == file_update.message_id).first()
        if not message:
            raise HTTPException(status_code=404, detail="New message not found 🚫")
        db_file.message_id = file_update.message_id
    if file_update.file_path:
        db_file.file_path = file_update.file_path
    if file_update.file_type:
        db_file.file_type = file_update.file_type
    db.commit()
    db.refresh(db_file)
    return FileRead.from_orm(db_file)

# 🗑️ Função para deletar um arquivo pelo ID
def delete_file(file_id: int, db: Session):
    db_file = db.query(File).filter(File.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found 🚫")
    db.delete(db_file)
    db.commit()
    return {"detail": "File deleted successfully ✅"}

# 📃 Função para listar todos os arquivos
def list_files(db: Session, skip: int = 0, limit: int = 100) -> List[FileRead]:
    files = db.query(File).offset(skip).limit(limit).all()
    return [FileRead.from_orm(file) for file in files]
