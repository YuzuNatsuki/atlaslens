"""Member 360 (M1) — assemble the full view for a single member."""

from __future__ import annotations

from app.agents.analyzer_agent import analyze_member
from app.core.cache import cache
from app.services.data_loader import DataLoader


async def build_member_360(member_id: str, loader: DataLoader) -> dict:
    profile = loader.get_profile(member_id)
    if profile is None:
        return {"error": f"profile {member_id} not found"}

    goals = loader.load_goals(member_id)
    daily_reports = loader.load_daily_reports(member_id)
    one_on_ones = loader.load_one_on_ones(member_id)
    meetings = loader.load_meetings(member_id=member_id)

    insights = await cache.get_or_compute(
        f"insights:{member_id}",
        lambda: analyze_member(profile, goals, daily_reports, one_on_ones),
    )

    return {
        "profile": profile.model_dump(mode="json"),
        "goals": [g.model_dump(mode="json") for g in goals],
        "recent_daily_reports": [r.model_dump(mode="json") for r in daily_reports[-7:]],
        "recent_one_on_ones": [o.model_dump(mode="json") for o in one_on_ones[-4:]],
        "recent_meetings": [m.model_dump(mode="json") for m in meetings[-8:]],
        "insights": insights,
    }
