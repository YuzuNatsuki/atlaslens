"""Team Health Sensor (M6) — ethical, behavioural-only signal monitoring.

We compute objective indicators from text artifacts only:
- Daily report cadence (missed reports in the last 10 working days)
- Blocker mention rate
- Meeting load (number of meetings attended in the last 14 days)
- Recency of last 1on1

The output is presented to the EM as facts, not interpretations. No emotion
or mental-state inference, no per-member ranking, no notifications to the
member.
"""

from __future__ import annotations

from datetime import date as date_type, datetime, timedelta

from app.services.data_loader import DataLoader


def _member_signals(member_id: str, loader: DataLoader, *, today: date_type) -> dict:
    daily_window_start = today - timedelta(days=14)
    daily = [r for r in loader.load_daily_reports(member_id) if r.report_date >= daily_window_start]
    blockers = [r for r in daily if r.blockers.strip()]

    meeting_window_start = datetime.combine(today - timedelta(days=14), datetime.min.time())
    meetings = [
        m for m in loader.load_meetings(member_id=member_id) if m.held_at >= meeting_window_start
    ]

    one_on_ones = loader.load_one_on_ones(member_id)
    last_one_on_one = one_on_ones[-1].held_at if one_on_ones else None
    days_since_last_one_on_one = (
        (datetime.combine(today, datetime.min.time()) - last_one_on_one).days
        if last_one_on_one
        else None
    )

    return {
        "member_id": member_id,
        "daily_reports_last_14d": len(daily),
        "blockers_mentioned_last_14d": len(blockers),
        "meetings_attended_last_14d": len(meetings),
        "days_since_last_one_on_one": days_since_last_one_on_one,
    }


def _flag_facts(signals: dict) -> list[str]:
    facts: list[str] = []
    if signals["daily_reports_last_14d"] <= 5:
        facts.append(
            f"日報の提出が直近14日で{signals['daily_reports_last_14d']}件のみ — 確認推奨"
        )
    if signals["blockers_mentioned_last_14d"] >= 4:
        facts.append(
            f"ブロッカー言及が{signals['blockers_mentioned_last_14d']}件 — 1on1で深掘り推奨"
        )
    if signals["meetings_attended_last_14d"] >= 25:
        facts.append(
            f"会議参加が{signals['meetings_attended_last_14d']}件 — 過負荷の可能性、要確認"
        )
    if (
        signals["days_since_last_one_on_one"] is not None
        and signals["days_since_last_one_on_one"] >= 21
    ):
        facts.append(
            f"前回1on1から{signals['days_since_last_one_on_one']}日経過 — 設定を検討"
        )
    return facts


async def compute_member_health(member_id: str) -> dict:
    loader = DataLoader()
    today = date_type.today()
    signals = _member_signals(member_id, loader, today=today)
    return {**signals, "facts_for_em": _flag_facts(signals)}


async def compute_team_health() -> dict:
    loader = DataLoader()
    today = date_type.today()
    profiles = loader.load_profiles()
    rows = []
    for m in profiles:
        if m.role.value == "em":
            continue
        signals = _member_signals(m.id, loader, today=today)
        signals["name"] = m.name
        signals["facts_for_em"] = _flag_facts(signals)
        rows.append(signals)
    return {"as_of": today.isoformat(), "members": rows}
