from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from typing import List, Optional
from app.models.message import Message
from app.models.chat import Chat
from app.models.file import File
from app.schemas.message import MessageCreate, MessageRead, MessageUpdate, IAResponse
from app.AI.chat_graph.chat_graph import ChatGraph
from app.utils.tools import Tools
import os
from io import BytesIO

# Função para criar uma nova mensagem (sem arquivo)
def create_message(message_create: MessageCreate, db: Session) -> IAResponse:
    chat = db.query(Chat).filter(Chat.id == message_create.chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found 🚫")
    
    # Cria e salva a mensagem do usuário
    new_message = Message(
        chat_id=message_create.chat_id,
        sender="user",
        content=message_create.content
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    # Invoca o fluxo do ChatGraph
    chat_graph = ChatGraph()
    print("-------------------------------------------")
    print("Iniciando IA")
    print("-------------------------------------------")
    ia_response_data = chat_graph.invoke(new_message.chat_id, new_message.content)
    print("-------------------------------------------")
    print("Termino IA e inicio IF")
    print("-------------------------------------------")
    if "messages" in ia_response_data:
        # Normalmente pegamos o último content
        ia_response_content = ia_response_data["messages"][-1].content
        # Se estiver vazio, você pode tentar pegar algum "ToolMessage" (o gráfico em base64) ou erro
        if not ia_response_content:
            # Vamos verificar se há ToolMessages (respostas de ferramenta)
            for msg in reversed(ia_response_data["messages"]):
                if msg.content:
                    ia_response_content = msg.content
                    break
    else:
        ia_response_content = "Erro na resposta da IA"
    
    print("-------------------------------------------")
    print("Termino IF")
    print("-------------------------------------------")

    # Salva a resposta da IA como mensagem "agent"
    ia_message = Message(chat_id=chat.id, sender="agent", content=ia_response_content)
    db.add(ia_message)
    db.commit()
    db.refresh(ia_message)

    print("-------------------------------------------")
    print("Resposta final do LLM ou da ferramenta:", ia_response_content)

    return IAResponse(user=new_message.content, ia=ia_response_content)

# Função para criar uma nova mensagem com arquivo opcional
async def create_message_with_file(chat_id: int, content: str, file: Optional[UploadFile], db: Session) -> IAResponse:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found 🚫")

    # Cria a mensagem do usuário
    user_message = Message(chat_id=chat_id, sender="user", content=content)
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    file_text = None

    if file:
        tools = Tools()
        extension = file.filename.rsplit(".", 1)[-1].lower()
        file_bytes = await file.read()
        file_stream = BytesIO(file_bytes)
        try:
            file_text = tools.extract_text_from_file(file_stream, extension)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Salva metadados do arquivo no BD (sem salvar fisicamente se não quiser)
        file_record = File(
            message_id=user_message.id,
            file_path=file.filename,
            file_type=file.content_type,
        )
        db.add(file_record)
        db.commit()

    # Invoca o fluxo do ChatGraph (agora com o texto do arquivo se existir)
    chat_graph = ChatGraph()
    ia_response_data = chat_graph.invoke(user_message.chat_id, user_message.content, file_text)
    if "messages" in ia_response_data:
        ia_response_content = ia_response_data["messages"][-1].content
        if not ia_response_content:
            # Verifica se há ToolMessages com conteúdo (gráficos, etc.)
            for msg in reversed(ia_response_data["messages"]):
                if msg.content:
                    ia_response_content = msg.content
                    break
    else:
        ia_response_content = "Erro na resposta da IA"

    # Cria a mensagem "agent"
    ia_message = Message(chat_id=chat_id, sender="agent", content=ia_response_content)
    db.add(ia_message)
    db.commit()
    db.refresh(ia_message)

    return IAResponse(user=user_message.content, ia=ia_message.content)

def get_message(message_id: int, db: Session) -> MessageRead:
    db_message = db.query(Message).filter(Message.id == message_id).first()
    if not db_message:
        raise HTTPException(status_code=404, detail="Message not found 🚫")
    return MessageRead.from_orm(db_message)

def update_message(message_id: int, message_update: MessageUpdate, db: Session) -> MessageRead:
    db_message = db.query(Message).filter(Message.id == message_id).first()
    if not db_message:
        raise HTTPException(status_code=404, detail="Message not found 🚫")
    if message_update.sender:
        db_message.sender = message_update.sender
    if message_update.content:
        db_message.content = message_update.content
    if message_update.chat_id:
        new_chat = db.query(Chat).filter(Chat.id == message_update.chat_id).first()
        if not new_chat:
            raise HTTPException(status_code=404, detail="New chat not found 🚫")
        db_message.chat_id = message_update.chat_id
    db.commit()
    db.refresh(db_message)
    return MessageRead.from_orm(db_message)

def delete_message(message_id: int, db: Session):
    db_message = db.query(Message).filter(Message.id == message_id).first()
    if not db_message:
        raise HTTPException(status_code=404, detail="Message not found 🚫")
    db.delete(db_message)
    db.commit()
    return {"detail": "Message deleted successfully ✅"}

def list_messages(db: Session, skip: int = 0, limit: int = 100) -> List[MessageRead]:
    messages = db.query(Message).offset(skip).limit(limit).all()
    return [MessageRead.from_orm(message) for message in messages]
