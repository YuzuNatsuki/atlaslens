"""Cosmos-backed repository for the org hierarchy (Company → Division → Department → Team)."""

from __future__ import annotations

import uuid

from app.core.cosmos_client import get_container
from app.models.schemas import Company, Department, Division, MemberProfile, Role, Team


def _strip(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if not k.startswith("_")}


def _filter_fields(doc: dict, model: type) -> dict:
    return {k: v for k, v in _strip(doc).items() if k in model.model_fields}


# ---------- read ----------


def all_companies() -> list[Company]:
    return [
        Company(**_filter_fields(d, Company))
        for d in get_container("companies").read_all_items()
    ]


def all_divisions() -> list[Division]:
    return [
        Division(**_filter_fields(d, Division))
        for d in get_container("divisions").read_all_items()
    ]


def all_departments() -> list[Department]:
    return [
        Department(**_filter_fields(d, Department))
        for d in get_container("departments").read_all_items()
    ]


def all_teams() -> list[Team]:
    return [
        Team(**_filter_fields(d, Team))
        for d in get_container("teams").read_all_items()
    ]


# ---------- write ----------


def upsert_company(c: Company) -> Company:
    get_container("companies").upsert_item(c.model_dump(mode="json"))
    return c


def upsert_division(d: Division) -> Division:
    get_container("divisions").upsert_item(d.model_dump(mode="json"))
    return d


def upsert_department(d: Department) -> Department:
    get_container("departments").upsert_item(d.model_dump(mode="json"))
    return d


def upsert_team(t: Team) -> Team:
    get_container("teams").upsert_item(t.model_dump(mode="json"))
    return t


def delete_division(division_id: str, company_id: str) -> bool:
    try:
        get_container("divisions").delete_item(item=division_id, partition_key=company_id)
        return True
    except Exception:
        return False


def delete_department(department_id: str, division_id: str) -> bool:
    try:
        get_container("departments").delete_item(item=department_id, partition_key=division_id)
        return True
    except Exception:
        return False


def delete_team(team_id: str, department_id: str) -> bool:
    try:
        get_container("teams").delete_item(item=team_id, partition_key=department_id)
        return True
    except Exception:
        return False


# ---------- composite views ----------


def org_tree() -> dict:
    companies = all_companies()
    divisions = all_divisions()
    departments = all_departments()
    teams = all_teams()

    teams_by_dept: dict[str, list[dict]] = {}
    for t in teams:
        teams_by_dept.setdefault(t.department_id, []).append(t.model_dump(mode="json"))

    depts_by_div: dict[str, list[dict]] = {}
    for d in departments:
        depts_by_div.setdefault(d.division_id, []).append(
            {**d.model_dump(mode="json"), "teams": teams_by_dept.get(d.id, [])}
        )

    divs_by_company: dict[str, list[dict]] = {}
    for d in divisions:
        divs_by_company.setdefault(d.company_id, []).append(
            {**d.model_dump(mode="json"), "departments": depts_by_div.get(d.id, [])}
        )

    return {
        "companies": [
            {**c.model_dump(mode="json"), "divisions": divs_by_company.get(c.id, [])}
            for c in companies
        ]
    }


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ---------- seed (called from seed_migration) ----------


SEED_COMPANY = Company(id="atlascorp", name="AtlasCorp")

SEED_DIVISIONS = [
    Division(id="div-platform", company_id="atlascorp", name="Platform 本部", head_member_id="em001"),
    Division(id="div-product",  company_id="atlascorp", name="Product 本部"),
]

SEED_DEPARTMENTS = [
    Department(id="dept-sre",       division_id="div-platform", name="SRE 課",        head_member_id="mem001"),
    Department(id="dept-backend",   division_id="div-platform", name="Backend 課",    head_member_id="mem002"),
    Department(id="dept-frontend",  division_id="div-product",  name="Frontend 課",   head_member_id="mem003"),
    Department(id="dept-onboarding",division_id="div-product",  name="新卒育成 課",   head_member_id="em001"),
]

SEED_TEAMS = [
    Team(id="team-sre",       department_id="dept-sre",        name="SRE Team",            manager_member_id="mem001", member_ids=["mem001"]),
    Team(id="team-payment",   department_id="dept-backend",    name="Payment Team",        manager_member_id="mem002", member_ids=["mem002"]),
    Team(id="team-design-sys",department_id="dept-frontend",   name="Design System Team",  manager_member_id="mem003", member_ids=["mem003"]),
    Team(id="team-newgrad",   department_id="dept-onboarding", name="新卒 Team",            manager_member_id="em001",  member_ids=["mem004"]),
]


# member_id → (team_id, manages_team_id_or_none)
MEMBER_ASSIGNMENTS: dict[str, dict[str, str | None | bool]] = {
    "em001":  {"team_id": "team-newgrad",    "manages_team_id": "team-newgrad",   "is_admin": True},
    "mem001": {"team_id": "team-sre",        "manages_team_id": "team-sre",       "is_admin": False},
    "mem002": {"team_id": "team-payment",    "manages_team_id": "team-payment",   "is_admin": False},
    "mem003": {"team_id": "team-design-sys", "manages_team_id": "team-design-sys","is_admin": False},
    "mem004": {"team_id": "team-newgrad",    "manages_team_id": None,             "is_admin": False},
}


def apply_assignments_to(profiles: list[MemberProfile]) -> list[MemberProfile]:
    out: list[MemberProfile] = []
    for p in profiles:
        a = MEMBER_ASSIGNMENTS.get(p.id, {})
        if not a:
            out.append(p)
            continue
        out.append(
            MemberProfile(
                **{
                    **p.model_dump(),
                    "role": Role(p.role.value),
                    "team_id": a.get("team_id"),
                    "manages_team_id": a.get("manages_team_id"),
                    "is_admin": bool(a.get("is_admin", False)),
                }
            )
        )
    return out
