from langchain_openai import AzureChatOpenAI
from app.core.config import settings
from typing import Optional, Dict, Any


def get_model(
    model_name: str = "gpt-4o-mini",
    temperature: Optional[float] = 0.1,
    model_kwargs: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = settings.AZURE_OPENAI_API_KEY,
    request_timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
    presence_penalty: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
    seed: Optional[int] = None,
    streaming: bool = False,
    n: Optional[int] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    azure_endpoint: Optional[str] = settings.AZURE_OPENAI_ENDPOINT,
    api_version: Optional[str] = '2024-08-01-preview',
):
    """Configura e retorna o modelo LLM com os parâmetros opcionais apenas se estiverem definidos."""

    params = {
        "api_key": api_key,
        "azure_deployment": model_name,
        "openai_api_version": api_version,
        "temperature": temperature,
        "model_kwargs": model_kwargs or {},
        "request_timeout": request_timeout,
        "max_retries": max_retries,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty,
        "seed": seed,
        "streaming": streaming,
        "n": n,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "azure_endpoint": azure_endpoint,

    }

    # Remove os parâmetros que são None
    filtered_params = {k: v for k, v in params.items() if v is not None}
    return AzureChatOpenAI(**filtered_params)

