"""Insight Action Tracking (PDCA loop for AI-surfaced signals).

When AtlasLens surfaces a risk signal (e.g. retention concern in the Daily
Pulse range summary, or a stuck area in the Skill Growth Summary), the EM
needs a place to log "I'm acting on this" and later "this is resolved".

Each action lives in ``ai_artefacts`` (kind=``insight-action``,
key=<action_id>) so it survives restarts and lives next to the artefact
that spawned it. The status timeline is kept inline as a ``history`` list,
making the PDCA trail readable in one read.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.services.artefact_store import (
    delete_artefact,
    get_artefact,
    list_artefacts,
    save_artefact,
)

log = logging.getLogger(__name__)

ARTEFACT_KIND = "insight-action"

ALLOWED_STATUSES = ("open", "in_progress", "resolved", "wont_fix")
DEFAULT_STATUS = "open"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _normalise(action: dict[str, Any] | None) -> dict[str, Any] | None:
    if action is None:
        return None
    base: dict[str, Any] = {
        "id": action.get("id"),
        "status": action.get("status") or DEFAULT_STATUS,
        "title": action.get("title") or "",
        "source_kind": action.get("source_kind"),
        "source_key": action.get("source_key"),
        "signal_id": action.get("signal_id"),
        "member_id": action.get("member_id"),
        "signal_kind": action.get("signal_kind"),
        "evidence_dates": action.get("evidence_dates") or [],
        "details": action.get("details") or "",
        "history": list(action.get("history") or []),
        "created_at": action.get("created_at"),
        "created_by": action.get("created_by"),
        "updated_at": action.get("updated_at"),
    }
    return base


def create_action(
    *,
    created_by: str,
    title: str,
    source_kind: str | None = None,
    source_key: str | None = None,
    signal_id: str | None = None,
    member_id: str | None = None,
    signal_kind: str | None = None,
    evidence_dates: list[str] | None = None,
    details: str = "",
    initial_note: str = "",
) -> dict[str, Any]:
    """Create a new action tracker rooted at an AI-surfaced signal."""
    action_id = uuid.uuid4().hex
    now = _now_iso()
    history = [
        {
            "at": now,
            "by": created_by,
            "status": DEFAULT_STATUS,
            "note": initial_note or "(作成)",
        }
    ]
    payload = {
        "id": action_id,
        "status": DEFAULT_STATUS,
        "title": title.strip()[:200] or "(無題のアクション)",
        "source_kind": source_kind,
        "source_key": source_key,
        "signal_id": signal_id,
        "signal_kind": signal_kind,
        "member_id": member_id,
        "evidence_dates": evidence_dates or [],
        "details": (details or "").strip()[:2000],
        "history": history,
        "created_at": now,
        "created_by": created_by,
        "updated_at": now,
    }
    saved = save_artefact(
        ARTEFACT_KIND,
        action_id,
        payload,
        extra={
            "member_id": member_id,
            "status": DEFAULT_STATUS,
            "created_by": created_by,
            "signal_kind": signal_kind,
        },
    )
    payload["generated_at"] = saved.get("generated_at")
    return _normalise(payload)


def get_action(action_id: str) -> dict[str, Any] | None:
    cached = get_artefact(ARTEFACT_KIND, action_id)
    if cached is None:
        return None
    payload = _normalise(cached.get("payload"))
    if payload is None:
        return None
    payload.setdefault("created_at", cached.get("generated_at"))
    return payload


def update_action(
    action_id: str,
    *,
    actor: str,
    status: str | None = None,
    note: str = "",
    details: str | None = None,
) -> dict[str, Any] | None:
    """Append a status / note entry. Returns the updated action (or None)."""
    if status is not None and status not in ALLOWED_STATUSES:
        raise ValueError(f"unknown status: {status}")

    current = get_action(action_id)
    if current is None:
        return None

    new_status = status or current.get("status") or DEFAULT_STATUS
    entry: dict[str, Any] = {
        "at": _now_iso(),
        "by": actor,
        "status": new_status,
        "note": (note or "").strip()[:1000],
    }
    history = list(current.get("history") or [])
    history.append(entry)

    payload = dict(current)
    payload["status"] = new_status
    if details is not None:
        payload["details"] = details.strip()[:2000]
    payload["history"] = history
    payload["updated_at"] = entry["at"]

    save_artefact(
        ARTEFACT_KIND,
        action_id,
        payload,
        extra={
            "member_id": payload.get("member_id"),
            "status": new_status,
            "created_by": payload.get("created_by"),
            "signal_kind": payload.get("signal_kind"),
        },
    )
    return _normalise(payload)


def list_actions(
    *,
    status: str | None = None,
    member_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List recent actions newest-first, optionally filtered.

    We list via ``list_artefacts`` (returns metadata only) and then re-read
    the full payload per row so the UI sees the full timeline.
    """
    rows = list_artefacts(ARTEFACT_KIND, limit=max(limit * 4, 50))
    out: list[dict[str, Any]] = []
    for r in rows:
        key = r.get("key")
        if not key:
            continue
        cached = get_artefact(ARTEFACT_KIND, key)
        if cached is None:
            continue
        payload = _normalise(cached.get("payload"))
        if payload is None:
            continue
        if status and payload.get("status") != status:
            continue
        if member_id and payload.get("member_id") != member_id:
            continue
        payload.setdefault("created_at", cached.get("generated_at"))
        out.append(payload)
        if len(out) >= limit:
            break
    return out


def delete_action(action_id: str) -> bool:
    return delete_artefact(ARTEFACT_KIND, action_id)
