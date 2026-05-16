"""1on1 Companion (M3) API — prepare packets, draft minutes, persist records. EM only."""

from datetime import datetime
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import AuthContext, get_auth_context, require_em
from app.core.cache import cache
from app.models.schemas import OneOnOne
from app.services.data_loader import DataLoader
from app.services.one_on_one_companion import (
    draft_minutes_from_notes,
    prepare_one_on_one_packet,
)
from app.services.one_on_one_store import make_one_on_one_id, save_one_on_one

router = APIRouter()


async def _em_only(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    return await require_em(auth)


class MinutesDraftRequest(BaseModel):
    member_id: str
    raw_notes: str


@router.get("/packet/{member_id}")
async def get_packet(member_id: str, auth: AuthContext = Depends(_em_only)) -> dict:
    loader = DataLoader()
    members = {m.id: m for m in loader.load_profiles()}
    if member_id not in members:
        raise HTTPException(status_code=404, detail=f"member {member_id} not found")
    return await prepare_one_on_one_packet(member_id, loader)


@router.post("/draft-minutes")
async def draft_minutes(
    payload: MinutesDraftRequest,
    auth: AuthContext = Depends(_em_only),
) -> dict:
    return await draft_minutes_from_notes(
        em_id=auth.member_id,
        member_id=payload.member_id,
        raw_notes=payload.raw_notes,
    )


class OneOnOneRecord(BaseModel):
    member_id: str
    held_at: datetime | None = None
    held_on: date_type | None = None
    topics: list[str] = Field(default_factory=list)
    notes: str = ""
    todos: list[str] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)


@router.post("/records")
async def save_record(
    payload: OneOnOneRecord,
    auth: AuthContext = Depends(_em_only),
) -> dict:
    """Persist a 1on1 record so it appears in the member's history."""
    held_at = payload.held_at or (
        datetime.combine(payload.held_on, datetime.min.time())
        if payload.held_on
        else datetime.now()
    )
    record = OneOnOne(
        id=make_one_on_one_id(auth.member_id, payload.member_id, held_at),
        em_id=auth.member_id,
        member_id=payload.member_id,
        held_at=held_at,
        topics=[t for t in payload.topics if t.strip()],
        notes=payload.notes.strip(),
        todos=[t for t in payload.todos if t.strip()],
        follow_ups=[f for f in payload.follow_ups if f.strip()],
    )
    saved = save_one_on_one(record)
    # Bust the prep-packet cache so the next prep run sees the new 1on1.
    cache.invalidate(f"1on1packet:{payload.member_id}")
    return {"saved": True, "record": saved.model_dump(mode="json")}
