from app.controllers.chat import get_last_k_messages
from langchain_core.messages import HumanMessage, AIMessage
from typing import List
from app.core.database import get_db
from sqlalchemy.orm import Session

def get_k_messages_formatted(chat_id: int, k: int) -> List[object]:
    with next(get_db()) as db:  # Cria a session
        messages = get_last_k_messages(chat_id, k, db)

        formatted_messages = []
        # Reverte para colocar da mais antiga para a mais recente
        for message in reversed(messages):
            content = message.content or ""

            # Se contiver "base64", removemos ou substituímos
            if "base64" in content:
                content = "[Imagem em base64 omitida]" 
                # ou, se preferir, content = content.replace("base64", "[OMITIDO]")

            if message.sender.lower() == "agent":
                formatted_messages.append(AIMessage(content=content))
            else:
                formatted_messages.append(HumanMessage(content=content))

        return formatted_messages
