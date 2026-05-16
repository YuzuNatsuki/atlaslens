"""Cosmos-backed repositories for each AtlasLens entity.

All write paths persist to Cosmos. Read paths query Cosmos as the source of
truth. A separate migration step seeds Cosmos from the bundled YAML/MD files
on first run; the previous file-system "store" services delegate here so the
existing API surface keeps working unchanged.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date as date_type
from datetime import datetime
from typing import Any

from app.core.cosmos_client import get_container
from app.models.schemas import (
    DailyReport,
    Goal,
    MeetingMinute,
    MemberProfile,
    OneOnOne,
    Role,
)


def _jsonify(value: Any) -> Any:
    """Make Pydantic objects + dates JSON-friendly for Cosmos."""
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if isinstance(value, date_type):
        return value.isoformat()
    return value


def _normalize(doc: dict) -> dict:
    """Strip Cosmos-internal fields and coerce nested dates back to plain values."""
    return {k: v for k, v in doc.items() if not k.startswith("_")}


# ---------- members ----------


def upsert_member(profile: MemberProfile) -> None:
    container = get_container("members")
    body = profile.model_dump(mode="json")
    container.upsert_item(body)


def all_members() -> list[MemberProfile]:
    items = list(
        get_container("members").read_all_items()
    )
    out: list[MemberProfile] = []
    for raw in items:
        clean = _normalize(raw)
        clean["role"] = Role(clean["role"])
        out.append(MemberProfile(**{k: v for k, v in clean.items() if k in MemberProfile.model_fields}))
    out.sort(key=lambda m: m.id)
    return out


def get_member(member_id: str) -> MemberProfile | None:
    try:
        raw = get_container("members").read_item(item=member_id, partition_key=member_id)
    except Exception:
        return None
    clean = _normalize(raw)
    clean["role"] = Role(clean["role"])
    return MemberProfile(**{k: v for k, v in clean.items() if k in MemberProfile.model_fields})


# ---------- goals ----------


def upsert_goal(goal: Goal) -> Goal:
    container = get_container("goals")
    container.upsert_item(goal.model_dump(mode="json"))
    return goal


def list_goals_for(member_id: str) -> list[Goal]:
    container = get_container("goals")
    items = container.query_items(
        query="SELECT * FROM c WHERE c.member_id = @mid",
        parameters=[{"name": "@mid", "value": member_id}],
        partition_key=member_id,
    )
    out = [Goal(**{k: v for k, v in _normalize(i).items() if k in Goal.model_fields}) for i in items]
    out.sort(key=lambda g: g.id)
    return out


def delete_goal(member_id: str, goal_id: str) -> bool:
    container = get_container("goals")
    try:
        container.delete_item(item=goal_id, partition_key=member_id)
        return True
    except Exception:
        return False


# ---------- daily reports ----------


def upsert_daily(report: DailyReport) -> DailyReport:
    container = get_container("daily_reports")
    container.upsert_item(report.model_dump(mode="json"))
    return report


def list_daily_for(member_id: str, *, since: date_type | None = None) -> list[DailyReport]:
    container = get_container("daily_reports")
    items = container.query_items(
        query="SELECT * FROM c WHERE c.member_id = @mid",
        parameters=[{"name": "@mid", "value": member_id}],
        partition_key=member_id,
    )
    out: list[DailyReport] = []
    for raw in items:
        clean = _normalize(raw)
        report = DailyReport(**{k: v for k, v in clean.items() if k in DailyReport.model_fields})
        if since and report.report_date < since:
            continue
        out.append(report)
    out.sort(key=lambda r: r.report_date)
    return out


def daily_on_date(report_date: date_type) -> list[DailyReport]:
    container = get_container("daily_reports")
    items = container.query_items(
        query="SELECT * FROM c WHERE c.report_date = @d",
        parameters=[{"name": "@d", "value": report_date.isoformat()}],
        enable_cross_partition_query=True,
    )
    out = [
        DailyReport(**{k: v for k, v in _normalize(i).items() if k in DailyReport.model_fields})
        for i in items
    ]
    out.sort(key=lambda r: r.member_id)
    return out


# ---------- one-on-ones ----------


def upsert_one_on_one(record: OneOnOne) -> OneOnOne:
    container = get_container("one_on_ones")
    container.upsert_item(record.model_dump(mode="json"))
    return record


def list_one_on_ones_for(member_id: str) -> list[OneOnOne]:
    container = get_container("one_on_ones")
    items = container.query_items(
        query="SELECT * FROM c WHERE c.member_id = @mid",
        parameters=[{"name": "@mid", "value": member_id}],
        partition_key=member_id,
    )
    out = [OneOnOne(**{k: v for k, v in _normalize(i).items() if k in OneOnOne.model_fields}) for i in items]
    out.sort(key=lambda o: o.held_at)
    return out


# ---------- meetings ----------


def upsert_meeting(meeting: MeetingMinute) -> MeetingMinute:
    container = get_container("meetings")
    container.upsert_item(meeting.model_dump(mode="json"))
    return meeting


def list_meetings(member_id: str | None = None) -> list[MeetingMinute]:
    container = get_container("meetings")
    if member_id:
        items = container.query_items(
            query="SELECT * FROM c WHERE ARRAY_CONTAINS(c.attendees, @mid)",
            parameters=[{"name": "@mid", "value": member_id}],
            enable_cross_partition_query=True,
        )
    else:
        items = container.read_all_items()
    out = [
        MeetingMinute(**{k: v for k, v in _normalize(i).items() if k in MeetingMinute.model_fields})
        for i in items
    ]
    out.sort(key=lambda m: m.held_at)
    return out


# ---------- prep notes ----------


def get_prep_for(member_id: str) -> dict | None:
    container = get_container("prep_notes")
    try:
        raw = container.read_item(item=member_id, partition_key=member_id)
    except Exception:
        return None
    return _normalize(raw)


def upsert_prep(member_id: str, notes: str) -> dict:
    container = get_container("prep_notes")
    payload = {
        "id": member_id,
        "member_id": member_id,
        "notes": notes,
        "updated_at": date_type.today().isoformat(),
    }
    container.upsert_item(payload)
    return payload


# ---------- bulk seeding ----------


def bulk_upsert_members(profiles: Iterable[MemberProfile]) -> int:
    n = 0
    for p in profiles:
        upsert_member(p)
        n += 1
    return n


def bulk_upsert_goals(goals: Iterable[Goal]) -> int:
    n = 0
    for g in goals:
        upsert_goal(g)
        n += 1
    return n


def bulk_upsert_daily(reports: Iterable[DailyReport]) -> int:
    n = 0
    for r in reports:
        upsert_daily(r)
        n += 1
    return n


def bulk_upsert_one_on_ones(items: Iterable[OneOnOne]) -> int:
    n = 0
    for o in items:
        upsert_one_on_one(o)
        n += 1
    return n


def bulk_upsert_meetings(items: Iterable[MeetingMinute]) -> int:
    n = 0
    for m in items:
        upsert_meeting(m)
        n += 1
    return n
