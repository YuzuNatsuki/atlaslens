"""Analyzer Agent — uses Azure OpenAI (deployed under the Foundry resource)."""

from __future__ import annotations

import json

from app.core.azure_clients import chat_complete
from app.models.schemas import DailyReport, Goal, MemberProfile, OneOnOne

ANALYZER_SYSTEM_PROMPT = """\
You are AtlasLens "Analyzer". Read the member context and return a strict JSON
object with these EXACT keys and shapes — no extras, no synonyms:

{
  "highlights":         [{"text": "<<= 120 chars in Japanese", "evidence": ["<source id>"]}],
  "risks":              [{"text": "<<= 120 chars in Japanese", "evidence": ["<source id>"]}],
  "growth_signals":     [{"text": "<<= 120 chars in Japanese", "evidence": ["<source id>"]}],
  "suggested_questions":[{"text": "<<= 100 chars Japanese question", "evidence": ["<source id>"]}]
}

Constraints:
- AT MOST 3 items per array. Pick the most informative.
- `evidence` ids must come from the supplied data (daily-..., 1on1-..., g-..., mtg-...).
- Stay behavioural. Never infer emotion or mental state.
- Output Japanese for `text` values.
"""


async def analyze_member(
    profile: MemberProfile,
    goals: list[Goal],
    daily_reports: list[DailyReport],
    one_on_ones: list[OneOnOne],
) -> dict:
    payload = {
        "profile": {
            "id": profile.id,
            "name": profile.name,
            "role": profile.role.value,
            "title": profile.title,
            "skills": profile.skills,
        },
        "goals": [
            {
                "id": g.id,
                "objective": g.objective,
                "status": g.status,
                "progress_pct": g.progress_pct,
                "key_results": g.key_results,
            }
            for g in goals
        ],
        "recent_daily_reports": [
            {
                "id": d.id,
                "date": d.report_date.isoformat(),
                "yesterday": d.yesterday,
                "today": d.today,
                "blockers": d.blockers,
            }
            for d in daily_reports[-7:]
        ],
        "recent_one_on_ones": [
            {
                "id": o.id,
                "held_at": o.held_at.isoformat(),
                "topics": o.topics,
                "notes": o.notes,
                "todos": o.todos,
            }
            for o in one_on_ones[-2:]
        ],
    }
    user_prompt = (
        "Member context follows. Return the JSON described in the system prompt.\n\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
    )
    raw = await chat_complete(
        messages=[
            {"role": "system", "content": ANALYZER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
        max_tokens=900,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw, "parse_error": True}
