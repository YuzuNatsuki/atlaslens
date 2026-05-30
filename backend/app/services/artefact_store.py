"""Cosmos-backed persistent store for generated AI artefacts.

Used today by Daily Pulse to keep team summaries across restarts and across
container replicas. The in-memory TTL cache (`app.core.cache`) is still useful
for hot demo clicks, but it loses data on redeploy — Cosmos is the source of
truth.

Documents:
    {
        "id":          "team-summary:2026-05-12",
        "kind":        "team-summary",
        "key":         "2026-05-12",
        "payload":     <arbitrary JSON-serialisable dict>,
        "generated_at": "2026-05-30T07:12:33.456+00:00",
        "model":       "gpt-4o",     # optional
        "report_count": 6,            # optional
    }

Partition key is `/kind` so artefacts of the same type are co-located.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.core.cosmos_client import cosmos_configured, get_container

log = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _doc_id(kind: str, key: str) -> str:
    return f"{kind}:{key}"


def get_artefact(kind: str, key: str) -> dict[str, Any] | None:
    """Return the stored artefact or None when missing / Cosmos not configured."""
    if not cosmos_configured():
        return None
    try:
        item = get_container("ai_artefacts").read_item(
            item=_doc_id(kind, key),
            partition_key=kind,
        )
    except Exception:  # noqa: BLE001 — Cosmos raises a SDK-specific 404
        return None
    return _strip_meta(item)


def save_artefact(
    kind: str,
    key: str,
    payload: dict[str, Any],
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Upsert an artefact. Returns the stored body (without Cosmos meta)."""
    if not cosmos_configured():
        return {"payload": payload, "generated_at": _now_iso(), **(extra or {})}
    doc = {
        "id": _doc_id(kind, key),
        "kind": kind,
        "key": key,
        "payload": payload,
        "generated_at": _now_iso(),
        **(extra or {}),
    }
    try:
        get_container("ai_artefacts").upsert_item(doc)
    except Exception as exc:  # noqa: BLE001
        log.warning("artefact save failed (%s:%s): %s", kind, key, exc)
    return _strip_meta(doc)


def delete_artefact(kind: str, key: str) -> bool:
    if not cosmos_configured():
        return False
    try:
        get_container("ai_artefacts").delete_item(
            item=_doc_id(kind, key),
            partition_key=kind,
        )
        return True
    except Exception:  # noqa: BLE001
        return False


def list_artefacts(kind: str, *, limit: int = 50) -> list[dict[str, Any]]:
    """Return artefacts of a kind, most-recently-generated first."""
    if not cosmos_configured():
        return []
    container = get_container("ai_artefacts")
    items = container.query_items(
        query=(
            "SELECT TOP @lim c.id, c.kind, c.key, c.generated_at, c.report_count, c.model "
            "FROM c WHERE c.kind = @kind ORDER BY c.generated_at DESC"
        ),
        parameters=[
            {"name": "@kind", "value": kind},
            {"name": "@lim", "value": int(limit)},
        ],
        partition_key=kind,
    )
    return [_strip_meta(i) for i in items]


def _strip_meta(doc: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in doc.items() if not k.startswith("_")}
