"""Azure OpenAI client — uses the model deployment under the Foundry resource.

We keep this thin helper because the multi-agent code is essentially a series
of stateless chat completion calls. Foundry Agent Service (managed agents,
threads) is reserved for paths where its overhead pays off — the Org Impact
Simulator is wired through Prompt Flow instead.
"""

from __future__ import annotations

from functools import lru_cache

from openai import AsyncAzureOpenAI

from app.core.config import get_settings


@lru_cache
def get_openai_client() -> AsyncAzureOpenAI:
    settings = get_settings()
    return AsyncAzureOpenAI(
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_endpoint=settings.azure_openai_endpoint,
    )


async def chat_complete(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float = 0.3,
    response_format: dict | None = None,
    max_tokens: int | None = None,
) -> str:
    settings = get_settings()
    client = get_openai_client()
    deployment = model or settings.azure_openai_chat_deployment
    kwargs: dict = {
        "model": deployment,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format:
        kwargs["response_format"] = response_format
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


async def embed(text: str) -> list[float]:
    settings = get_settings()
    client = get_openai_client()
    response = await client.embeddings.create(
        model=settings.azure_openai_embedding_deployment,
        input=text,
    )
    return response.data[0].embedding
