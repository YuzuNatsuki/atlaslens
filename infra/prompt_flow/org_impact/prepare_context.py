"""Prompt Flow node — build a compact context string for downstream LLM nodes."""

from __future__ import annotations

import json

from promptflow.core import tool


@tool
def prepare(
    change: dict,
    members: list,
    collaboration_pairs: list,
    shared_skills: dict,
) -> str:
    """Pack the inputs into a single JSON string the LLM nodes can read."""
    payload = {
        "proposed_change": change,
        "members": members,
        "collaboration_pairs": collaboration_pairs,
        "shared_skills": shared_skills,
    }
    return json.dumps(payload, ensure_ascii=False, default=str)
