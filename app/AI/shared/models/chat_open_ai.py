from langchain_openai import ChatOpenAI
from app.core.config import settings
from typing import Optional, Dict, Any

def get_model(
    model_name: str = "gpt-4o-mini",
    temperature: Optional[float] = None,
    model_kwargs: Optional[Dict[str, Any]] = None,
    openai_api_key: Optional[str] = settings.OPENAI_API_KEY,
    openai_api_base: Optional[str] = None,
    openai_organization: Optional[str] = None,
    openai_proxy: Optional[str] = None,
    request_timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
    presence_penalty: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
    seed: Optional[int] = None,
    streaming: bool = False,
    n: Optional[int] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None
):
    """Configura e retorna o modelo LLM com os parâmetros opcionais apenas se estiverem definidos."""

    params = {
        "api_key": openai_api_key,
        "model": model_name,
        "temperature": temperature,
        "model_kwargs": model_kwargs or {},
        "base_url": openai_api_base,
        "organization": openai_organization,
        "proxy": openai_proxy,
        "request_timeout": request_timeout,
        "max_retries": max_retries,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty,
        "seed": seed,
        "streaming": streaming,
        "n": n,
        "top_p": top_p,
        "max_tokens": max_tokens
    }

    # Remove os parâmetros que são None
    filtered_params = {k: v for k, v in params.items() if v is not None}
    return ChatOpenAI(**filtered_params)
