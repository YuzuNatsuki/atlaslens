"""Aggregated KPIs for the admin dashboard.

Pure read-side aggregation across already-persisted entities. Everything is
fact-only: counts, ratios, and recency, never AI inference. Falls back to the
file-based seed loader when Cosmos is not configured so the dashboard renders
in local dev too.
"""

from __future__ import annotations

from collections import Counter
from datetime import date as date_type
from datetime import datetime, timedelta
from typing import Any

from app.core.cosmos_client import cosmos_configured
from app.services.artefact_store import list_artefacts
from app.services.data_loader import DataLoader

# Windows used by the KPI calculation. Centralised so the UI matches.
DAILY_WINDOW_DAYS = 14
ONE_ON_ONE_WINDOW_DAYS = 30
ONE_ON_ONE_OVERDUE_DAYS = 30


def compute_dashboard() -> dict[str, Any]:
    loader = DataLoader()
    today = date_type.today()
    profiles = loader.load_profiles()

    # ---- members ----
    role_counter: Counter[str] = Counter()
    admin_count = 0
    manager_count = 0
    for p in profiles:
        role_counter[p.role.value] += 1
        if p.is_admin:
            admin_count += 1
        if p.manages_team_id:
            manager_count += 1

    # Anyone whose role is "em" or who manages a team is a manager-like account
    # that should not count against member-level submission ratios.
    em_ids = {p.id for p in profiles if p.role.value == "em"}
    member_facing = [p for p in profiles if p.id not in em_ids]
    member_total = len(member_facing)

    # ---- daily reports ----
    daily_since = today - timedelta(days=DAILY_WINDOW_DAYS)
    submitted_ids: set[str] = set()
    submission_counts: dict[str, int] = {}
    total_daily_in_window = 0
    for p in member_facing:
        reports = [
            r for r in loader.load_daily_reports(p.id, since=daily_since)
        ]
        submission_counts[p.id] = len(reports)
        if reports:
            submitted_ids.add(p.id)
        total_daily_in_window += len(reports)
    submission_rate = (
        len(submitted_ids) / member_total if member_total else 0.0
    )

    # ---- 1on1s ----
    one_on_one_window_start = datetime.combine(
        today - timedelta(days=ONE_ON_ONE_WINDOW_DAYS), datetime.min.time()
    )
    one_on_ones_in_window = 0
    overdue_members: list[dict[str, Any]] = []
    for p in member_facing:
        items = loader.load_one_on_ones(p.id)
        recent = [o for o in items if o.held_at >= one_on_one_window_start]
        one_on_ones_in_window += len(recent)
        last = items[-1].held_at if items else None
        days_since = (
            (datetime.combine(today, datetime.min.time()) - last).days
            if last
            else None
        )
        if days_since is None or days_since >= ONE_ON_ONE_OVERDUE_DAYS:
            overdue_members.append(
                {
                    "member_id": p.id,
                    "name": p.name,
                    "days_since_last": days_since,
                }
            )

    # ---- goals ----
    goal_status: Counter[str] = Counter()
    members_with_goals = 0
    career_canvas_filled = 0
    for p in profiles:
        goals = loader.load_goals(p.id)
        if goals:
            members_with_goals += 1
        for g in goals:
            goal_status[g.status or "unknown"] += 1
            if (
                (g.career_vision_1y and g.career_vision_1y.strip())
                or (g.career_vision_3y and g.career_vision_3y.strip())
                or g.skills_to_grow
            ):
                career_canvas_filled += 1

    # ---- AI generations ----
    ai_artefacts_total = 0
    ai_artefacts_recent: list[dict[str, Any]] = []
    if cosmos_configured():
        for kind in ("team-summary", "skill-growth"):
            rows = list_artefacts(kind, limit=10)
            ai_artefacts_total += len(rows)
            for r in rows[:5]:
                ai_artefacts_recent.append(
                    {
                        "kind": kind,
                        "key": r.get("key"),
                        "generated_at": r.get("generated_at"),
                    }
                )
        ai_artefacts_recent.sort(
            key=lambda r: r.get("generated_at") or "", reverse=True
        )
        ai_artefacts_recent = ai_artefacts_recent[:8]

    return {
        "as_of": today.isoformat(),
        "members": {
            "total": len(profiles),
            "by_role": dict(role_counter),
            "admins": admin_count,
            "team_managers": manager_count,
        },
        "daily_reports": {
            "window_days": DAILY_WINDOW_DAYS,
            "member_total": member_total,
            "members_submitted": len(submitted_ids),
            "submission_rate": round(submission_rate, 3),
            "total_in_window": total_daily_in_window,
        },
        "one_on_ones": {
            "window_days": ONE_ON_ONE_WINDOW_DAYS,
            "held_in_window": one_on_ones_in_window,
            "overdue_count": len(overdue_members),
            "overdue_members": sorted(
                overdue_members,
                key=lambda r: (r["days_since_last"] is None, -(r["days_since_last"] or 0)),
            )[:8],
        },
        "goals": {
            "members_with_goals": members_with_goals,
            "by_status": dict(goal_status),
            "career_canvas_filled": career_canvas_filled,
        },
        "ai": {
            "artefacts_total": ai_artefacts_total,
            "recent": ai_artefacts_recent,
        },
    }
