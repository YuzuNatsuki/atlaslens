"""Cross-agent memory — shared state every AtlasLens agent can read.

Scoped per EM (``actor_id == em_member_id``). Today's slots:

- ``focus_members``: members the EM wants every agent to keep an eye on,
  with a free-text reason. Used by the AI Assistant and the Daily Pulse
  prompts to bias their output.
- ``recent_topics``: last few questions the EM asked the assistant, so a
  fresh chat session feels continuous.
- ``preferences``: a small dict of UI / tone preferences (e.g. preferred
  reply style) the assistant honours by default.

Persisted to Cosmos ``ai_artefacts`` (``kind=agent-memory``,
``key=<em_member_id>``). Falls back to in-memory state when Cosmos is
not configured so the API surface remains stable in local / test envs.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.services.artefact_store import (
    get_artefact,
    save_artefact,
)

log = logging.getLogger(__name__)

ARTEFACT_KIND = "agent-memory"
MAX_FOCUS_MEMBERS = 10
MAX_RECENT_TOPICS = 8
MAX_TOPIC_LEN = 200


def _empty_memory(em_member_id: str) -> dict[str, Any]:
    return {
        "em_member_id": em_member_id,
        "focus_members": [],
        "recent_topics": [],
        "preferences": {},
        "updated_at": None,
    }


def get_memory(em_member_id: str) -> dict[str, Any]:
    """Return the EM's memory document (always a usable shape)."""
    cached = get_artefact(ARTEFACT_KIND, em_member_id)
    if cached is None:
        return _empty_memory(em_member_id)
    payload = cached.get("payload") or {}
    base = _empty_memory(em_member_id)
    base.update(
        {
            k: v
            for k, v in payload.items()
            if k in {"focus_members", "recent_topics", "preferences"}
            and v is not None
        }
    )
    base["updated_at"] = cached.get("generated_at")
    return base


def _save(em_member_id: str, memory: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "em_member_id": em_member_id,
        "focus_members": memory.get("focus_members", []),
        "recent_topics": memory.get("recent_topics", []),
        "preferences": memory.get("preferences", {}),
    }
    saved = save_artefact(
        ARTEFACT_KIND,
        em_member_id,
        payload,
        extra={"em_member_id": em_member_id},
    )
    return {
        "em_member_id": em_member_id,
        **payload,
        "updated_at": saved.get("generated_at"),
    }


def add_focus_member(
    em_member_id: str, *, member_id: str, reason: str = ""
) -> dict[str, Any]:
    """Add (or refresh) a focused member. Idempotent on member_id."""
    member_id = member_id.strip()
    if not member_id:
        return get_memory(em_member_id)
    memory = get_memory(em_member_id)
    focus = [f for f in memory["focus_members"] if f.get("member_id") != member_id]
    focus.insert(
        0,
        {
            "member_id": member_id,
            "reason": (reason or "")[:300],
            "pinned_at": datetime.now(UTC).isoformat(timespec="seconds"),
        },
    )
    memory["focus_members"] = focus[:MAX_FOCUS_MEMBERS]
    return _save(em_member_id, memory)


def remove_focus_member(em_member_id: str, *, member_id: str) -> dict[str, Any]:
    memory = get_memory(em_member_id)
    memory["focus_members"] = [
        f for f in memory["focus_members"] if f.get("member_id") != member_id
    ]
    return _save(em_member_id, memory)


def record_topic(em_member_id: str, *, topic: str) -> dict[str, Any]:
    """Push a short summary line onto the EM's recent topic stack."""
    topic = (topic or "").strip()
    if not topic:
        return get_memory(em_member_id)
    topic = topic[:MAX_TOPIC_LEN]
    memory = get_memory(em_member_id)
    items = [
        t
        for t in memory["recent_topics"]
        if isinstance(t, dict) and t.get("topic") != topic
    ]
    items.insert(
        0,
        {
            "topic": topic,
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
        },
    )
    memory["recent_topics"] = items[:MAX_RECENT_TOPICS]
    return _save(em_member_id, memory)


def update_preferences(em_member_id: str, *, patch: dict[str, Any]) -> dict[str, Any]:
    """Shallow-merge UI / tone preferences."""
    memory = get_memory(em_member_id)
    prefs = dict(memory.get("preferences") or {})
    for k, v in (patch or {}).items():
        if v is None:
            prefs.pop(k, None)
        else:
            prefs[str(k)] = v
    memory["preferences"] = prefs
    return _save(em_member_id, memory)


def format_for_prompt(
    em_member_id: str,
    *,
    member_index: dict[str, str] | None = None,
) -> str:
    """Render the EM's memory as a compact Japanese context block.

    Returns an empty string when there's nothing useful to inject — callers
    can ``if block:`` it into the system prompt without conditionals.
    """
    memory = get_memory(em_member_id)
    focus = memory.get("focus_members") or []
    topics = memory.get("recent_topics") or []
    prefs = memory.get("preferences") or {}

    if not focus and not topics and not prefs:
        return ""

    lines: list[str] = ["[ユーザーの共有メモリ — 各エージェントが参照しています]"]

    if focus:
        rendered = []
        for f in focus[:MAX_FOCUS_MEMBERS]:
            mid = f.get("member_id", "")
            name = (member_index or {}).get(mid, mid)
            reason = f.get("reason") or ""
            label = f"{name} ({mid})" if name != mid else mid
            rendered.append(f"- {label}: {reason}" if reason else f"- {label}")
        lines.append("注目しているメンバー:")
        lines.extend(rendered)

    if topics:
        lines.append("直近ユーザーが確認した話題:")
        for t in topics[:5]:
            if isinstance(t, dict) and t.get("topic"):
                lines.append(f"- {t['topic']}")

    if prefs:
        flat = ", ".join(f"{k}={v}" for k, v in prefs.items() if v is not None)
        if flat:
            lines.append(f"ユーザーの好み: {flat}")

    return "\n".join(lines)
