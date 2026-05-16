"""Build a Semantic Kernel instance wired to Azure OpenAI."""

from __future__ import annotations

from functools import lru_cache

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

from app.core.config import get_settings


@lru_cache
def build_kernel() -> Kernel:
    settings = get_settings()
    kernel = Kernel()
    kernel.add_service(
        AzureChatCompletion(
            service_id="azure_chat",
            deployment_name=settings.azure_openai_chat_deployment,
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
    )
    kernel.add_service(
        AzureChatCompletion(
            service_id="azure_chat_fast",
            deployment_name=settings.azure_openai_chat_deployment_fast,
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
    )
    return kernel
