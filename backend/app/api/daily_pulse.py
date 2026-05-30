"""Daily Pulse (M2) API — daily report drafting (Member) and team summary (EM).

Team summaries are persisted to Cosmos. `GET /team-summary?report_date=...`
returns the saved one (instant). `POST /team-summary/generate` always
regenerates and overwrites. `GET /team-summaries` lists past generations.
"""

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import AuthContext, get_auth_context, require_em
from app.services.daily_pulse import (
    discard_team_summary,
    draft_daily_report,
    list_team_summaries,
    summarize_team_day,
)
from app.services.data_loader import DataLoader

router = APIRouter()


async def _em_only(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    return await require_em(auth)


class DraftRequest(BaseModel):
    report_date: date_type
    bullet_hints: list[str] = []


class GenerateRequest(BaseModel):
    report_date: date_type
    force: bool = True


@router.post("/draft")
async def draft(
    payload: DraftRequest,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    """Generate a daily report draft for the current user."""
    return await draft_daily_report(
        member_id=auth.member_id,
        report_date=payload.report_date,
        bullet_hints=payload.bullet_hints,
    )


@router.get("/team-summary")
async def team_summary(
    report_date: date_type,
    _: AuthContext = Depends(_em_only),
) -> dict:
    """Return the stored summary or generate one on first request."""
    loader = DataLoader()
    return await summarize_team_day(report_date, loader, force=False)


@router.post("/team-summary/generate")
async def regenerate_team_summary(
    payload: GenerateRequest,
    _: AuthContext = Depends(_em_only),
) -> dict:
    """Force regeneration and overwrite the persisted summary."""
    loader = DataLoader()
    return await summarize_team_day(payload.report_date, loader, force=payload.force)


@router.delete("/team-summary")
async def remove_team_summary(
    report_date: date_type,
    _: AuthContext = Depends(_em_only),
) -> dict:
    ok = discard_team_summary(report_date)
    if not ok:
        raise HTTPException(status_code=404, detail="summary not found")
    return {"deleted": True, "date": report_date.isoformat()}


@router.get("/team-summaries")
async def list_summaries(
    _: AuthContext = Depends(_em_only),
    limit: int = 30,
) -> dict:
    """List previously generated team summaries, newest first."""
    return {"summaries": await list_team_summaries(limit=limit)}
