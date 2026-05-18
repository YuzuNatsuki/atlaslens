"""Tool registry the Foundry-hosted Chat agent can invoke autonomously.

Each tool reads from Cosmos / DataLoader (no AI). The Chat agent decides
which to call based on the EM's question, and the chat service returns
both the final reply and a transcript of the tool calls for the UI.
"""

from __future__ import annotations

import json
from datetime import date as date_type
from datetime import datetime, timedelta
from typing import Any

from app.services import cosmos_repo, org_repo
from app.services.data_loader import DataLoader

# ---------- tool implementations ----------


def _loader() -> DataLoader:
    return DataLoader()


def list_team() -> dict:
    """Return every member with id, name, role, title, team_id."""
    return {
        "members": [
            {
                "id": m.id,
                "name": m.name,
                "role": m.role.value,
                "title": m.title,
                "team_id": m.team_id,
                "manages_team_id": m.manages_team_id,
                "skills": m.skills,
            }
            for m in cosmos_repo.all_members()
        ]
    }


def get_member(member_id: str) -> dict:
    """Profile + goals + recent daily reports + last 1on1 for one member."""
    loader = _loader()
    profile = loader.get_profile(member_id)
    if profile is None:
        return {"error": f"member {member_id} not found"}
    goals = loader.load_goals(member_id)
    dailies = loader.load_daily_reports(member_id)
    one_on_ones = loader.load_one_on_ones(member_id)
    return {
        "profile": profile.model_dump(mode="json"),
        "goals": [g.model_dump(mode="json") for g in goals],
        "recent_daily_reports": [
            {
                "date": d.report_date.isoformat(),
                "today": d.today,
                "blockers": d.blockers,
            }
            for d in dailies[-7:]
        ],
        "last_one_on_one": (
            {
                "date": one_on_ones[-1].held_at.date().isoformat(),
                "topics": one_on_ones[-1].topics,
                "notes": one_on_ones[-1].notes,
                "todos": one_on_ones[-1].todos,
            }
            if one_on_ones
            else None
        ),
    }


def find_blockers(days: int = 14) -> dict:
    """Members whose recent daily reports mention blockers."""
    loader = _loader()
    cutoff = date_type.today() - timedelta(days=days)
    out = []
    for m in cosmos_repo.all_members():
        if m.role.value == "em":
            continue
        recent_blockers = [
            {"date": d.report_date.isoformat(), "blocker": d.blockers}
            for d in loader.load_daily_reports(m.id)
            if d.report_date >= cutoff and d.blockers.strip()
        ]
        if recent_blockers:
            out.append(
                {
                    "member_id": m.id,
                    "name": m.name,
                    "blockers": recent_blockers,
                }
            )
    return {"days_window": days, "members_with_blockers": out}


def get_goal_alignment() -> dict:
    """Roll-up of every member's OKR status."""
    members = cosmos_repo.all_members()
    rows = []
    loader = _loader()
    for m in members:
        if m.role.value == "em":
            continue
        for g in loader.load_goals(m.id):
            rows.append(
                {
                    "member_id": m.id,
                    "name": m.name,
                    "goal": g.objective,
                    "status": g.status,
                    "progress_pct": g.progress_pct,
                }
            )
    rows.sort(key=lambda r: (r["status"], r["progress_pct"]))
    return {"goals": rows}


async def get_team_health() -> dict:
    """Same rule-based aggregation as the M6 dashboard, served as a tool."""
    from app.services.team_health import compute_team_health

    return await compute_team_health()


def get_org_tree() -> dict:
    """Company → Division → Department → Team hierarchy."""
    return org_repo.org_tree()


def get_meetings_with(member_id: str, days: int = 30) -> dict:
    """Meetings the given member attended in the last `days`."""
    loader = _loader()
    cutoff = datetime.now() - timedelta(days=days)
    rows = []
    for meeting in loader.load_meetings(member_id=member_id):
        if meeting.held_at < cutoff:
            continue
        rows.append(
            {
                "title": meeting.title,
                "held_at": meeting.held_at.isoformat(),
                "attendees": meeting.attendees,
                "decisions": meeting.decisions,
                "action_items": meeting.action_items,
            }
        )
    return {"meetings": rows}


async def run_org_simulation(description: str, kind: str = "other") -> dict:
    """Run the Org Impact Simulator Prompt Flow on a proposed change."""
    from app.services.org_impact import simulate_change

    change = {"kind": kind, "description": description, "parameters": {}}
    result = await simulate_change(change)
    impact = result.get("impact", {})
    return {
        "summary": impact.get("summary"),
        "overall_risk_level": impact.get("overall_risk_level"),
        "knowledge_risks": impact.get("knowledge_risks"),
        "workload_shifts": impact.get("workload_shifts"),
    }


# ---------- registry ----------


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_team",
            "description": "全メンバー一覧を返す。誰がいるかを確認するときに使う。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_member",
            "description": "1 人のメンバーのプロフィール、OKR、直近の日報、最終 1on1 を取得。",
            "parameters": {
                "type": "object",
                "properties": {
                    "member_id": {"type": "string", "description": "例: mem001"},
                },
                "required": ["member_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_blockers",
            "description": "最近の日報でブロッカーを書いたメンバーを列挙。",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "default": 14},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_goal_alignment",
            "description": "全メンバーの OKR ステータスをまとめる。遅れているもの順。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_team_health",
            "description": "チームの行動指標（日報提出率、ブロッカー数、会議数、1on1 経過日数）を返す。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_org_tree",
            "description": "事業部→課→チームの階層と各層の管理者を返す。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_meetings_with",
            "description": "指定メンバーが参加した直近の会議。",
            "parameters": {
                "type": "object",
                "properties": {
                    "member_id": {"type": "string"},
                    "days": {"type": "integer", "default": 30},
                },
                "required": ["member_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_org_simulation",
            "description": "体制変更案 (description) の影響を Prompt Flow で予測。Simulator を呼ぶ。",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "変更内容の自然文"},
                    "kind": {
                        "type": "string",
                        "enum": [
                            "split_team",
                            "merge_teams",
                            "move_member",
                            "change_manager",
                            "promote",
                            "hire",
                            "other",
                        ],
                        "default": "other",
                    },
                },
                "required": ["description"],
            },
        },
    },
]


TOOL_HANDLERS = {
    "list_team": list_team,
    "get_member": get_member,
    "find_blockers": find_blockers,
    "get_goal_alignment": get_goal_alignment,
    "get_team_health": get_team_health,
    "get_org_tree": get_org_tree,
    "get_meetings_with": get_meetings_with,
    "run_org_simulation": run_org_simulation,
}


async def dispatch(tool_name: str, arguments: dict | str) -> str:
    """Execute a tool by name and return a JSON string.

    Tools may be sync or async; we await coroutines transparently.
    """
    import inspect

    handler = TOOL_HANDLERS.get(tool_name)
    if handler is None:
        return json.dumps({"error": f"unknown tool: {tool_name}"})
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {}
    try:
        result = handler(**(arguments or {}))
        if inspect.isawaitable(result):
            result = await result
    except TypeError as exc:
        return json.dumps({"error": f"bad arguments for {tool_name}: {exc}"})
    return json.dumps(result, ensure_ascii=False, default=str)
