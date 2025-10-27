import logging
from app.services.retrieval import RetrievalService

def sync_documents():
    """
    Executa a sincronização dos documentos:
      - Carrega os documentos do Google Drive.
      - Processa os textos e gera as embeddings via Azure OpenAI.
      - Adiciona os documentos processados ao banco vetorial do Supabase.
    
    Retorna:
        dict: Mensagem informando o sucesso da operação.
    
    Lança:
        Exception: Caso ocorra algum erro durante a sincronização.
    """
    try:
        retrieval_service = RetrievalService()
        retrieval_service.load_and_add_documents()
        return {"message": "Documentos sincronizados com sucesso!"}
    except Exception as e:
        logging.error(f"Erro ao sincronizar documentos: {e}")
        raise e
