"""Audit logging — records who did what against which entity.

Evaluation / people-management domains require an answer to "who viewed
whom's record" before the system can be trusted in production. AtlasLens
writes one row per sensitive request into the ``audit_events`` Cosmos
container (partition key ``/actor_id``).

When Cosmos isn't configured (local dev, tests) we fall back to a small
in-memory ring buffer so the API surface stays consistent.
"""

from __future__ import annotations

import logging
import uuid
from collections import deque
from datetime import UTC, datetime
from typing import Any

from app.core.cosmos_client import cosmos_configured, get_container

log = logging.getLogger(__name__)


# Sensitive actions worth logging by default. Routes outside this set do not
# emit an audit event so we don't drown the container with health probes.
ACTION_VIEW = "view"
ACTION_MUTATE = "mutate"
ACTION_LOGIN = "login"
ACTION_LOGIN_FAILED = "login_failed"
ACTION_AI_GENERATE = "ai.generate"
ACTION_AI_ASSISTANT = "ai.assistant"

_MAX_IN_MEMORY = 500
_in_memory: deque[dict[str, Any]] = deque(maxlen=_MAX_IN_MEMORY)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def record_event(
    *,
    actor_id: str,
    actor_email: str | None = None,
    actor_role: str | None = None,
    action: str,
    target_kind: str | None = None,
    target_id: str | None = None,
    path: str | None = None,
    method: str | None = None,
    status_code: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist (or buffer) one audit event. Never raises."""
    doc: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "actor_id": actor_id or "anonymous",
        "actor_email": actor_email,
        "actor_role": actor_role,
        "action": action,
        "target_kind": target_kind,
        "target_id": target_id,
        "path": path,
        "method": method,
        "status_code": status_code,
        "metadata": metadata or {},
        "occurred_at": _now_iso(),
    }
    if not cosmos_configured():
        _in_memory.append(doc)
        return doc
    try:
        get_container("audit_events").upsert_item(doc)
    except Exception as exc:  # noqa: BLE001
        log.warning("audit write failed: %s", exc)
        _in_memory.append(doc)
    return doc


def list_events(
    *,
    actor_id: str | None = None,
    action: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return recent events newest-first. ``actor_id`` lets the query stay
    on a single partition; without it we cross-partition (admin-only path)."""
    limit = max(1, min(limit, 500))
    if not cosmos_configured():
        rows = list(_in_memory)
        if actor_id:
            rows = [r for r in rows if r.get("actor_id") == actor_id]
        if action:
            rows = [r for r in rows if r.get("action") == action]
        rows.sort(key=lambda r: r.get("occurred_at", ""), reverse=True)
        return rows[:limit]

    clauses = []
    params: list[dict[str, Any]] = [{"name": "@lim", "value": int(limit)}]
    if actor_id:
        clauses.append("c.actor_id = @actor")
        params.append({"name": "@actor", "value": actor_id})
    if action:
        clauses.append("c.action = @action")
        params.append({"name": "@action", "value": action})
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = (
        f"SELECT TOP @lim c.id, c.actor_id, c.actor_email, c.actor_role, c.action, "
        f"c.target_kind, c.target_id, c.path, c.method, c.status_code, "
        f"c.metadata, c.occurred_at FROM c{where} ORDER BY c.occurred_at DESC"
    )
    container = get_container("audit_events")
    try:
        if actor_id:
            items = container.query_items(
                query=sql,
                parameters=params,
                partition_key=actor_id,
            )
        else:
            items = container.query_items(
                query=sql,
                parameters=params,
                enable_cross_partition_query=True,
            )
        return list(items)
    except Exception as exc:  # noqa: BLE001
        log.warning("audit list failed: %s", exc)
        return []


def reset_in_memory() -> None:
    """Test helper — clears the in-memory buffer."""
    _in_memory.clear()
