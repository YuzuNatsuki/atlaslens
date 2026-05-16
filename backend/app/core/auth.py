"""JWT-based authentication.

Login flow:
    1. POST /api/auth/login {email, password}
    2. Backend looks the email up in `credentials.yaml`, verifies bcrypt hash
    3. Issues a HS256 JWT (sub=member_id, role=em|member, email, name)
    4. Frontend stores token in localStorage and sends `Authorization: Bearer <jwt>`

Backend dependency `get_auth_context` parses the Bearer token on every request
and returns the resolved `AuthContext`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import bcrypt
import yaml
from fastapi import Header, HTTPException, status
from jose import JWTError, jwt

from app.core.config import get_settings


@dataclass(frozen=True)
class AuthContext:
    email: str
    name: str
    member_id: str
    role: str  # "em" | "member"
    identity_provider: str = "atlaslens"


@dataclass(frozen=True)
class Credential:
    member_id: str
    email: str
    name: str
    password_hash: str


@lru_cache
def _load_credentials() -> dict[str, Credential]:
    """Load credentials.yaml, keyed by lowercase email."""
    path = get_settings().data_dir / "credentials.yaml"
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    result: dict[str, Credential] = {}
    for entry in raw.get("accounts") or []:
        cred = Credential(
            member_id=entry["member_id"],
            email=entry["email"],
            name=entry.get("name", entry["email"]),
            password_hash=entry["password_hash"],
        )
        result[cred.email.lower()] = cred
    return result


def _role_for_member(member_id: str) -> str:
    return "em" if member_id.lower().startswith("em") else "member"


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def authenticate(email: str, password: str) -> AuthContext | None:
    creds = _load_credentials()
    cred = creds.get(email.lower())
    if cred is None:
        return None
    if not verify_password(password, cred.password_hash):
        return None
    return AuthContext(
        email=cred.email,
        name=cred.name,
        member_id=cred.member_id,
        role=_role_for_member(cred.member_id),
    )


def create_access_token(auth: AuthContext) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_minutes)
    payload: dict[str, Any] = {
        "sub": auth.member_id,
        "email": auth.email,
        "name": auth.name,
        "role": auth.role,
        "exp": int(expires_at.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_token(token: str) -> AuthContext:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return AuthContext(
        email=payload.get("email", ""),
        name=payload.get("name", ""),
        member_id=payload["sub"],
        role=payload.get("role", "member"),
    )


async def get_auth_context(
    authorization: str | None = Header(default=None),
) -> AuthContext:
    """Parse `Authorization: Bearer <jwt>` and return the resolved user."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(None, 1)[1].strip()
    return decode_token(token)


async def require_em(auth: AuthContext) -> AuthContext:
    if auth.role != "em":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="EM access required")
    return auth
