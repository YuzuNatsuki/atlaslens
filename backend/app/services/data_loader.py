"""Read-side loader.

By default reads from Cosmos. Falls back to the bundled file-based seed if
Cosmos is not configured (local dev without a Cosmos account).
"""

from __future__ import annotations

from datetime import date as date_type, datetime
from pathlib import Path
from typing import Iterable

import yaml

from app.core.config import get_settings
from app.core.cosmos_client import cosmos_configured
from app.models.schemas import (
    DailyReport,
    Goal,
    MeetingMinute,
    MemberProfile,
    OneOnOne,
    Role,
)


class DataLoader:
    """Unified read API used by services + the seed migration."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or get_settings().data_dir
        self._use_cosmos = cosmos_configured()

    # ---------- profiles ----------

    def load_profiles(self) -> list[MemberProfile]:
        if self._use_cosmos:
            from app.services import cosmos_repo

            profiles = cosmos_repo.all_members()
            if profiles:
                return profiles
        # File fallback (used for seeding / local dev)
        return self._file_profiles()

    def _file_profiles(self) -> list[MemberProfile]:
        members_dir = self.data_dir / "members"
        if not members_dir.exists():
            return []
        profiles: list[MemberProfile] = []
        for path in sorted(members_dir.glob("*.yaml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            raw["role"] = Role(raw["role"])
            profiles.append(MemberProfile(**raw))
        return profiles

    def get_profile(self, member_id: str) -> MemberProfile | None:
        if self._use_cosmos:
            from app.services import cosmos_repo

            return cosmos_repo.get_member(member_id) or self._file_profile(member_id)
        return self._file_profile(member_id)

    def _file_profile(self, member_id: str) -> MemberProfile | None:
        path = self.data_dir / "members" / f"{member_id}.yaml"
        if not path.exists():
            return None
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        raw["role"] = Role(raw["role"])
        return MemberProfile(**raw)

    # ---------- goals ----------

    def load_goals(self, member_id: str) -> list[Goal]:
        if self._use_cosmos:
            from app.services import cosmos_repo

            return cosmos_repo.list_goals_for(member_id)
        return self._file_goals(member_id)

    def _file_goals(self, member_id: str) -> list[Goal]:
        path = self.data_dir / "goals" / f"{member_id}.yaml"
        if not path.exists():
            return []
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        return [Goal(**item) for item in raw]

    # ---------- daily reports ----------

    def load_daily_reports(
        self, member_id: str, *, since: date_type | None = None
    ) -> list[DailyReport]:
        if self._use_cosmos:
            from app.services import cosmos_repo

            return cosmos_repo.list_daily_for(member_id, since=since)
        return self._file_daily(member_id, since=since)

    def _file_daily(
        self, member_id: str, *, since: date_type | None = None
    ) -> list[DailyReport]:
        member_dir = self.data_dir / "daily_reports" / member_id
        if not member_dir.exists():
            return []
        reports: list[DailyReport] = []
        for path in sorted(member_dir.glob("*.md")):
            report = _parse_daily_markdown(path, member_id)
            if report is None:
                continue
            if since and report.report_date < since:
                continue
            reports.append(report)
        return reports

    def daily_reports_on(self, report_date: date_type) -> list[DailyReport]:
        if self._use_cosmos:
            from app.services import cosmos_repo

            return cosmos_repo.daily_on_date(report_date)
        results: list[DailyReport] = []
        reports_root = self.data_dir / "daily_reports"
        if not reports_root.exists():
            return []
        for member_dir in sorted(reports_root.iterdir()):
            if not member_dir.is_dir():
                continue
            path = member_dir / f"{report_date.isoformat()}.md"
            if not path.exists():
                continue
            report = _parse_daily_markdown(path, member_dir.name)
            if report is not None:
                results.append(report)
        return results

    # ---------- meetings ----------

    def load_meetings(self, member_id: str | None = None) -> list[MeetingMinute]:
        if self._use_cosmos:
            from app.services import cosmos_repo

            return cosmos_repo.list_meetings(member_id)
        return self._file_meetings(member_id)

    def _file_meetings(self, member_id: str | None) -> list[MeetingMinute]:
        meetings_dir = self.data_dir / "meetings"
        if not meetings_dir.exists():
            return []
        meetings: list[MeetingMinute] = []
        for path in sorted(meetings_dir.glob("*.md")):
            meeting = _parse_meeting_markdown(path)
            if meeting is None:
                continue
            if member_id and member_id not in meeting.attendees:
                continue
            meetings.append(meeting)
        return meetings

    # ---------- 1on1s ----------

    def load_one_on_ones(self, member_id: str) -> list[OneOnOne]:
        if self._use_cosmos:
            from app.services import cosmos_repo

            return cosmos_repo.list_one_on_ones_for(member_id)
        return self._file_one_on_ones(member_id)

    def _file_one_on_ones(self, member_id: str) -> list[OneOnOne]:
        member_dir = self.data_dir / "one_on_ones" / member_id
        if not member_dir.exists():
            return []
        items: list[OneOnOne] = []
        for path in sorted(member_dir.glob("*.md")):
            o = _parse_one_on_one_markdown(path, member_id)
            if o is not None:
                items.append(o)
        return items


# ---------- markdown parsing helpers (used by file fallback + seed) ----------


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            front = yaml.safe_load(text[4:end]) or {}
            body = text[end + 5 :]
            return front, body
    return {}, text


def _parse_daily_markdown(path: Path, member_id: str) -> DailyReport | None:
    text = path.read_text(encoding="utf-8")
    front, body = _parse_frontmatter(text)
    sections = _split_sections(body)
    return DailyReport(
        id=front.get("id", f"daily-{member_id}-{path.stem}"),
        member_id=member_id,
        report_date=_to_date(front.get("date") or path.stem),
        yesterday=sections.get("昨日", sections.get("Yesterday", "")).strip(),
        today=sections.get("今日", sections.get("Today", "")).strip(),
        blockers=sections.get("ブロッカー", sections.get("Blockers", "")).strip(),
        mood=front.get("mood"),
    )


def _parse_meeting_markdown(path: Path) -> MeetingMinute | None:
    text = path.read_text(encoding="utf-8")
    front, body = _parse_frontmatter(text)
    sections = _split_sections(body)
    held_at_raw = front.get("held_at")
    held_at = (
        datetime.fromisoformat(held_at_raw)
        if isinstance(held_at_raw, str)
        else (held_at_raw if isinstance(held_at_raw, datetime) else datetime.now())
    )
    return MeetingMinute(
        id=front.get("id", f"mtg-{path.stem}"),
        title=front.get("title", path.stem),
        held_at=held_at,
        attendees=list(front.get("attendees", [])),
        agenda=list(front.get("agenda", [])),
        notes=sections.get("ノート", sections.get("Notes", body)).strip(),
        decisions=_bullets(sections.get("決定", sections.get("Decisions", ""))),
        action_items=_bullets(sections.get("アクション", sections.get("Actions", ""))),
    )


def _parse_one_on_one_markdown(path: Path, member_id: str) -> OneOnOne | None:
    text = path.read_text(encoding="utf-8")
    front, body = _parse_frontmatter(text)
    sections = _split_sections(body)
    held_at_raw = front.get("held_at")
    held_at = (
        datetime.fromisoformat(held_at_raw)
        if isinstance(held_at_raw, str)
        else (held_at_raw if isinstance(held_at_raw, datetime) else datetime.now())
    )
    return OneOnOne(
        id=front.get("id", f"1on1-{member_id}-{path.stem}"),
        em_id=front.get("em_id", "em001"),
        member_id=member_id,
        held_at=held_at,
        topics=list(front.get("topics", [])),
        notes=sections.get("ノート", sections.get("Notes", body)).strip(),
        todos=_bullets(sections.get("ToDo", sections.get("Todos", ""))),
        follow_ups=_bullets(sections.get("フォローアップ", sections.get("Follow-ups", ""))),
    )


def _split_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = line[3:].strip()
            buf = []
        else:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def _bullets(text: str) -> list[str]:
    return [
        line.lstrip("-* ").strip()
        for line in text.splitlines()
        if line.strip().startswith(("-", "*"))
    ]


def _to_date(value) -> date_type:
    if isinstance(value, date_type):
        return value
    return date_type.fromisoformat(str(value))


def members_by_id(members: Iterable[MemberProfile]) -> dict[str, MemberProfile]:
    return {m.id: m for m in members}
