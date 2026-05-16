"""Goal storage — Cosmos when configured, file fallback for local seed."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.core.config import get_settings
from app.core.cosmos_client import cosmos_configured
from app.models.schemas import Goal


def list_goals(member_id: str) -> list[Goal]:
    if cosmos_configured():
        from app.services import cosmos_repo

        return cosmos_repo.list_goals_for(member_id)
    return _file_load(member_id)


def upsert_goal(member_id: str, goal: Goal) -> Goal:
    if cosmos_configured():
        from app.services import cosmos_repo

        return cosmos_repo.upsert_goal(goal)
    goals = _file_load(member_id)
    replaced = False
    out: list[Goal] = []
    for existing in goals:
        if existing.id == goal.id:
            out.append(goal)
            replaced = True
        else:
            out.append(existing)
    if not replaced:
        out.append(goal)
    _file_write(member_id, out)
    return goal


def delete_goal(member_id: str, goal_id: str) -> bool:
    if cosmos_configured():
        from app.services import cosmos_repo

        return cosmos_repo.delete_goal(member_id, goal_id)
    goals = _file_load(member_id)
    remaining = [g for g in goals if g.id != goal_id]
    if len(remaining) == len(goals):
        return False
    _file_write(member_id, remaining)
    return True


# ---- file fallback ----


def _path_for(member_id: str) -> Path:
    return get_settings().data_dir / "goals" / f"{member_id}.yaml"


def _file_load(member_id: str) -> list[Goal]:
    path = _path_for(member_id)
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [Goal(**item) for item in raw]


def _file_write(member_id: str, goals: list[Goal]) -> None:
    path = _path_for(member_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [g.model_dump(mode="json") for g in goals]
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
