"""Daily Pulse (M2) services — daily report draft + EM team summary.

Team summaries are persisted to Cosmos via `artefact_store` so that:
- Repeated views by any EM return the same generated summary instantly.
- Summaries survive container restarts and replicas.
- The user can choose to regenerate (force=True) and overwrite.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import timedelta

from app.agents.reporter_agent import draft_member_daily, summarize_day
from app.services.artefact_store import (
    delete_artefact,
    get_artefact,
    list_artefacts,
    save_artefact,
)
from app.services.data_loader import DataLoader

ARTEFACT_KIND = "team-summary"


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


async def summarize_team_day(
    report_date: date_type,
    loader: DataLoader,
    *,
    force: bool = False,
) -> dict:
    """Return a Cosmos-persisted team summary, or compute one when missing/forced."""
    date_key = report_date.isoformat()
    reports = loader.daily_reports_on(report_date)

    if not force:
        cached = get_artefact(ARTEFACT_KIND, date_key)
        if cached is not None:
            # Old artefacts may have member_id as keys; rewrite on the fly so
            # the UI always shows readable names even before a re-generation.
            members = {m.id: m.name for m in loader.load_profiles()}
            return {
                "date": date_key,
                "report_count": cached.get("report_count", len(reports)),
                "summary": _rewrite_member_ids_to_names(
                    cached["payload"], members
                ),
                "generated_at": cached.get("generated_at"),
                "from_cache": True,
            }

    members = {m.id: m.name for m in loader.load_profiles()}
    payload = [
        {
            # Hand the name through so the LLM never has to do an ID→name
            # lookup. We keep the id around for evidence purposes only.
            "member_name": members.get(r.member_id, r.member_id),
            "member_id": r.member_id,
            "yesterday": r.yesterday,
            "today": r.today,
            "blockers": r.blockers,
        }
        for r in reports
    ]
    summary = await summarize_day(payload, members)
    summary = _rewrite_member_ids_to_names(summary, members)
    saved = save_artefact(
        ARTEFACT_KIND,
        date_key,
        summary,
        extra={"report_count": len(reports), "model": "gpt-4o"},
    )
    return {
        "date": date_key,
        "report_count": len(reports),
        "summary": summary,
        "generated_at": saved.get("generated_at"),
        "from_cache": False,
    }


async def list_team_summaries(*, limit: int = 30) -> list[dict]:
    """Return summary metadata, newest first."""
    rows = list_artefacts(ARTEFACT_KIND, limit=limit)
    return [
        {
            "date": r.get("key"),
            "generated_at": r.get("generated_at"),
            "report_count": r.get("report_count"),
            "model": r.get("model"),
        }
        for r in rows
    ]


def discard_team_summary(report_date: date_type) -> bool:
    return delete_artefact(ARTEFACT_KIND, report_date.isoformat())


def _rewrite_member_ids_to_names(
    summary: dict, members: dict[str, str]
) -> dict:
    """If the LLM accidentally returned member_ids as keys, swap them for
    the human-readable names so the UI always shows '田中 健' not 'mem001'."""
    if not isinstance(summary, dict):
        return summary
    for section in ("highlights", "blockers_to_surface"):
        body = summary.get(section)
        if not isinstance(body, dict):
            continue
        rewritten: dict[str, object] = {}
        for key, value in body.items():
            new_key = members.get(key, key)
            rewritten[new_key] = value
        summary[section] = rewritten
    return summary
