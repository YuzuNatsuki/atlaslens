"""Daily Pulse (M2) API — daily report drafting (Member) and team summary (EM)."""

from datetime import date as date_type

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import AuthContext, get_auth_context, require_em
from app.services.data_loader import DataLoader
from app.services.daily_pulse import draft_daily_report, summarize_team_day

router = APIRouter()


async def _em_only(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    return await require_em(auth)


class DraftRequest(BaseModel):
    report_date: date_type
    bullet_hints: list[str] = []


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
    """EM-facing team summary."""
    loader = DataLoader()
    return await summarize_team_day(report_date, loader)
