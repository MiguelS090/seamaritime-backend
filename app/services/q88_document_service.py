import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.AI.chat_graph.q88_state import Q88LLMResult

logger = logging.getLogger(__name__)

# Configuração de diretórios
DOCUMENTS_DIR = Path("documents/processed")
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


class DocumentMetadata(BaseModel):
    """Metadados do documento processado"""
    document_id: str = Field(description="ID único do documento")
    original_filename: str = Field(description="Nome original do ficheiro")
    vessel_name: Optional[str] = Field(description="Nome do navio")
    imo_number: Optional[str] = Field(description="Número IMO")
    created_at: datetime = Field(description="Data de criação")
    updated_at: datetime = Field(description="Última atualização")
    saved_by: Optional[str] = Field(default=None, description="Usuário que salvou")
    status: str = Field(default="draft", description="Status: draft, validated, sent_to_bc")
    file_path: Optional[str] = Field(default=None, description="Caminho do ficheiro original")


class EditHistory(BaseModel):
    """Histórico de edições de um campo"""
    timestamp: datetime = Field(description="Quando foi editado")
    field_name: str = Field(description="Nome do campo editado")
    old_value: Optional[str] = Field(description="Valor anterior")
    new_value: str = Field(description="Novo valor")
    edited_by: Optional[str] = Field(default=None, description="Quem editou")


