"""Org Impact Simulator (M5) service.

Primary path: Foundry Prompt Flow (`infra/prompt_flow/org_impact`) — a 5-node
DAG that breaks the analysis into communication, knowledge, workload, and
synthesis nodes. Fallback: direct chat-completion via `simulator_agent.simulate`.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta

from app.agents.simulator_agent import simulate as legacy_simulate
from app.core.cache import cache
from app.services.data_loader import DataLoader
from app.services.prompt_flow_runner import run_org_impact_flow


def _build_org_context(loader: DataLoader) -> dict:
    profiles = loader.load_profiles()
    cutoff = datetime.now() - timedelta(days=30)
    pair_counts: Counter[tuple[str, str]] = Counter()
    for meeting in loader.load_meetings():
        if meeting.held_at < cutoff:
            continue
        attendees = sorted(set(meeting.attendees))
        for i, a in enumerate(attendees):
            for b in attendees[i + 1 :]:
                pair_counts[(a, b)] += 1

    skill_owners: dict[str, list[str]] = {}
    for m in profiles:
        for skill in m.skills:
            skill_owners.setdefault(skill, []).append(m.id)

    return {
        "members": [
            {
                "id": m.id,
                "name": m.name,
                "role": m.role.value,
                "manager_id": m.manager_id,
                "skills": m.skills,
            }
            for m in profiles
        ],
        "collaboration_pairs": [
            {"a": a, "b": b, "shared_meetings_30d": count}
            for (a, b), count in pair_counts.most_common(10)
        ],
        "shared_skills": {
            skill: owners for skill, owners in skill_owners.items() if len(owners) > 1
        },
        "_member_index": {m.id: m.name for m in profiles},
    }


async def _execute(change: dict, org_context: dict) -> dict:
    """Try Prompt Flow first; fall back to the direct LLM agent on any error."""
    flow_inputs = {
        "change": change,
        "members": org_context["members"],
        "collaboration_pairs": org_context["collaboration_pairs"],
        "shared_skills": org_context["shared_skills"],
    }
    try:
        result = await asyncio.to_thread(run_org_impact_flow, flow_inputs)
        if isinstance(result, dict) and result:
            result["_source"] = "prompt_flow"
            return result
    except Exception as exc:  # noqa: BLE001
        # Bubble the failure into the trace, then fall back.
        fallback_org = {
            "members": org_context["members"],
            "collaboration_pairs": org_context["collaboration_pairs"],
            "shared_skills": org_context["shared_skills"],
        }
        result = await legacy_simulate(change=change, org_context=fallback_org)
        if isinstance(result, dict):
            result["_source"] = "fallback_agent"
            result["_prompt_flow_error"] = str(exc)
        return result

    # Empty result from flow → fallback
    fallback_org = {
        "members": org_context["members"],
        "collaboration_pairs": org_context["collaboration_pairs"],
        "shared_skills": org_context["shared_skills"],
    }
    result = await legacy_simulate(change=change, org_context=fallback_org)
    if isinstance(result, dict):
        result["_source"] = "fallback_agent_empty_flow"
    return result


async def simulate_change(change: dict) -> dict:
    loader = DataLoader()
    org_context = _build_org_context(loader)
    member_index = org_context.pop("_member_index")

    cache_key = "sim:" + hashlib.sha1(
        json.dumps(change, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    result = await cache.get_or_compute(
        cache_key,
        lambda: _execute(change, org_context),
    )
    return {"change": change, "impact": result, "members": member_index}
