"""Daily Pulse (M2) services — daily report draft + EM team summary.

Team summaries are persisted to Cosmos via `artefact_store` so that:
- Repeated views by any EM return the same generated summary instantly.
- Summaries survive container restarts and replicas.
- The user can choose to regenerate (force=True) and overwrite.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import timedelta

from app.agents.reporter_agent import (
    draft_member_daily,
    summarize_day,
    summarize_range,
)
from app.services.artefact_store import (
    delete_artefact,
    get_artefact,
    list_artefacts,
    save_artefact,
)
from app.services.data_loader import DataLoader

ARTEFACT_KIND = "team-summary"
ARTEFACT_KIND_RANGE = "team-summary-range"

# Soft caps so a runaway request can't sweep an entire year of reports.
RANGE_MAX_DAYS = 31
RANGE_MAX_REPORTS = 250


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


# ---------------- Range summary (multi-day trend) ----------------


def _range_key(start: date_type, end: date_type) -> str:
    """Stable cache key for a (start, end) pair, e.g. '2026-05-13_2026-05-19'."""
    return f"{start.isoformat()}_{end.isoformat()}"


def _validate_range(start: date_type, end: date_type) -> None:
    if end < start:
        raise ValueError("end_date must be on or after start_date")
    span = (end - start).days + 1
    if span > RANGE_MAX_DAYS:
        raise ValueError(
            f"range too large: {span} days (max {RANGE_MAX_DAYS})"
        )


def _collect_range_reports(
    start: date_type, end: date_type, loader: DataLoader
) -> list:
    """Daily reports from `start` to `end` inclusive, oldest first."""
    reports = []
    current = start
    while current <= end:
        reports.extend(loader.daily_reports_on(current))
        current += timedelta(days=1)
    reports.sort(key=lambda r: (r.report_date, r.member_id))
    return reports


async def summarize_team_range(
    start_date: date_type,
    end_date: date_type,
    loader: DataLoader,
    *,
    force: bool = False,
) -> dict:
    """Return a Cosmos-persisted range trend summary, generating when missing."""
    _validate_range(start_date, end_date)
    key = _range_key(start_date, end_date)

    if not force:
        cached = get_artefact(ARTEFACT_KIND_RANGE, key)
        if cached is not None:
            members = {m.id: m.name for m in loader.load_profiles()}
            return {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "report_count": cached.get("report_count", 0),
                "member_count": cached.get("member_count", 0),
                "summary": _rewrite_range_member_ids_to_names(
                    cached["payload"], members
                ),
                "generated_at": cached.get("generated_at"),
                "from_cache": True,
            }

    reports = _collect_range_reports(start_date, end_date, loader)
    if len(reports) > RANGE_MAX_REPORTS:
        raise ValueError(
            f"too many reports in range: {len(reports)} (max {RANGE_MAX_REPORTS})"
        )

    members = {m.id: m.name for m in loader.load_profiles()}
    member_count = len({r.member_id for r in reports})
    payload = [
        {
            "member_name": members.get(r.member_id, r.member_id),
            "member_id": r.member_id,
            "report_date": r.report_date.isoformat(),
            "yesterday": r.yesterday,
            "today": r.today,
            "blockers": r.blockers,
        }
        for r in reports
    ]
    summary = await summarize_range(payload, members)
    summary = _rewrite_range_member_ids_to_names(summary, members)
    saved = save_artefact(
        ARTEFACT_KIND_RANGE,
        key,
        summary,
        extra={
            "report_count": len(reports),
            "member_count": member_count,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "model": "gpt-4o",
        },
    )
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "report_count": len(reports),
        "member_count": member_count,
        "summary": summary,
        "generated_at": saved.get("generated_at"),
        "from_cache": False,
    }


async def list_team_range_summaries(*, limit: int = 30) -> list[dict]:
    rows = list_artefacts(ARTEFACT_KIND_RANGE, limit=limit)
    return [
        {
            "key": r.get("key"),
            "start_date": r.get("start_date"),
            "end_date": r.get("end_date"),
            "generated_at": r.get("generated_at"),
            "report_count": r.get("report_count"),
            "member_count": r.get("member_count"),
            "model": r.get("model"),
        }
        for r in rows
    ]


def discard_team_range_summary(start_date: date_type, end_date: date_type) -> bool:
    return delete_artefact(ARTEFACT_KIND_RANGE, _range_key(start_date, end_date))


def _rewrite_range_member_ids_to_names(
    summary: dict, members: dict[str, str]
) -> dict:
    """Same intent as the single-day rewriter, but covers the range schema's
    by_member dict and the member_name field inside each risk_signals[] entry."""
    if not isinstance(summary, dict):
        return summary

    by_member = summary.get("by_member")
    if isinstance(by_member, dict):
        summary["by_member"] = {
            members.get(k, k): v for k, v in by_member.items()
        }

    risks = summary.get("risk_signals")
    if isinstance(risks, list):
        for item in risks:
            if isinstance(item, dict) and "member_name" in item:
                item["member_name"] = members.get(
                    item["member_name"], item["member_name"]
                )

    return summary


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
