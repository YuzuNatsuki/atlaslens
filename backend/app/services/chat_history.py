"""Persist EM chat sessions (Cosmos ai_artefacts, with in-memory fallback)."""

from __future__ import annotations

from typing import Any

from app.core.cosmos_client import cosmos_configured
from app.services.artefact_store import delete_artefact, get_artefact, save_artefact

ARTEFACT_KIND = "em-chat-session"
MAX_MESSAGES = 80


# Dev / tests when Cosmos is not configured.
_memory: dict[str, dict[str, Any]] = {}


def _trim(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(messages) <= MAX_MESSAGES:
        return messages
    return messages[-MAX_MESSAGES:]


def _from_payload(payload: dict[str, Any], updated_at: str | None) -> dict[str, Any]:
    return {
        "messages": payload.get("messages") or [],
        "style": payload.get("style") or "standard",
        "style_instructions": payload.get("style_instructions"),
        "updated_at": updated_at,
    }


def get_session(member_id: str) -> dict[str, Any] | None:
    stored = get_artefact(ARTEFACT_KIND, member_id)
    if stored is not None:
        payload = stored.get("payload")
        if isinstance(payload, dict):
            return _from_payload(payload, stored.get("generated_at"))
    return _memory.get(member_id)


def save_session(
    member_id: str,
    *,
    messages: list[dict[str, Any]],
    style: str | None = "standard",
    style_instructions: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "messages": _trim(messages),
        "style": style or "standard",
    }
    if style_instructions and style_instructions.strip():
        payload["style_instructions"] = style_instructions.strip()

    if cosmos_configured():
        saved = save_artefact(ARTEFACT_KIND, member_id, payload)
        body = _from_payload(payload, saved.get("generated_at"))
        _memory.pop(member_id, None)
        return body

    body = _from_payload(payload, None)
    _memory[member_id] = body
    return body


def clear_session(member_id: str) -> None:
    delete_artefact(ARTEFACT_KIND, member_id)
    _memory.pop(member_id, None)
