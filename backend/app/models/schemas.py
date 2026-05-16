"""Pydantic schemas for AtlasLens domain objects.

Data sources are text-only: profiles, goals, daily reports, meetings, 1on1s.
No external SaaS (GitHub/Jira/Slack) integration in MVP.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Role(StrEnum):
    EM = "em"
    TECH_LEAD = "tech_lead"
    SENIOR = "senior"
    MID = "mid"
    JUNIOR = "junior"


class MemberProfile(BaseModel):
    """A team member's static profile information."""

    id: str
    name: str
    role: Role
    title: str
    joined_at: date
    manager_id: str | None = None
    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    bio: str = ""


class Goal(BaseModel):
    """An OKR or MBO entry tied to a member."""

    id: str
    member_id: str
    period: str  # e.g. "2026-Q2"
    objective: str
    key_results: list[str]
    progress_pct: int = 0
    status: str = "on_track"  # on_track / at_risk / off_track / done


class DailyReport(BaseModel):
    """A self-authored daily report."""

    id: str
    member_id: str
    report_date: date
    yesterday: str
    today: str
    blockers: str = ""
    mood: int | None = None  # 1-5 self-rated, optional


class MeetingMinute(BaseModel):
    """Generic meeting minute."""

    id: str
    title: str
    held_at: datetime
    attendees: list[str]  # member ids
    agenda: list[str] = Field(default_factory=list)
    notes: str
    decisions: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)


class OneOnOne(BaseModel):
    """A 1on1 record between EM and a member."""

    id: str
    em_id: str
    member_id: str
    held_at: datetime
    topics: list[str]
    notes: str
    todos: list[str] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)


class KnowledgeRecord(BaseModel):
    """Unified record stored in the Knowledge Store (Cosmos / AI Search)."""

    id: str
    source_type: str  # profile / goal / daily / meeting / 1on1
    member_ids: list[str]
    timestamp: datetime
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)
    embedding: list[float] | None = None
