"""Foundry Agent Service runner.

Hosts the Analyzer (and any future agents) as managed agents on Azure AI
Foundry. The Foundry Portal then shows each invocation as a thread/run with
full step traces — the same agents we run elsewhere via direct chat
completions become first-class agents that appear in the Foundry "Agents"
panel and can be inspected end-to-end.

Auth: DefaultAzureCredential. Locally this picks up `az login`; in the
Container App it uses the system-assigned managed identity (which must have
the "Azure AI User" role on the Foundry account).

The SDK (azure-ai-agents) is synchronous, so blocking calls are wrapped in
`asyncio.to_thread` to stay friendly with FastAPI's event loop.
"""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from typing import Any

from azure.ai.agents import AgentsClient
from azure.identity import DefaultAzureCredential

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Cached agent_id per (name, model, instructions-fingerprint). We avoid
# creating a fresh agent for every request — the SDK lets us reuse one across
# many threads, which is the natural unit Foundry exposes in its Portal.
_agent_cache: dict[tuple[str, str, int], str] = {}


@lru_cache
def _get_client() -> AgentsClient | None:
    settings = get_settings()
    endpoint = getattr(settings, "azure_ai_foundry_project_endpoint", "") or ""
    if not endpoint:
        return None
    try:
        return AgentsClient(endpoint=endpoint, credential=DefaultAzureCredential())
    except Exception as exc:  # noqa: BLE001
        logger.warning("Foundry AgentsClient init failed: %s", exc)
        return None


def is_available() -> bool:
    return _get_client() is not None


def _ensure_agent_sync(client: AgentsClient, name: str, model: str, instructions: str) -> str:
    """Find an agent by name (latest match) or create a new one. Returns agent_id."""
    key = (name, model, hash(instructions))
    if key in _agent_cache:
        return _agent_cache[key]

    # Look for an existing agent with the same name. Foundry doesn't enforce
    # uniqueness by name, but we keep one per (name, instructions) tuple so
    # the Portal stays readable.
    try:
        for agent in client.list_agents():
            if agent.name == name and agent.model == model and agent.instructions == instructions:
                _agent_cache[key] = agent.id
                return agent.id
    except Exception as exc:  # noqa: BLE001
        logger.warning("list_agents failed (will create new): %s", exc)

    created = client.create_agent(model=model, name=name, instructions=instructions)
    _agent_cache[key] = created.id
    return created.id


def _run_sync(
    client: AgentsClient,
    agent_id: str,
    user_prompt: str,
) -> str:
    """One thread → one message → run-and-wait → read assistant reply."""
    thread = client.threads.create()
    client.messages.create(thread_id=thread.id, role="user", content=user_prompt)
    run = client.runs.create_and_process(thread_id=thread.id, agent_id=agent_id)
    if getattr(run, "status", None) == "failed":
        err = getattr(run, "last_error", None)
        raise RuntimeError(f"Foundry run failed: {err}")
    msg = client.messages.get_last_message_text_by_role(thread_id=thread.id, role="assistant")
    if msg is None:
        return ""
    # `msg` is a MessageTextContent with .text.value
    text = getattr(getattr(msg, "text", None), "value", None)
    return text or ""


async def run_agent(
    *,
    name: str,
    instructions: str,
    user_prompt: str,
    model: str | None = None,
) -> str:
    """Run a Foundry-hosted agent and return the assistant's reply text.

    Raises RuntimeError if Foundry is not configured (`is_available()` is False)
    or if the run itself fails. Callers should catch and fall back to direct
    chat completions.
    """
    client = _get_client()
    if client is None:
        raise RuntimeError("Foundry Agent Service is not configured")
    settings = get_settings()
    model_name = model or settings.azure_openai_chat_deployment

    def _blocking() -> str:
        agent_id = _ensure_agent_sync(client, name, model_name, instructions)
        return _run_sync(client, agent_id, user_prompt)

    return await asyncio.to_thread(_blocking)


def diagnostics() -> dict[str, Any]:
    """Used by /health to report whether Foundry agents are reachable."""
    client = _get_client()
    if client is None:
        return {"configured": False}
    try:
        names = [a.name for a in client.list_agents()][:5]
        return {"configured": True, "agents_sample": names}
    except Exception as exc:  # noqa: BLE001
        return {"configured": True, "error": str(exc)}
