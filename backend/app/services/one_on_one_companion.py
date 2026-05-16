"""1on1 Companion (M3) services — pre-1on1 packet + minutes drafting."""

from __future__ import annotations

from app.agents.coach_agent import build_one_on_one_packet, draft_minutes
from app.core.cache import cache
from app.services.data_loader import DataLoader


async def prepare_one_on_one_packet(member_id: str, loader: DataLoader) -> dict:
    profile = loader.get_profile(member_id)
    if profile is None:
        return {"error": f"member {member_id} not found"}

    goals = loader.load_goals(member_id)
    daily_reports = loader.load_daily_reports(member_id)
    one_on_ones = loader.load_one_on_ones(member_id)

    last_one_on_one = one_on_ones[-1] if one_on_ones else None
    context = {
        "member": {
            "id": profile.id,
            "name": profile.name,
            "role": profile.role.value,
            "title": profile.title,
            "skills": profile.skills,
        },
        "goals": [
            {"id": g.id, "objective": g.objective, "status": g.status, "progress_pct": g.progress_pct}
            for g in goals
        ],
        "recent_daily_reports": [
            {
                "id": r.id,
                "date": r.report_date.isoformat(),
                "yesterday": r.yesterday,
                "today": r.today,
                "blockers": r.blockers,
            }
            for r in daily_reports[-7:]
        ],
        "previous_one_on_one": (
            {
                "id": last_one_on_one.id,
                "held_at": last_one_on_one.held_at.isoformat(),
                "topics": last_one_on_one.topics,
                "notes": last_one_on_one.notes,
                "todos": last_one_on_one.todos,
                "follow_ups": last_one_on_one.follow_ups,
            }
            if last_one_on_one
            else None
        ),
    }
    packet = await cache.get_or_compute(
        f"1on1packet:{member_id}",
        lambda: build_one_on_one_packet(context),
    )
    return {"member_id": member_id, "context": context, "packet": packet}


async def draft_minutes_from_notes(
    em_id: str,
    member_id: str,
    raw_notes: str,
) -> dict:
    structured = await draft_minutes(raw_notes=raw_notes, em_id=em_id, member_id=member_id)
    return {
        "em_id": em_id,
        "member_id": member_id,
        "structured": structured,
    }
