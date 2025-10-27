"""
================================================================================
Azure AD OAuth2 Configuration for Business Central Integration
================================================================================
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class AzureADSettings(BaseSettings):
    """
    Configurações para autenticação Azure AD
    """
    
    # Azure AD Settings
    AZURE_AD_TENANT_ID: str = os.getenv("AZURE_AD_TENANT_ID", "")
    AZURE_AD_CLIENT_ID: str = os.getenv("AZURE_AD_CLIENT_ID", "")
    AZURE_AD_CLIENT_SECRET: str = os.getenv("AZURE_AD_CLIENT_SECRET", "")
    
    # Azure AD Endpoints
    AZURE_AD_AUTHORITY: str = f"https://login.microsoftonline.com/{AZURE_AD_TENANT_ID}"
    AZURE_AD_TOKEN_URL: str = f"https://login.microsoftonline.com/{AZURE_AD_TENANT_ID}/oauth2/v2.0/token"
    AZURE_AD_JWKS_URL: str = f"https://login.microsoftonline.com/{AZURE_AD_TENANT_ID}/discovery/v2.0/keys"
    
    # API Settings
    API_AUDIENCE: Optional[str] = None  # api://your-client-id
    API_SCOPES: list = ["api://default"]
    
    # Desenvolvimento: permitir bypass de autenticação
    ENABLE_AZURE_AD_AUTH: bool = os.getenv("ENABLE_AZURE_AD_AUTH", "false").lower() == "true"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignorar campos extra do .env

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Construir API Audience se não foi fornecido
        if not self.API_AUDIENCE and self.AZURE_AD_CLIENT_ID:
            self.API_AUDIENCE = f"api://{self.AZURE_AD_CLIENT_ID}"


# Instância global das configurações
azure_ad_settings = AzureADSettings()

