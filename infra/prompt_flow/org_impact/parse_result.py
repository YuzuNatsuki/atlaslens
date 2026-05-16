"""Prompt Flow node — assemble the final dict from upstream JSON strings."""

from __future__ import annotations

import json
import re

from promptflow.core import tool


def _loose_json(text: str, default):
    if not text:
        return default
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return default


@tool
def parse(
    comms_raw: str,
    knowledge_raw: str,
    workload_raw: str,
    synthesis_raw: str,
) -> dict:
    comms = _loose_json(comms_raw, default=[])
    knowledge = _loose_json(knowledge_raw, default=[])
    workload = _loose_json(workload_raw, default=[])
    synthesis = _loose_json(synthesis_raw, default={})

    return {
        "summary": synthesis.get("summary", ""),
        "overall_risk_level": synthesis.get("overall_risk_level", "medium"),
        "communication_impacts": comms if isinstance(comms, list) else [],
        "knowledge_risks": knowledge if isinstance(knowledge, list) else [],
        "workload_shifts": workload if isinstance(workload, list) else [],
        "timeline_recommendation": synthesis.get("timeline_recommendation", []),
    }
