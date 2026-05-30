"""Migrate the bundled file-based seed into Cosmos on first run.

Idempotent: each container is seeded only if it is empty.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from app.core.config import get_settings
from app.core.cosmos_client import count_items, ensure_all_containers
from app.models.schemas import (
    DailyReport,
    Goal,
    MeetingMinute,
    MemberProfile,
    OneOnOne,
    Role,
)
from app.services import cosmos_repo, org_repo
from app.services.data_loader import (
    _parse_daily_markdown,
    _parse_meeting_markdown,
    _parse_one_on_one_markdown,
)

log = logging.getLogger(__name__)


def _data_dir() -> Path:
    return get_settings().data_dir


def _file_profiles() -> list[MemberProfile]:
    profiles: list[MemberProfile] = []
    members_dir = _data_dir() / "members"
    if not members_dir.exists():
        return profiles
    for path in sorted(members_dir.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        raw["role"] = Role(raw["role"])
        profiles.append(MemberProfile(**raw))
    return profiles


def _file_goals(member_id: str) -> list[Goal]:
    path = _data_dir() / "goals" / f"{member_id}.yaml"
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [Goal(**item) for item in raw]


def _file_daily(member_id: str) -> list[DailyReport]:
    folder = _data_dir() / "daily_reports" / member_id
    if not folder.exists():
        return []
    reports: list[DailyReport] = []
    for path in sorted(folder.glob("*.md")):
        r = _parse_daily_markdown(path, member_id)
        if r is not None:
            reports.append(r)
    return reports


def _file_one_on_ones(member_id: str) -> list[OneOnOne]:
    folder = _data_dir() / "one_on_ones" / member_id
    if not folder.exists():
        return []
    items: list[OneOnOne] = []
    for path in sorted(folder.glob("*.md")):
        o = _parse_one_on_one_markdown(path, member_id)
        if o is not None:
            items.append(o)
    return items


def _file_meetings() -> list[MeetingMinute]:
    folder = _data_dir() / "meetings"
    if not folder.exists():
        return []
    items: list[MeetingMinute] = []
    for path in sorted(folder.glob("*.md")):
        m = _parse_meeting_markdown(path)
        if m is not None:
            items.append(m)
    return items


def migrate_if_empty() -> dict[str, int]:
    ensure_all_containers()
    profiles = _file_profiles()
    result: dict[str, int] = {}

    # Org hierarchy seed (independent of file data)
    if count_items("companies") == 0:
        org_repo.upsert_company(org_repo.SEED_COMPANY)
        result["companies"] = 1
    if count_items("divisions") == 0:
        for d in org_repo.SEED_DIVISIONS:
            org_repo.upsert_division(d)
        result["divisions"] = len(org_repo.SEED_DIVISIONS)
    if count_items("departments") == 0:
        for d in org_repo.SEED_DEPARTMENTS:
            org_repo.upsert_department(d)
        result["departments"] = len(org_repo.SEED_DEPARTMENTS)
    if count_items("teams") == 0:
        for t in org_repo.SEED_TEAMS:
            org_repo.upsert_team(t)
        result["teams"] = len(org_repo.SEED_TEAMS)

    if count_items("members") == 0 and profiles:
        enriched = org_repo.apply_assignments_to(profiles)
        result["members"] = cosmos_repo.bulk_upsert_members(enriched)
        log.info("seeded %d members (with team assignments)", result["members"])
    else:
        # One-shot back-fill: existing members may have been seeded before the
        # org hierarchy existed. Apply assignments if team_id is still null.
        existing = cosmos_repo.all_members()
        if existing and any(m.team_id is None for m in existing):
            enriched = org_repo.apply_assignments_to(existing)
            cosmos_repo.bulk_upsert_members(enriched)
            result["members_patched"] = len(enriched)
            log.info("back-filled team assignments for %d members", len(enriched))

    if count_items("goals") == 0:
        all_goals: list[Goal] = []
        for m in profiles:
            all_goals.extend(_file_goals(m.id))
        if all_goals:
            result["goals"] = cosmos_repo.bulk_upsert_goals(all_goals)
            log.info("seeded %d goals", result["goals"])

    if count_items("daily_reports") == 0:
        all_reports: list[DailyReport] = []
        for m in profiles:
            all_reports.extend(_file_daily(m.id))
        if all_reports:
            result["daily_reports"] = cosmos_repo.bulk_upsert_daily(all_reports)
            log.info("seeded %d daily reports", result["daily_reports"])

    if count_items("one_on_ones") == 0:
        all_one_on_ones: list[OneOnOne] = []
        for m in profiles:
            all_one_on_ones.extend(_file_one_on_ones(m.id))
        if all_one_on_ones:
            result["one_on_ones"] = cosmos_repo.bulk_upsert_one_on_ones(all_one_on_ones)
            log.info("seeded %d one-on-ones", result["one_on_ones"])

    if count_items("meetings") == 0:
        meetings = _file_meetings()
        if meetings:
            result["meetings"] = cosmos_repo.bulk_upsert_meetings(meetings)
            log.info("seeded %d meetings", result["meetings"])

    return result


# Allowed scopes for force_reseed_from_files(). The "all" alias expands to
# everything, so the admin endpoint can just take a free-form string.
_RESEED_SCOPES = {
    "members",
    "goals",
    "daily_reports",
    "one_on_ones",
    "meetings",
}


def force_reseed_from_files(scope: str = "all") -> dict[str, int]:
    """Force-upsert file-based seed data into Cosmos.

    Unlike :func:`migrate_if_empty`, this always upserts: it is meant for
    refreshing demo content after the bundled YAML / Markdown files have
    been updated. Existing rows with the same ``id`` are overwritten; rows
    that no longer exist in the files are left alone (no deletes).

    ``scope`` can be ``"all"`` or a comma-separated list of any of:
    ``members, goals, daily_reports, one_on_ones, meetings``.
    """
    ensure_all_containers()

    requested: set[str]
    if scope.strip().lower() in {"", "all"}:
        requested = set(_RESEED_SCOPES)
    else:
        requested = {p.strip() for p in scope.split(",") if p.strip()}
        unknown = requested - _RESEED_SCOPES
        if unknown:
            raise ValueError(
                f"Unknown reseed scope(s): {sorted(unknown)}. "
                f"Allowed: {sorted(_RESEED_SCOPES) + ['all']}"
            )

    profiles = _file_profiles()
    if not profiles:
        log.warning("force_reseed: no file profiles found, nothing to do")
        return {}

    result: dict[str, int] = {}

    if "members" in requested:
        enriched = org_repo.apply_assignments_to(profiles)
        result["members"] = cosmos_repo.bulk_upsert_members(enriched)
        log.info("force_reseed: upserted %d members", result["members"])

    if "goals" in requested:
        all_goals: list[Goal] = []
        for m in profiles:
            all_goals.extend(_file_goals(m.id))
        if all_goals:
            result["goals"] = cosmos_repo.bulk_upsert_goals(all_goals)
            log.info("force_reseed: upserted %d goals", result["goals"])

    if "daily_reports" in requested:
        all_reports: list[DailyReport] = []
        for m in profiles:
            all_reports.extend(_file_daily(m.id))
        if all_reports:
            result["daily_reports"] = cosmos_repo.bulk_upsert_daily(all_reports)
            log.info(
                "force_reseed: upserted %d daily reports", result["daily_reports"]
            )

    if "one_on_ones" in requested:
        all_one_on_ones: list[OneOnOne] = []
        for m in profiles:
            all_one_on_ones.extend(_file_one_on_ones(m.id))
        if all_one_on_ones:
            result["one_on_ones"] = cosmos_repo.bulk_upsert_one_on_ones(
                all_one_on_ones
            )
            log.info(
                "force_reseed: upserted %d one_on_ones", result["one_on_ones"]
            )

    if "meetings" in requested:
        meetings = _file_meetings()
        if meetings:
            result["meetings"] = cosmos_repo.bulk_upsert_meetings(meetings)
            log.info("force_reseed: upserted %d meetings", result["meetings"])

    return result
