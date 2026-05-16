"""Goal Alignment Coach (M4) API — detect OKR drift."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import AuthContext, get_auth_context, require_em
from app.services.goal_alignment import check_alignment

router = APIRouter()


async def _em_only(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    return await require_em(auth)


@router.get("/alignment/{member_id}")
async def alignment(
    member_id: str,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    """Members see their own alignment; EM can see anyone."""
    if auth.role != "em" and auth.member_id != member_id:
        raise HTTPException(status_code=403, detail="cannot view other members")
    return await check_alignment(member_id)


@router.get("/alignment")
async def alignment_all(_: AuthContext = Depends(_em_only)) -> dict:
    """Org-wide alignment overview. EM only."""
    return await check_alignment(member_id=None)
