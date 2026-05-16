"""Member-scoped API — what an authenticated user can see about themselves."""

from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import AuthContext, get_auth_context
from app.models.schemas import DailyReport, Goal
from app.services.daily_pulse import draft_daily_report
from app.services.daily_report_store import save_daily_report
from app.services.data_loader import DataLoader
from app.services.goal_store import delete_goal, list_goals, upsert_goal
from app.services.prep_notes_store import get_current_prep, save_prep

router = APIRouter()


@router.get("/profile")
async def my_profile(auth: AuthContext = Depends(get_auth_context)) -> dict:
    loader = DataLoader()
    profile = loader.get_profile(auth.member_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")
    return profile.model_dump(mode="json")


@router.get("/goals")
async def my_goals(auth: AuthContext = Depends(get_auth_context)) -> dict:
    goals = list_goals(auth.member_id)
    return {"goals": [g.model_dump(mode="json") for g in goals]}


class GoalPayload(BaseModel):
    id: str | None = None
    period: str
    objective: str
    key_results: list[str] = Field(default_factory=list)
    progress_pct: int = Field(default=0, ge=0, le=100)
    status: str = "on_track"


def _make_goal_id(member_id: str, period: str) -> str:
    import uuid

    return f"g-{member_id}-{period}-{uuid.uuid4().hex[:6]}"


@router.post("/goals")
async def create_goal(
    payload: GoalPayload,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    goal = Goal(
        id=payload.id or _make_goal_id(auth.member_id, payload.period),
        member_id=auth.member_id,
        period=payload.period,
        objective=payload.objective,
        key_results=[kr for kr in payload.key_results if kr.strip()],
        progress_pct=payload.progress_pct,
        status=payload.status,
    )
    saved = upsert_goal(auth.member_id, goal)
    return {"goal": saved.model_dump(mode="json")}


@router.put("/goals/{goal_id}")
async def update_goal(
    goal_id: str,
    payload: GoalPayload,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    goal = Goal(
        id=goal_id,
        member_id=auth.member_id,
        period=payload.period,
        objective=payload.objective,
        key_results=[kr for kr in payload.key_results if kr.strip()],
        progress_pct=payload.progress_pct,
        status=payload.status,
    )
    saved = upsert_goal(auth.member_id, goal)
    return {"goal": saved.model_dump(mode="json")}


@router.delete("/goals/{goal_id}")
async def remove_goal(
    goal_id: str,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    deleted = delete_goal(auth.member_id, goal_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="goal not found")
    return {"deleted": goal_id}


@router.get("/daily-reports")
async def my_daily_reports(auth: AuthContext = Depends(get_auth_context)) -> dict:
    loader = DataLoader()
    reports = loader.load_daily_reports(auth.member_id)
    return {"reports": [r.model_dump(mode="json") for r in reports]}


class DailyReportPayload(BaseModel):
    report_date: date_type
    yesterday: str = ""
    today: str = ""
    blockers: str = ""
    mood: int | None = Field(default=None, ge=1, le=5)


@router.post("/daily-reports")
async def submit_my_daily_report(
    payload: DailyReportPayload,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    report = DailyReport(
        id=f"daily-{auth.member_id}-{payload.report_date.isoformat()}",
        member_id=auth.member_id,
        report_date=payload.report_date,
        yesterday=payload.yesterday.strip(),
        today=payload.today.strip(),
        blockers=payload.blockers.strip(),
        mood=payload.mood,
    )
    save_daily_report(report)
    return {"saved": True, "report": report.model_dump(mode="json")}


class DraftDailyPayload(BaseModel):
    report_date: date_type
    bullet_hints: list[str] = Field(default_factory=list)


@router.post("/daily-reports/draft")
async def draft_my_daily_report(
    payload: DraftDailyPayload,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    return await draft_daily_report(
        member_id=auth.member_id,
        report_date=payload.report_date,
        bullet_hints=payload.bullet_hints,
    )


@router.get("/one-on-ones")
async def my_one_on_ones(auth: AuthContext = Depends(get_auth_context)) -> dict:
    loader = DataLoader()
    items = loader.load_one_on_ones(auth.member_id)
    return {"one_on_ones": [o.model_dump(mode="json") for o in items]}


@router.get("/meetings")
async def my_meetings(auth: AuthContext = Depends(get_auth_context)) -> dict:
    loader = DataLoader()
    items = loader.load_meetings(member_id=auth.member_id)
    return {"meetings": [m.model_dump(mode="json") for m in items]}


# ---------- Pre-1on1 prep notes ----------


class PrepNotesPayload(BaseModel):
    notes: str


@router.get("/prep-notes")
async def get_prep_notes(auth: AuthContext = Depends(get_auth_context)) -> dict:
    return get_current_prep(auth.member_id)


@router.post("/prep-notes")
async def save_prep_notes(
    payload: PrepNotesPayload,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    return save_prep(auth.member_id, payload.notes)
