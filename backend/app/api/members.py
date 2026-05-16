"""Member 360 (M1) API — list members and fetch a full 360 view.

All endpoints in this router require the caller to be an EM. Members should
use the `/api/me/*` endpoints for their own scoped data.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import AuthContext, get_auth_context, require_em
from app.services.data_loader import DataLoader
from app.services.member_view import build_member_360

router = APIRouter()


async def _em_only(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    return await require_em(auth)


@router.get("")
async def list_members(_: AuthContext = Depends(_em_only)) -> dict:
    """List every member in AtlasCorp with light profile data. EM only."""
    loader = DataLoader()
    members = loader.load_profiles()
    return {"members": [m.model_dump(mode="json") for m in members]}


@router.get("/{member_id}")
async def get_member(member_id: str, _: AuthContext = Depends(_em_only)) -> dict:
    """Return the Member 360 view. EM only."""
    loader = DataLoader()
    members = {m.id: m for m in loader.load_profiles()}
    if member_id not in members:
        raise HTTPException(status_code=404, detail=f"member {member_id} not found")

    view = await build_member_360(member_id, loader)
    return view
