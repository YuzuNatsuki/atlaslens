"""Pydantic schemas for AtlasLens domain objects.

Data sources are text-only: profiles, goals, daily reports, meetings, 1on1s.
No external SaaS (GitHub/Jira/Slack) integration in MVP.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Role(StrEnum):
    ADMIN = "admin"
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
    team_id: str | None = None
    # Set when this member is the manager of a team — points back to teams.id.
    manages_team_id: str | None = None
    is_admin: bool = False
    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    bio: str = ""
    # Optional fields used by admin-managed accounts. For seed accounts these
    # remain null and login falls back to the shared DEMO_PASSWORD.
    email: str | None = None
    password_hash: str | None = None


# ---------- Organisational hierarchy ----------


class Company(BaseModel):
    id: str
    name: str


class Division(BaseModel):
    id: str
    company_id: str
    name: str
    head_member_id: str | None = None


class Department(BaseModel):
    id: str
    division_id: str
    name: str
    head_member_id: str | None = None


class Team(BaseModel):
    id: str
    department_id: str
    name: str
    manager_member_id: str | None = None
    member_ids: list[str] = Field(default_factory=list)


class Goal(BaseModel):
    """An OKR-style entry tied to a member.

    The classic OKR fields (objective + key_results + progress + status)
    live alongside a "career canvas" — free-text fields shared across the
    team so members can document where they want to head next. The career
    fields are optional, so existing seed data keeps working unchanged.
    """

    id: str
    member_id: str
    period: str  # e.g. "2026-Q2"
    objective: str
    key_results: list[str] = Field(default_factory=list)
    progress_pct: int = 0
    status: str = "on_track"  # on_track / at_risk / off_track / done

    # ---- career canvas (optional, shared format across the org) ----
    career_vision_1y: str | None = None
    career_vision_3y: str | None = None
    skills_to_grow: list[str] = Field(default_factory=list)
    roles_to_explore: list[str] = Field(default_factory=list)
    support_needed: str | None = None  # on_track / at_risk / off_track / done


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
