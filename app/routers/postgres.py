from fastapi import APIRouter, HTTPException, status
from app.controllers import postgres as postgres_controller

router = APIRouter(
    prefix="/postgres",
    tags=["postgres"]
)

@router.post("/sync", status_code=status.HTTP_200_OK)
def sync_documents_route():
    """
    Rota para sincronizar os documentos:
    - Chama o controller que executa o serviço de sincronização.
    """
    try:
        result = postgres_controller.sync_documents()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao sincronizar documentos")
