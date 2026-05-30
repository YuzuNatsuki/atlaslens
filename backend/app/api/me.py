"""Member-scoped API — what an authenticated user can see about themselves."""

from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import AuthContext, get_auth_context
from app.models.schemas import DailyReport, Goal
from app.services import agent_memory
from app.services.daily_pulse import draft_daily_report
from app.services.daily_report_store import save_daily_report
from app.services.data_loader import DataLoader
from app.services.goal_store import delete_goal, list_goals, upsert_goal
from app.services.prep_notes_store import get_current_prep, save_prep
from app.services.skill_growth import (
    DEFAULT_WINDOW_DAYS as GROWTH_DEFAULT_WINDOW,
)
from app.services.skill_growth import (
    generate_summary as generate_skill_growth,
)
from app.services.skill_growth import (
    get_summary_by_key as get_growth_by_key,
)
from app.services.skill_growth import (
    latest_summary as latest_growth_summary_fn,
)
from app.services.skill_growth import (
    list_summaries as list_growth_summaries,
)

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
    # Optional career canvas fields. Shared common format across the org so
    # 1on1 / EM can read the same structure across members.
    career_vision_1y: str | None = None
    career_vision_3y: str | None = None
    skills_to_grow: list[str] = Field(default_factory=list)
    roles_to_explore: list[str] = Field(default_factory=list)
    support_needed: str | None = None


def _make_goal_id(member_id: str, period: str) -> str:
    import uuid

    return f"g-{member_id}-{period}-{uuid.uuid4().hex[:6]}"


def _goal_from_payload(
    goal_id: str, member_id: str, payload: GoalPayload
) -> Goal:
    return Goal(
        id=goal_id,
        member_id=member_id,
        period=payload.period,
        objective=payload.objective,
        key_results=[kr for kr in payload.key_results if kr.strip()],
        progress_pct=payload.progress_pct,
        status=payload.status,
        career_vision_1y=(payload.career_vision_1y or "").strip() or None,
        career_vision_3y=(payload.career_vision_3y or "").strip() or None,
        skills_to_grow=[s.strip() for s in payload.skills_to_grow if s.strip()],
        roles_to_explore=[s.strip() for s in payload.roles_to_explore if s.strip()],
        support_needed=(payload.support_needed or "").strip() or None,
    )


@router.post("/goals")
async def create_goal(
    payload: GoalPayload,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    goal_id = payload.id or _make_goal_id(auth.member_id, payload.period)
    saved = upsert_goal(auth.member_id, _goal_from_payload(goal_id, auth.member_id, payload))
    return {"goal": saved.model_dump(mode="json")}


@router.put("/goals/{goal_id}")
async def update_goal(
    goal_id: str,
    payload: GoalPayload,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    saved = upsert_goal(auth.member_id, _goal_from_payload(goal_id, auth.member_id, payload))
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


# ---------- AI: Skill Growth Summary ----------


class GrowthGeneratePayload(BaseModel):
    window_days: int = Field(default=GROWTH_DEFAULT_WINDOW, ge=7, le=120)
    force: bool = False


@router.post("/growth-summary")
async def generate_growth_summary(
    payload: GrowthGeneratePayload,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    """Generate (or return cached) Skill Growth Summary for the current member."""
    return await generate_skill_growth(
        auth.member_id,
        window_days=payload.window_days,
        force=payload.force,
    )


@router.get("/growth-summary")
async def latest_growth_summary(
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    """Return today's cached summary (without spending tokens)."""
    cached = latest_growth_summary_fn(auth.member_id)
    if cached is None:
        return {"member_id": auth.member_id, "summary": None, "from_cache": False}
    return cached


@router.get("/growth-summary/history")
async def list_growth_history(
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    return {"items": list_growth_summaries(auth.member_id)}


@router.get("/growth-summary/{key:path}")
async def get_growth_summary_by_key(
    key: str,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    found = get_growth_by_key(auth.member_id, key)
    if found is None:
        raise HTTPException(status_code=404, detail="summary not found")
    return found


# ---------- Agent Memory (EM-scoped) ----------


class FocusPayload(BaseModel):
    member_id: str
    reason: str = ""


class PreferencesPayload(BaseModel):
    patch: dict


@router.get("/memory")
async def get_agent_memory(auth: AuthContext = Depends(get_auth_context)) -> dict:
    """Return the EM's shared memory document (focus members / topics / prefs)."""
    return agent_memory.get_memory(auth.member_id)


@router.post("/memory/focus")
async def add_memory_focus(
    payload: FocusPayload,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    return agent_memory.add_focus_member(
        auth.member_id, member_id=payload.member_id, reason=payload.reason
    )


@router.delete("/memory/focus/{member_id}")
async def remove_memory_focus(
    member_id: str,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    return agent_memory.remove_focus_member(auth.member_id, member_id=member_id)


@router.post("/memory/preferences")
async def update_memory_preferences(
    payload: PreferencesPayload,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    return agent_memory.update_preferences(auth.member_id, patch=payload.patch)
