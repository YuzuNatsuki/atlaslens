"""Goal Alignment Coach (M4) — detect drift between OKRs and recent activity."""

from __future__ import annotations

import json

from app.core.azure_clients import chat_complete
from app.services.data_loader import DataLoader

ALIGNMENT_SYSTEM_PROMPT = """\
You are AtlasLens "Goal Alignment Coach". Given a member's OKRs and recent
daily reports + 1on1 notes, judge whether their day-to-day work is aligned.

Rules:
- Be evidence-driven: cite specific daily report dates as evidence.
- Output JSON with keys per goal: status (aligned/at_risk/drifting), reasoning,
  evidence, next_suggested_actions.
- Add an `overall` key summarising alignment for this member.
- Conservative: prefer at_risk over drifting unless evidence is strong.
"""


async def _alignment_for(member_id: str, loader: DataLoader) -> dict:
    profile = loader.get_profile(member_id)
    if profile is None:
        return {"member_id": member_id, "error": "not found"}
    goals = loader.load_goals(member_id)
    daily_reports = loader.load_daily_reports(member_id)
    one_on_ones = loader.load_one_on_ones(member_id)
    if not goals:
        return {"member_id": member_id, "skipped": "no goals defined"}

    payload = {
        "member": profile.model_dump(mode="json"),
        "goals": [g.model_dump(mode="json") for g in goals],
        "recent_daily_reports": [
            d.model_dump(mode="json") for d in daily_reports[-14:]
        ],
        "recent_one_on_ones": [
            o.model_dump(mode="json") for o in one_on_ones[-3:]
        ],
    }
    raw = await chat_complete(
        messages=[
            {"role": "system", "content": ALIGNMENT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Judge alignment as JSON.\n\n"
                + json.dumps(payload, ensure_ascii=False, default=str),
            },
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    try:
        analysis = json.loads(raw)
    except json.JSONDecodeError:
        analysis = {"raw": raw, "parse_error": True}
    return {"member_id": member_id, "analysis": analysis}


async def check_alignment(member_id: str | None) -> dict:
    loader = DataLoader()
    if member_id:
        return await _alignment_for(member_id, loader)

    profiles = loader.load_profiles()
    results = []
    for m in profiles:
        if not loader.load_goals(m.id):
            continue
        results.append(await _alignment_for(m.id, loader))
    return {"members": results}
