"""Insight Action Tracking API — PDCA loop for AI-surfaced signals.

EM-only. Closes the loop between "AI flagged this" and "EM resolved it"
so we can demonstrate the system is actually moving the needle.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import AuthContext, get_auth_context, require_em
from app.services import insight_actions

router = APIRouter()


async def _em_only(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    return await require_em(auth)


class CreateActionPayload(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    source_kind: str | None = None  # e.g. "team-summary-range"
    source_key: str | None = None  # e.g. "2026-05-13_2026-05-19"
    signal_id: str | None = None  # opaque fingerprint from the source artefact
    signal_kind: str | None = None  # retention / friction / capacity / engagement / health
    member_id: str | None = None
    evidence_dates: list[str] = Field(default_factory=list)
    details: str = ""
    initial_note: str = ""


class UpdateActionPayload(BaseModel):
    status: str | None = None  # open / in_progress / resolved / wont_fix
    note: str = ""
    details: str | None = None


@router.post("")
async def create_action(
    payload: CreateActionPayload,
    auth: AuthContext = Depends(_em_only),
) -> dict:
    return insight_actions.create_action(
        created_by=auth.member_id,
        title=payload.title,
        source_kind=payload.source_kind,
        source_key=payload.source_key,
        signal_id=payload.signal_id,
        signal_kind=payload.signal_kind,
        member_id=payload.member_id,
        evidence_dates=payload.evidence_dates,
        details=payload.details,
        initial_note=payload.initial_note,
    )


@router.get("")
async def list_actions(
    _: AuthContext = Depends(_em_only),
    status: str | None = None,
    member_id: str | None = None,
    limit: int = 50,
) -> dict:
    rows = insight_actions.list_actions(
        status=status, member_id=member_id, limit=limit
    )
    return {"actions": rows, "count": len(rows)}


@router.get("/{action_id}")
async def get_action(
    action_id: str,
    _: AuthContext = Depends(_em_only),
) -> dict:
    found = insight_actions.get_action(action_id)
    if found is None:
        raise HTTPException(status_code=404, detail="action not found")
    return found


@router.patch("/{action_id}")
async def update_action(
    action_id: str,
    payload: UpdateActionPayload,
    auth: AuthContext = Depends(_em_only),
) -> dict:
    try:
        updated = insight_actions.update_action(
            action_id,
            actor=auth.member_id,
            status=payload.status,
            note=payload.note,
            details=payload.details,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="action not found")
    return updated


@router.delete("/{action_id}", status_code=204)
async def delete_action(
    action_id: str,
    _: AuthContext = Depends(_em_only),
) -> None:
    ok = insight_actions.delete_action(action_id)
    if not ok:
        raise HTTPException(status_code=404, detail="action not found")
