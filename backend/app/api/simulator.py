"""Org Impact Simulator (M5) API — predict impact of structural changes. EM only."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import AuthContext, get_auth_context, require_em
from app.services.org_impact import simulate_change

router = APIRouter()


async def _em_only(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    return await require_em(auth)


class StructureChange(BaseModel):
    kind: str
    description: str
    parameters: dict[str, str | list[str]] = {}


class SimulationRequest(BaseModel):
    change: StructureChange


@router.post("/simulate")
async def simulate(
    payload: SimulationRequest,
    _: AuthContext = Depends(_em_only),
) -> dict:
    return await simulate_change(payload.change.model_dump())
