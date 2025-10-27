import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl

load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )

    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # URLs do Banco de Dados como string, para o create_engine() não falhar
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    READ_ONLY_DATABASE_URL: str = os.getenv("READ_ONLY_DATABASE_URL", "")
    DATABASE_URL_NEXUN: str = os.getenv("DATABASE_URL_NEXUN", "")
    DATABASE_URL_AZURE: str = os.getenv("DATABASE_URL_AZURE", "")

    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")
    ADMIN_USERNAME: str = "admin"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")

    # Agora é um 'str'; se quiser usar como lista, faça .split(",") no código
    FRONT_END: str = os.getenv("FRONT_END", "")

    # Azure OpenAI
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "")
    AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
    AZURE_OPENAI_DEPLOYMENT_EMAIL: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_EMAIL", "")

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # Google Drive
    FOLDER_ID: str = os.getenv("FOLDER_ID", "")
    
    # Azure Form Recognizer
    AZURE_FORM_RECOGNIZER_ENDPOINT: str = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT", "")
    AZURE_FORM_RECOGNIZER_API_KEY: str = os.getenv("AZURE_FORM_RECOGNIZER_API_KEY", "")

settings = Settings()
