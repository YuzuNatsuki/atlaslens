"""Member 360 (M1) — assemble the full view for a single member.

The non-AI portion (profile / goals / daily reports / 1on1s / meetings) is
returned immediately on the main endpoint. AI insights are split into their
own endpoint so the page loads instantly and the EM kicks off the analysis on
demand.
"""

from __future__ import annotations

from app.agents.analyzer_agent import analyze_member
from app.core.cache import cache
from app.services.data_loader import DataLoader


def build_member_view(member_id: str, loader: DataLoader) -> dict:
    """Fast, file/Cosmos-only view — no AI calls."""
    profile = loader.get_profile(member_id)
    if profile is None:
        return {"error": f"profile {member_id} not found"}

    goals = loader.load_goals(member_id)
    daily_reports = loader.load_daily_reports(member_id)
    one_on_ones = loader.load_one_on_ones(member_id)
    meetings = loader.load_meetings(member_id=member_id)

    return {
        "profile": profile.model_dump(mode="json"),
        "goals": [g.model_dump(mode="json") for g in goals],
        "recent_daily_reports": [r.model_dump(mode="json") for r in daily_reports[-7:]],
        "recent_one_on_ones": [o.model_dump(mode="json") for o in one_on_ones[-4:]],
        "recent_meetings": [m.model_dump(mode="json") for m in meetings[-8:]],
    }


async def build_insights(member_id: str, loader: DataLoader) -> dict:
    """AI-driven Analyzer pass. Cached for 10 min."""
    profile = loader.get_profile(member_id)
    if profile is None:
        return {"error": f"profile {member_id} not found"}
    goals = loader.load_goals(member_id)
    daily_reports = loader.load_daily_reports(member_id)
    one_on_ones = loader.load_one_on_ones(member_id)
    return await cache.get_or_compute(
        f"insights:{member_id}",
        lambda: analyze_member(profile, goals, daily_reports, one_on_ones),
    )


# Legacy callers
async def build_member_360(member_id: str, loader: DataLoader) -> dict:
    view = build_member_view(member_id, loader)
    if "error" in view:
        return view
    view["insights"] = await build_insights(member_id, loader)
    return view
