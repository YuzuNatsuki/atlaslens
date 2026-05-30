"""Admin API — full org + member management. Admin role only."""

from __future__ import annotations

import secrets
from datetime import date as date_type

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import AuthContext, get_auth_context, require_admin
from app.models.schemas import Department, Division, MemberProfile, Role, Team
from app.services import admin_dashboard, cosmos_repo, org_repo
from app.services.seed_migration import force_reseed_from_files

router = APIRouter()


async def _admin_only(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    return await require_admin(auth)


# ---------- Dashboard ----------


@router.get("/dashboard")
async def get_dashboard(_: AuthContext = Depends(_admin_only)) -> dict:
    """Aggregated KPIs (members, daily reports, 1on1, OKR, AI generations)."""
    return admin_dashboard.compute_dashboard()


# ---------- Force re-seed (refresh demo / sample data into Cosmos) ----------


class ReseedPayload(BaseModel):
    # Comma-separated scope, e.g. "daily_reports,goals" or "all".
    scope: str = Field(default="all", max_length=200)


@router.post("/reseed")
async def reseed_cosmos_from_files(
    payload: ReseedPayload,
    _: AuthContext = Depends(_admin_only),
) -> dict:
    """Force-upsert the bundled file seed (YAML / Markdown) into Cosmos.

    Use after the demo content under ``data/atlascorp/`` has been refreshed
    — ``migrate_if_empty`` only fires on empty containers, so it cannot pick
    up content changes once the system has run once. Existing rows with the
    same id are overwritten; no rows are deleted.
    """
    try:
        result = force_reseed_from_files(payload.scope)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"reseeded": result, "scope": payload.scope}


# ---------- Org tree ----------


@router.get("/org")
async def get_org_tree(_: AuthContext = Depends(_admin_only)) -> dict:
    """Hierarchical view: company → division → department → team."""
    tree = org_repo.org_tree()
    members = cosmos_repo.all_members()
    tree["members"] = [m.model_dump(mode="json") for m in members]
    return tree


class DivisionPayload(BaseModel):
    id: str | None = None
    company_id: str = "atlascorp"
    name: str
    head_member_id: str | None = None


@router.post("/divisions")
async def create_division(
    payload: DivisionPayload, _: AuthContext = Depends(_admin_only)
) -> dict:
    d = Division(
        id=payload.id or org_repo.new_id("div"),
        company_id=payload.company_id,
        name=payload.name,
        head_member_id=payload.head_member_id,
    )
    return {"division": org_repo.upsert_division(d).model_dump(mode="json")}


@router.put("/divisions/{division_id}")
async def update_division(
    division_id: str, payload: DivisionPayload, _: AuthContext = Depends(_admin_only)
) -> dict:
    d = Division(
        id=division_id,
        company_id=payload.company_id,
        name=payload.name,
        head_member_id=payload.head_member_id,
    )
    return {"division": org_repo.upsert_division(d).model_dump(mode="json")}


