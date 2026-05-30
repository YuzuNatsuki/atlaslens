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
    discard_team_range_summary,
    discard_team_summary,
    draft_daily_report,
    list_team_range_summaries,
    list_team_summaries,
    summarize_team_day,
    summarize_team_range,
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


# ---------------- Range (multi-day trend) summary ----------------


class RangeGenerateRequest(BaseModel):
    start_date: date_type
    end_date: date_type
    force: bool = True


@router.get("/team-summary/range")
async def team_summary_range(
    start_date: date_type,
    end_date: date_type,
    _: AuthContext = Depends(_em_only),
) -> dict:
    """Return the stored multi-day trend summary, or generate on first request."""
    loader = DataLoader()
    try:
        return await summarize_team_range(start_date, end_date, loader, force=False)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/team-summary/range/generate")
async def regenerate_team_summary_range(
    payload: RangeGenerateRequest,
    _: AuthContext = Depends(_em_only),
) -> dict:
    """Force regeneration and overwrite the persisted range summary."""
    loader = DataLoader()
    try:
        return await summarize_team_range(
            payload.start_date,
            payload.end_date,
            loader,
            force=payload.force,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/team-summary/range")
async def remove_team_summary_range(
    start_date: date_type,
    end_date: date_type,
    _: AuthContext = Depends(_em_only),
) -> dict:
    ok = discard_team_range_summary(start_date, end_date)
    if not ok:
        raise HTTPException(status_code=404, detail="summary not found")
    return {
        "deleted": True,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }


@router.get("/team-summaries/range")
async def list_summaries_range(
    _: AuthContext = Depends(_em_only),
    limit: int = 30,
) -> dict:
    """List previously generated range summaries, newest first."""
    return {"summaries": await list_team_range_summaries(limit=limit)}
