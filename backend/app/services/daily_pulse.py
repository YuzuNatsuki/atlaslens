"""Daily Pulse (M2) services — daily report draft + EM team summary."""

from __future__ import annotations

from datetime import date as date_type
from datetime import timedelta

from app.agents.reporter_agent import draft_member_daily, summarize_day
from app.core.cache import cache
from app.services.data_loader import DataLoader


async def draft_daily_report(
    member_id: str,
    report_date: date_type,
    bullet_hints: list[str],
) -> dict:
    loader = DataLoader()
    profile = loader.get_profile(member_id)
    if profile is None:
        return {"error": f"member {member_id} not found"}

    history_since = report_date - timedelta(days=5)
    history = loader.load_daily_reports(member_id, since=history_since)
    recent = [
        {
            "date": r.report_date.isoformat(),
            "yesterday": r.yesterday,
            "today": r.today,
            "blockers": r.blockers,
        }
        for r in history
    ]
    draft = await draft_member_daily(
        member_name=profile.name,
        bullet_hints=bullet_hints,
        recent_history=recent,
    )
    return {"member_id": member_id, "date": report_date.isoformat(), "draft": draft}


async def summarize_team_day(report_date: date_type, loader: DataLoader) -> dict:
    reports = loader.daily_reports_on(report_date)
    members = {m.id: m.name for m in loader.load_profiles()}
    payload = [
        {
            "member_id": r.member_id,
            "yesterday": r.yesterday,
            "today": r.today,
            "blockers": r.blockers,
        }
        for r in reports
    ]
    summary = await cache.get_or_compute(
        f"team-summary:{report_date.isoformat()}",
        lambda: summarize_day(payload, members),
    )
    return {
        "date": report_date.isoformat(),
        "report_count": len(reports),
        "summary": summary,
    }
