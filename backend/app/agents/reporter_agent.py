"""Reporter Agent — uses Azure OpenAI (under the Foundry resource)."""

from __future__ import annotations

import json

from app.core.azure_clients import chat_complete

DAILY_DRAFT_SYSTEM_PROMPT = """\
You are AtlasLens "Reporter" — drafting a daily report for a team member.
Use the member's stated bullet hints plus the past few days of reports for
context. Output JSON with: yesterday, today, blockers, suggested_mood (1-5).
Keep each section to 2-4 short bullet points, factual and concrete.
Output Japanese.
"""


async def draft_member_daily(
    member_name: str,
    bullet_hints: list[str],
    recent_history: list[dict],
) -> dict:
    payload = {
        "member": member_name,
        "hints": bullet_hints,
        "recent_history": recent_history,
    }
    user_prompt = (
        "Draft today's daily report for this member. Output JSON as specified.\n\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
    )
    raw = await chat_complete(
        messages=[
            {"role": "system", "content": DAILY_DRAFT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
        max_tokens=400,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw, "parse_error": True}


TEAM_SUMMARY_SYSTEM_PROMPT = """\
You are AtlasLens "Reporter" producing an EM-facing summary of one day of team
daily reports. Return a strict JSON object — exact keys, Japanese values:

{
  "tldr": ["<<= 80 chars Japanese bullet>", ...],
  "highlights": {
    "<member name>": "<<= 100 chars Japanese summary of their day>"
  },
  "blockers_to_surface": {
    "<member name>": "<<= 100 chars Japanese blocker description>"
  },
  "themes": ["<<= 80 chars Japanese cross-team theme>", ...]
}

Scannable, specific, no fluff. Output Japanese.
"""


async def summarize_day(reports: list[dict], member_index: dict[str, str]) -> dict:
    payload = {"reports": reports, "members": member_index}
    user_prompt = (
        "Summarize today's team for the EM as JSON.\n\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
    )
    raw = await chat_complete(
        messages=[
            {"role": "system", "content": TEAM_SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
        max_tokens=700,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw, "parse_error": True}
