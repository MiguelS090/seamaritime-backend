"""
Módulo centralizado para Structured Output usando Azure OpenAI + LangChain.

Este módulo fornece funções utilitárias para criar modelos LLM com saída estruturada,
garantindo que a resposta da IA seja sempre validada e compatível com schemas Pydantic.

Autor: SeaMaritime AI Team
Data: 2025-10-08
"""

import logging
from typing import Type, TypeVar, Optional, Dict, Any
from pydantic import BaseModel
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

# TypeVar para generic typing
T = TypeVar('T', bound=BaseModel)


def get_structured_azure_model(
    schema: Type[T],
    model_name: str = "gpt-4o",
    temperature: float = 0.0,
    max_tokens: int = 12000,
    api_key: Optional[str] = None,
    azure_endpoint: Optional[str] = None,
    api_version: str = '2024-08-01-preview',
    **kwargs
) -> AzureChatOpenAI:
    """
    Cria um modelo Azure OpenAI com Structured Output configurado.
    
    Esta função garante que a saída do modelo seja sempre validada contra
    o schema Pydantic fornecido, eliminando a necessidade de parsing manual.
    
    Args:
        schema: Classe Pydantic que define a estrutura esperada da resposta
        model_name: Nome do deployment Azure (padrão: gpt-4o)
        temperature: Controla a aleatoriedade (0.0 = determinístico)
        max_tokens: Número máximo de tokens na resposta
        api_key: Chave da API Azure (usa settings.AZURE_OPENAI_API_KEY se None)
        azure_endpoint: Endpoint Azure (usa settings.AZURE_OPENAI_ENDPOINT se None)
        api_version: Versão da API Azure
        **kwargs: Parâmetros adicionais para AzureChatOpenAI
        
    Returns:
        AzureChatOpenAI configurado com structured output
        
    Example:
        >>> from pydantic import BaseModel
        >>> class MyResponse(BaseModel):
        ...     name: str
        ...     age: int
        >>> 
        >>> llm = get_structured_azure_model(MyResponse)
        >>> result = llm.invoke("Extract: John is 30 years old")
        >>> print(result.name, result.age)  # "John", 30
    """
    
    # Usar valores padrão do settings se não fornecidos
    api_key = api_key or settings.AZURE_OPENAI_API_KEY
    azure_endpoint = azure_endpoint or settings.AZURE_OPENAI_ENDPOINT
    
    # Configurar modelo base
    base_model = AzureChatOpenAI(
        api_key=api_key,
        azure_deployment=model_name,
        azure_endpoint=azure_endpoint,
        openai_api_version=api_version,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )
    
    # Configurar structured output usando JSON Schema
    structured_model = base_model.with_structured_output(
        schema,
        method="json_schema",  # Força o modelo a seguir o schema
        strict=True  # Validação rigorosa
    )
    
    logger.info(
        f"✅ Modelo estruturado criado: {model_name} com schema {schema.__name__}"
    )
    
    return structured_model


def get_structured_openai_model(
    schema: Type[T],
    model_name: str = "gpt-4o-mini",
    temperature: float = 0.0,
    max_tokens: int = 12000,
    api_key: Optional[str] = None,
    **kwargs
) -> ChatOpenAI:
    """
    Cria um modelo OpenAI com Structured Output configurado.
    
    Similar a get_structured_azure_model, mas para OpenAI direto.
    
    Args:
        schema: Classe Pydantic que define a estrutura esperada
        model_name: Nome do modelo OpenAI
        temperature: Controla a aleatoriedade
        max_tokens: Número máximo de tokens
        api_key: Chave da API OpenAI (usa settings.OPENAI_API_KEY se None)
        **kwargs: Parâmetros adicionais
        
    Returns:
        ChatOpenAI configurado com structured output
    """
    
    api_key = api_key or settings.OPENAI_API_KEY
    
    base_model = ChatOpenAI(
        api_key=api_key,
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )
    
    structured_model = base_model.with_structured_output(
        schema,
        method="json_schema",
        strict=True
    )
    
    logger.info(
        f"✅ Modelo estruturado criado: {model_name} com schema {schema.__name__}"
    )
    
    return structured_model


def validate_structured_output(result: Any, expected_schema: Type[T]) -> T:
    """
    Valida que a saída é do tipo esperado.
    
    Útil para garantir type safety em tempo de execução.
    
    Args:
        result: Resultado retornado pelo modelo
        expected_schema: Schema Pydantic esperado
        
    Returns:
        Resultado validado
        
    Raises:
        TypeError: Se o resultado não for do tipo esperado
    """
    if not isinstance(result, expected_schema):
        raise TypeError(
            f"Resultado não é do tipo esperado. "
            f"Esperado: {expected_schema.__name__}, "
            f"Recebido: {type(result).__name__}"
        )
    
    return result


# Exemplo de uso documentado
if __name__ == "__main__":
    """
    Exemplo de uso do módulo structured_llm.
    """
    from pydantic import BaseModel, Field
    
    class VesselInfo(BaseModel):
        """Schema exemplo para extração de informações de navio"""
        name: str = Field(description="Nome do navio")
        imo: str = Field(description="Número IMO")
        flag: str = Field(description="Bandeira do navio")
    
    # Criar modelo estruturado
    llm = get_structured_azure_model(
        schema=VesselInfo,
        model_name="gpt-4o",
        temperature=0.0
    )
    
    # Usar modelo
    prompt = "Extract vessel info: Ship ASK PROGRESS with IMO 9283629 under Mauritius flag"
    result = llm.invoke(prompt)
    
    # Resultado é automaticamente um objeto VesselInfo validado
    print(f"Name: {result.name}")
    print(f"IMO: {result.imo}")
    print(f"Flag: {result.flag}")

