from langchain_googledrive.document_loaders import GoogleDriveLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_postgres.vectorstores import PGVector
from langchain_openai import AzureOpenAIEmbeddings
from app.core.database import get_db
from app.core.config import settings  # 🚀 Agora importa diretamente de config.py
import logging

# 📝 Configuração de logs para melhor depuração
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class RetrievalService:

    def __init__(self):
        # 🔑 Carrega configurações diretamente do config.py
        self.folder_id = settings.FOLDER_ID
        self.gdrive_credentials_file = "credentials.json"  
        self.azure_endpoint = settings.AZURE_OPENAI_ENDPOINT
        self.azure_api_key = settings.AZURE_OPENAI_API_KEY
        self.embedding_api_version = settings.AZURE_OPENAI_API_VERSION

    def _get_google_drive_loader(self):
        """📂 Inicializa o carregador do Google Drive."""
        try:
            return GoogleDriveLoader(
                gdrive_api_file=self.gdrive_credentials_file,
                folder_id=self.folder_id,
                recursive=True,
                includeItemsFromAllDrives=True,
                use_unstructured=False,
                enable_pypdf=True
            )
        except Exception as e:
            logging.error(f"❌ Erro ao inicializar GoogleDriveLoader: {e}")
            raise

    def _get_postgres_vector_store(self, embeddings):
        """📊 Obtém o armazenamento vetorial do PostgreSQL."""
        try:
            return PGVector(
                embeddings=embeddings,
                connection=settings.DATABASE_URL,
                collection_name="documents",
            )
        except Exception as e:
            logging.error(f"❌ Erro ao conectar ao PostgresVectorStore: {e}")
            raise

    def _get_azure_embeddings(self):
        """🧠 Obtém as embeddings do Azure OpenAI."""
        try:
            return AzureOpenAIEmbeddings(
                api_key=self.azure_api_key,
                api_version=self.embedding_api_version,
                azure_endpoint=self.azure_endpoint,
            )
        except Exception as e:
            logging.error(f"❌ Erro ao inicializar AzureOpenAIEmbeddings: {e}")
            raise

    def load_and_add_documents(self):
        """📂 Carrega documentos do Google Drive, processa e adiciona ao PostgreSQL."""
        try:
            self.delete_all_documents()

            loader = self._get_google_drive_loader()
            documents = loader.load()

            embeddings = self._get_azure_embeddings()
            with next(get_db()) as db_session:
                vector_store = self._get_postgres_vector_store(embeddings)
                text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
                split_documents = text_splitter.split_documents(documents)

                vector_store.add_documents(split_documents)
                logging.info("✅ Documentos carregados e adicionados com sucesso ao PostgreSQL!")
        except Exception as e:
            logging.error(f"❌ Erro ao carregar e adicionar documentos: {e}")
            raise

    def delete_all_documents(self):
        """🗑️ Exclui todos os documentos do banco vetorial no PostgreSQL."""
        try:
            with next(get_db()) as db_session:
                db_session.execute("DELETE FROM documents WHERE id IS NOT NULL;")
                db_session.commit()
                logging.info("✅ Todos os documentos foram deletados do PostgreSQL.")
        except Exception as e:
            logging.error(f"❌ Erro ao deletar documentos: {e}")
            raise