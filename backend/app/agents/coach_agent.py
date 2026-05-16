"""Coach Agent — uses Azure OpenAI (under the Foundry resource)."""

from __future__ import annotations

import json

from app.core.azure_clients import chat_complete

COACH_SYSTEM_PROMPT = """\
You are AtlasLens "Coach". Return a strict JSON object for an EM's 1on1 prep.
Use these EXACT keys and shapes — no extras, no synonyms:

{
  "opening_check_in": "<<= 140 chars Japanese opener>",
  "discussion_topics":         [{"text": "<<= 140 chars Japanese topic with the question to ask>", "evidence": ["<source id>"]}],
  "growth_questions":          [{"text": "<<= 140 chars Japanese question>",                       "evidence": ["<source id>"]}],
  "blockers_to_surface":       [{"text": "<<= 140 chars Japanese (blocker + question)>",           "evidence": ["<source id>"]}],
  "follow_ups_from_last_time": [{"text": "<<= 140 chars Japanese follow-up status check>",         "evidence": ["<source id>"]}]
}

Constraints:
- AT MOST 3 items per array.
- Stay behavioural. Never infer emotion. Surface only what shows up in the data.
- Output Japanese for all `text` values.
"""


async def build_one_on_one_packet(context: dict) -> dict:
    user_prompt = (
        "Member context follows. Return the JSON described in the system prompt.\n\n"
        + json.dumps(context, ensure_ascii=False, default=str)
    )
    raw = await chat_complete(
        messages=[
            {"role": "system", "content": COACH_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
        max_tokens=1100,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw, "parse_error": True}


MINUTES_SYSTEM_PROMPT = """\
You are AtlasLens "Coach" turning raw 1on1 notes into structured minutes.
Return a strict JSON object — exact keys, no extras, all values in Japanese:

{
  "summary": "<<= 200 chars summary>",
  "key_topics": ["<<= 60 chars>", ...],
  "decisions":  ["<<= 80 chars>", ...],
  "todos":      [{"task": "...", "owner": "<name|EM>", "due": "YYYY-MM-DD|null"}],
  "follow_ups_for_next_time": ["<<= 80 chars>", ...]
}

Stay strictly factual — do not invent content that isn't in the notes.
"""


async def draft_minutes(raw_notes: str, em_id: str, member_id: str) -> dict:
    user_prompt = (
        f"EM id: {em_id}\nMember id: {member_id}\n\n"
        "Convert the following raw notes into the JSON described in the system prompt.\n\n"
        "RAW NOTES:\n" + raw_notes
    )
    raw = await chat_complete(
        messages=[
            {"role": "system", "content": MINUTES_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
        max_tokens=800,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw, "parse_error": True}
