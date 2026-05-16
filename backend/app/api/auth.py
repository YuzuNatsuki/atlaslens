"""Auth API — email/password login + current user introspection."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import (
    AuthContext,
    authenticate,
    create_access_token,
    get_auth_context,
)
from app.services.data_loader import DataLoader

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user: dict


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    auth = authenticate(payload.email, payload.password)
    if auth is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid email or password",
        )
    token, expires_at = create_access_token(auth)
    loader = DataLoader()
    profile = loader.get_profile(auth.member_id)
    return LoginResponse(
        access_token=token,
        expires_at=expires_at.isoformat(),
        user={
            "email": auth.email,
            "name": auth.name,
            "member_id": auth.member_id,
            "role": auth.role,
            "profile": profile.model_dump(mode="json") if profile else None,
        },
    )


@router.get("/me")
async def me(auth: AuthContext = Depends(get_auth_context)) -> dict:
    loader = DataLoader()
    profile = loader.get_profile(auth.member_id)
    return {
        "email": auth.email,
        "name": auth.name,
        "identity_provider": auth.identity_provider,
        "member_id": auth.member_id,
        "role": auth.role,
        "profile": profile.model_dump(mode="json") if profile else None,
    }