@router.delete("/divisions/{division_id}")
async def remove_division(
    division_id: str, _: AuthContext = Depends(_admin_only)
) -> dict:
    # Must look up the division first to know its partition key.
    target = next((d for d in org_repo.all_divisions() if d.id == division_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="division not found")
    if not org_repo.delete_division(division_id, target.company_id):
        raise HTTPException(status_code=500, detail="delete failed")
    return {"deleted": division_id}


class DepartmentPayload(BaseModel):
    id: str | None = None
    division_id: str
    name: str
    head_member_id: str | None = None


@router.post("/departments")
async def create_department(
    payload: DepartmentPayload, _: AuthContext = Depends(_admin_only)
) -> dict:
    d = Department(
        id=payload.id or org_repo.new_id("dept"),
        division_id=payload.division_id,
        name=payload.name,
        head_member_id=payload.head_member_id,
    )
    return {"department": org_repo.upsert_department(d).model_dump(mode="json")}


@router.put("/departments/{department_id}")
async def update_department(
    department_id: str,
    payload: DepartmentPayload,
    _: AuthContext = Depends(_admin_only),
) -> dict:
    d = Department(
        id=department_id,
        division_id=payload.division_id,
        name=payload.name,
        head_member_id=payload.head_member_id,
    )
    return {"department": org_repo.upsert_department(d).model_dump(mode="json")}


@router.delete("/departments/{department_id}")
async def remove_department(
    department_id: str, _: AuthContext = Depends(_admin_only)
) -> dict:
    target = next((d for d in org_repo.all_departments() if d.id == department_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="department not found")
    if not org_repo.delete_department(department_id, target.division_id):
        raise HTTPException(status_code=500, detail="delete failed")
    return {"deleted": department_id}


class TeamPayload(BaseModel):
    id: str | None = None
    department_id: str
    name: str
    manager_member_id: str | None = None
    member_ids: list[str] = Field(default_factory=list)


@router.post("/teams")
async def create_team(
    payload: TeamPayload, _: AuthContext = Depends(_admin_only)
) -> dict:
    t = Team(
        id=payload.id or org_repo.new_id("team"),
        department_id=payload.department_id,
        name=payload.name,
        manager_member_id=payload.manager_member_id,
        member_ids=payload.member_ids,
    )
    saved = org_repo.upsert_team(t)
    _sync_member_team_ids(saved)
    return {"team": saved.model_dump(mode="json")}


@router.put("/teams/{team_id}")
async def update_team(
    team_id: str, payload: TeamPayload, _: AuthContext = Depends(_admin_only)
) -> dict:
    t = Team(
        id=team_id,
        department_id=payload.department_id,
        name=payload.name,
        manager_member_id=payload.manager_member_id,
        member_ids=payload.member_ids,
    )
    saved = org_repo.upsert_team(t)
    _sync_member_team_ids(saved)
    return {"team": saved.model_dump(mode="json")}


@router.delete("/teams/{team_id}")
async def remove_team(team_id: str, _: AuthContext = Depends(_admin_only)) -> dict:
    target = next((t for t in org_repo.all_teams() if t.id == team_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="team not found")
    if not org_repo.delete_team(team_id, target.department_id):
        raise HTTPException(status_code=500, detail="delete failed")
    # Detach members whose team_id pointed at this team.
    detached = []
    for m in cosmos_repo.all_members():
        if m.team_id == team_id or m.manages_team_id == team_id:
            updated = m.model_copy(
                update={
                    "team_id": None if m.team_id == team_id else m.team_id,
                    "manages_team_id": None if m.manages_team_id == team_id else m.manages_team_id,
                }
            )
            cosmos_repo.upsert_member(updated)
            detached.append(m.id)
    return {"deleted": team_id, "detached_members": detached}


def _sync_member_team_ids(team: Team) -> None:
    """Keep members.team_id and members.manages_team_id consistent with the team's roster."""
    all_members = cosmos_repo.all_members()
    member_index = {m.id: m for m in all_members}
    new_members = set(team.member_ids)

    # Drop any member who is no longer on this team.
    for m in all_members:
        if m.team_id == team.id and m.id not in new_members:
            cosmos_repo.upsert_member(m.model_copy(update={"team_id": None}))

    # Add new ones.
    for mid in new_members:
        if mid not in member_index:
            continue
        m = member_index[mid]
        if m.team_id != team.id:
            cosmos_repo.upsert_member(m.model_copy(update={"team_id": team.id}))

    # Manager pointer.
    if team.manager_member_id and team.manager_member_id in member_index:
        manager = member_index[team.manager_member_id]
        cosmos_repo.upsert_member(manager.model_copy(update={"manages_team_id": team.id}))


# ---------- Members ----------


class MemberPayload(BaseModel):
    id: str | None = None
    name: str
    role: str = "mid"
    title: str
    joined_at: date_type | None = None
    team_id: str | None = None
    manages_team_id: str | None = None
    is_admin: bool = False
    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    bio: str = ""
    email: str | None = None


# A simple in-memory map for newly issued passwords. Persists per process only.
_recent_passwords: dict[str, str] = {}


def _new_password() -> str:
    return secrets.token_urlsafe(9)


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=10)).decode("utf-8")


@router.get("/members")
async def list_members(_: AuthContext = Depends(_admin_only)) -> dict:
    members = cosmos_repo.all_members()
    return {"members": [m.model_dump(mode="json") for m in members]}


@router.post("/members")
async def create_member(
    payload: MemberPayload, _: AuthContext = Depends(_admin_only)
) -> dict:
    member_id = payload.id or org_repo.new_id("mem")
    pw = _new_password()
    profile = MemberProfile(
        id=member_id,
        name=payload.name,
        role=Role(payload.role),
        title=payload.title,
        joined_at=payload.joined_at or date_type.today(),
        team_id=payload.team_id,
        manages_team_id=payload.manages_team_id,
        is_admin=payload.is_admin,
        skills=payload.skills,
        interests=payload.interests,
        bio=payload.bio,
        email=payload.email,
        password_hash=_hash(pw) if payload.email else None,
    )
    cosmos_repo.upsert_member(profile)
    _recent_passwords[member_id] = pw
    return {
        "member": profile.model_dump(mode="json"),
        "initial_password": pw if payload.email else None,
    }


@router.put("/members/{member_id}")
async def update_member(
    member_id: str, payload: MemberPayload, _: AuthContext = Depends(_admin_only)
) -> dict:
    existing = cosmos_repo.get_member(member_id)
    profile = MemberProfile(
        id=member_id,
        name=payload.name,
        role=Role(payload.role),
        title=payload.title,
        joined_at=payload.joined_at or (existing.joined_at if existing else date_type.today()),
        team_id=payload.team_id,
        manages_team_id=payload.manages_team_id,
        is_admin=payload.is_admin,
        skills=payload.skills,
        interests=payload.interests,
        bio=payload.bio,
        email=payload.email or (existing.email if existing else None),
        password_hash=existing.password_hash if existing else None,
    )
    cosmos_repo.upsert_member(profile)
    return {"member": profile.model_dump(mode="json")}


@router.delete("/members/{member_id}")
async def remove_member(member_id: str, _: AuthContext = Depends(_admin_only)) -> dict:
    # Soft-delete via Cosmos point delete (partition key = id).
    from app.core.cosmos_client import get_container

    try:
        get_container("members").delete_item(item=member_id, partition_key=member_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=f"member not found: {exc}") from exc
    return {"deleted": member_id}


@router.post("/members/{member_id}/reset-password")
async def reset_password(member_id: str, _: AuthContext = Depends(_admin_only)) -> dict:
    """Issue a new initial password. Revealed once in the response."""
    profile = cosmos_repo.get_member(member_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="member not found")
    if not profile.email:
        raise HTTPException(
            status_code=400, detail="member has no email — cannot reset password"
        )
    pw = _new_password()
    _recent_passwords[member_id] = pw
    cosmos_repo.upsert_member(profile.model_copy(update={"password_hash": _hash(pw)}))
    return {"member_id": member_id, "new_password": pw}