class Q88ProcessedDocument(BaseModel):
    """Documento Q88 processado e salvo"""
    metadata: DocumentMetadata
    llm_result: Q88LLMResult
    edit_history: List[EditHistory] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Q88DocumentService:
    """Serviço para gestão de documentos Q88"""
    
    def __init__(self):
        self.documents_dir = DOCUMENTS_DIR
        logger.info(f"📁 Q88DocumentService inicializado: {self.documents_dir.absolute()}")
    
    def save_document(
        self,
        llm_result: Q88LLMResult,
        original_filename: str,
        file_path: Optional[str] = None,
        saved_by: Optional[str] = None
    ) -> Q88ProcessedDocument:
        """
        Salva um documento Q88 processado em JSON.
        
        Args:
            llm_result: Resultado estruturado da IA
            original_filename: Nome original do ficheiro enviado
            file_path: Caminho do ficheiro original (opcional)
            saved_by: Usuário que está a salvar (opcional)
            
        Returns:
            Q88ProcessedDocument: Documento salvo com metadados
        """
        try:
            # Extrair informações críticas do LLM result
            vessel_name = self._extract_vessel_name(llm_result)
            imo_number = self._extract_imo_number(llm_result)
            
            # Gerar ID único com timestamp
            timestamp = datetime.now()
            timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
            
            # Criar nome de ficheiro seguro
            safe_vessel_name = self._sanitize_filename(vessel_name or "UNKNOWN")
            safe_imo = self._sanitize_filename(imo_number or "NO_IMO")
            
            document_id = f"{safe_vessel_name}_{safe_imo}_{timestamp_str}"
            filename = f"{document_id}.json"
            
            # Criar metadados
            metadata = DocumentMetadata(
                document_id=document_id,
                original_filename=original_filename,
                vessel_name=vessel_name,
                imo_number=imo_number,
                created_at=timestamp,
                updated_at=timestamp,
                saved_by=saved_by,
                status="draft",
                file_path=file_path
            )
            
            # Criar documento completo
            document = Q88ProcessedDocument(
                metadata=metadata,
                llm_result=llm_result,
                edit_history=[]
            )
            
            # Salvar em JSON
            file_path_full = self.documents_dir / filename
            with open(file_path_full, 'w', encoding='utf-8') as f:
                json.dump(
                    document.model_dump(mode='json'),
                    f,
                    indent=2,
                    ensure_ascii=False
                )
            
            logger.info(f"✅ Documento salvo: {filename}")
            logger.info(f"   - Vessel: {vessel_name}")
            logger.info(f"   - IMO: {imo_number}")
            logger.info(f"   - Caminho: {file_path_full}")
            
            return document
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar documento: {str(e)}")
            raise
    
    def list_documents(
        self,
        vessel_name: Optional[str] = None,
        imo_number: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Lista documentos com filtros opcionais.
        
        Args:
            vessel_name: Filtrar por nome do navio (parcial)
            imo_number: Filtrar por número IMO (parcial)
            status: Filtrar por status
            date_from: Filtrar por data inicial
            date_to: Filtrar por data final
            limit: Número máximo de resultados
            offset: Deslocamento para paginação
            
        Returns:
            Lista de metadados dos documentos
        """
        try:
            documents = []
            
            # Listar todos os ficheiros JSON
            for json_file in self.documents_dir.glob("*.json"):
                try:
                    doc = self._load_document(json_file)
                    
                    # Aplicar filtros
                    if vessel_name and vessel_name.lower() not in (doc.metadata.vessel_name or "").lower():
                        continue
                    
                    if imo_number and imo_number not in (doc.metadata.imo_number or ""):
                        continue
                    
                    if status and doc.metadata.status != status:
                        continue
                    
                    if date_from and doc.metadata.created_at < date_from:
                        continue
                    
                    if date_to and doc.metadata.created_at > date_to:
                        continue
                    
                    # Adicionar à lista
                    documents.append({
                        "document_id": doc.metadata.document_id,
                        "vessel_name": doc.metadata.vessel_name,
                        "imo_number": doc.metadata.imo_number,
                        "original_filename": doc.metadata.original_filename,
                        "created_at": doc.metadata.created_at.isoformat(),
                        "updated_at": doc.metadata.updated_at.isoformat(),
                        "status": doc.metadata.status,
                        "total_fields_found": doc.llm_result.summary.total_fields_found,
                        "completion_percentage": doc.llm_result.summary.completion_percentage,
                        "edit_count": len(doc.edit_history)
                    })
                    
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao processar {json_file}: {e}")
                    continue
            
            # Ordenar por data (mais recente primeiro)
            documents.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Aplicar paginação
            paginated = documents[offset:offset + limit]
            
            logger.info(f"📋 Listados {len(paginated)} documentos (total: {len(documents)})")
            return paginated
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar documentos: {str(e)}")
            raise
    
    def get_document(self, document_id: str) -> Optional[Q88ProcessedDocument]:
        """
        Obtém um documento específico pelo ID.
        
        Args:
            document_id: ID do documento
            
        Returns:
            Q88ProcessedDocument ou None se não encontrado
        """
        try:
            # Procurar ficheiro
            json_file = self.documents_dir / f"{document_id}.json"
            
            if not json_file.exists():
                logger.warning(f"⚠️ Documento não encontrado: {document_id}")
                return None
            
            doc = self._load_document(json_file)
            logger.info(f"✅ Documento carregado: {document_id}")
            return doc
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar documento {document_id}: {str(e)}")
            raise
    
    def update_document_field(
        self,
        document_id: str,
        field_name: str,
        new_value: str,
        edited_by: Optional[str] = None
    ) -> Q88ProcessedDocument:
        """
        Atualiza um campo específico do documento.
        
        Args:
            document_id: ID do documento
            field_name: Nome do campo a atualizar
            new_value: Novo valor
            edited_by: Quem está a editar
            
        Returns:
            Documento atualizado
        """
        try:
            # Carregar documento
            doc = self.get_document(document_id)
            if not doc:
                raise ValueError(f"Documento não encontrado: {document_id}")
            
            # Verificar se campo existe
            if not hasattr(doc.llm_result.fields, field_name):
                raise ValueError(f"Campo não existe: {field_name}")
            
            # Obter valor antigo
            old_field = getattr(doc.llm_result.fields, field_name)
            old_value = old_field.value if old_field else None
            
            # Atualizar campo
            from app.AI.chat_graph.q88_state import Q88FieldData
            new_field_data = Q88FieldData(
                value=new_value,
                confidence=1.0,  # Confiança máxima para edições manuais
                source="manual-edit",
                raw_text=f"Edited by {edited_by or 'user'}"
            )
            setattr(doc.llm_result.fields, field_name, new_field_data)
            
            # Adicionar ao histórico
            edit_entry = EditHistory(
                timestamp=datetime.now(),
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                edited_by=edited_by
            )
            doc.edit_history.append(edit_entry)
            
            # Atualizar metadados
            doc.metadata.updated_at = datetime.now()
            
            # Salvar documento atualizado
            self._save_document(doc)
            
            logger.info(f"✅ Campo atualizado: {field_name} = {new_value}")
            return doc
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar campo: {str(e)}")
            raise
    
    def update_document_status(
        self,
        document_id: str,
        new_status: str
    ) -> Q88ProcessedDocument:
        """
        Atualiza o status do documento.
        
        Args:
            document_id: ID do documento
            new_status: Novo status (draft, validated, sent_to_bc)
            
        Returns:
            Documento atualizado
        """
        try:
            doc = self.get_document(document_id)
            if not doc:
                raise ValueError(f"Documento não encontrado: {document_id}")
            
            old_status = doc.metadata.status
            doc.metadata.status = new_status
            doc.metadata.updated_at = datetime.now()
            
            self._save_document(doc)
            
            logger.info(f"✅ Status atualizado: {old_status} → {new_status}")
            return doc
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar status: {str(e)}")
            raise
    
    def delete_document(self, document_id: str) -> bool:
        """
        Remove um documento.
        
        Args:
            document_id: ID do documento
            
        Returns:
            True se removido com sucesso
        """
        try:
            json_file = self.documents_dir / f"{document_id}.json"
            
            if not json_file.exists():
                logger.warning(f"⚠️ Documento não encontrado: {document_id}")
                return False
            
            json_file.unlink()
            logger.info(f"✅ Documento removido: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao remover documento: {str(e)}")
            raise
    
    def _extract_vessel_name(self, llm_result: Q88LLMResult) -> Optional[str]:
        """Extrai nome do navio do LLM result"""
        if llm_result.fields.VesselName:
            return llm_result.fields.VesselName.value
        return None
    
    def _extract_imo_number(self, llm_result: Q88LLMResult) -> Optional[str]:
        """Extrai número IMO do LLM result"""
        if llm_result.fields.IMONumber:
            return llm_result.fields.IMONumber.value
        return None
    
    def _sanitize_filename(self, text: str) -> str:
        """Remove caracteres inválidos do nome de ficheiro"""
        import re
        # Remover caracteres especiais
        safe_text = re.sub(r'[^\w\s-]', '', text)
        # Substituir espaços por underscore
        safe_text = re.sub(r'\s+', '_', safe_text)
        # Limitar tamanho
        return safe_text[:50]
    
    def _load_document(self, json_file: Path) -> Q88ProcessedDocument:
        """Carrega documento de ficheiro JSON"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return Q88ProcessedDocument(**data)
    
    def _save_document(self, document: Q88ProcessedDocument) -> None:
        """Salva documento em ficheiro JSON"""
        filename = f"{document.metadata.document_id}.json"
        file_path = self.documents_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(
                document.model_dump(mode='json'),
                f,
                indent=2,
                ensure_ascii=False
            )
















