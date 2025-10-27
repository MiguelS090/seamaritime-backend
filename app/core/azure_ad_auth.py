"""
================================================================================
Azure AD OAuth2 Authentication Middleware
================================================================================
"""

import jwt
import logging
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient
from app.core.azure_ad_config import azure_ad_settings

logger = logging.getLogger(__name__)

# HTTP Bearer Security Scheme
security = HTTPBearer()


class AzureADAuth:
    """
    Classe para validação de tokens Azure AD
    """
    
    def __init__(self):
        self.jwks_client = None
        if azure_ad_settings.ENABLE_AZURE_AD_AUTH:
            try:
                self.jwks_client = PyJWKClient(azure_ad_settings.AZURE_AD_JWKS_URL)
                logger.info(f"✅ Azure AD Auth inicializado - Tenant: {azure_ad_settings.AZURE_AD_TENANT_ID}")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar Azure AD Auth: {e}")
    
    async def verify_token(
        self, 
        credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> dict:
        """
        Verifica e valida token Azure AD
        """
        
        # Se autenticação Azure AD está desabilitada, retornar mock
        if not azure_ad_settings.ENABLE_AZURE_AD_AUTH:
            logger.warning("⚠️ Azure AD Auth DESABILITADO - Modo desenvolvimento")
            return {
                "sub": "dev-user",
                "name": "Development User",
                "email": "dev@seamaritime.com",
                "roles": ["admin"]
            }
        
        token = credentials.credentials
        
        try:
            # Obter signing key do Azure AD
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Decodificar e validar token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=azure_ad_settings.API_AUDIENCE,
                issuer=f"https://login.microsoftonline.com/{azure_ad_settings.AZURE_AD_TENANT_ID}/v2.0",
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                }
            )
            
            logger.info(f"✅ Token validado com sucesso - User: {payload.get('name', 'Unknown')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.error("❌ Token expirado")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidAudienceError:
            logger.error("❌ Audience inválida")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido (audience)",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidIssuerError:
            logger.error("❌ Issuer inválido")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido (issuer)",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"❌ Erro ao validar token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token inválido: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )


# Instância global
azure_ad_auth = AzureADAuth()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    """
    Dependency para obter usuário autenticado
    """
    return await azure_ad_auth.verify_token(credentials)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[dict]:
    """
    Dependency para obter usuário autenticado (opcional)
    """
    if not credentials:
        return None
    return await azure_ad_auth.verify_token(credentials)

