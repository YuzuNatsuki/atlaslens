"""Team Health Sensor (M6) API — ethical behavioral-signal monitoring.

The sensor only looks at objective work-product signals (report cadence, blocker
mentions, meeting load). It does **not** infer emotion or mental state.
Notifications go to the EM only; AI states facts, not judgments.
"""

from fastapi import APIRouter, Depends

from app.core.auth import AuthContext, get_auth_context, require_em
from app.services.team_health import compute_member_health, compute_team_health

router = APIRouter()


async def _em_only(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    return await require_em(auth)


@router.get("/team")
async def team_health(_: AuthContext = Depends(_em_only)) -> dict:
    """EM-only team health view."""
    return await compute_team_health()


@router.get("/member/{member_id}")
async def member_health(
    member_id: str,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    """Members can see only their own signals. EM can see anyone."""
    if auth.role != "em" and auth.member_id != member_id:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="cannot view other members")
    return await compute_member_health(member_id)
