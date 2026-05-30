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

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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


_DEMO_ACCOUNTS = [
    {"member_id": "em001", "email": "tanaka.ken@atlaslens.dev", "name": "田中 健"},
    {"member_id": "mem001", "email": "sato.misaki@atlaslens.dev", "name": "佐藤 美咲"},
    {"member_id": "mem002", "email": "suzuki.ryo@atlaslens.dev", "name": "鈴木 亮"},
    {"member_id": "mem003", "email": "yamamoto.yuka@atlaslens.dev", "name": "山本 由香"},
    {"member_id": "mem004", "email": "watanabe.sho@atlaslens.dev", "name": "渡辺 翔"},
    {"member_id": "mem005", "email": "takahashi.yui@atlaslens.dev", "name": "高橋 結衣"},
]


def _load_credentials() -> dict[str, Credential]:
    """Build the credentials map.

    All three sources are layered (later sources override earlier ones):

      1. `credentials.yaml` next to the seed data (if present)
      2. Hard-coded demo accounts hashed with the env-provided `DEMO_PASSWORD`
      3. Cosmos members whose `email` and `password_hash` are set (admin-managed)

    Keeping all three layered means admin-created accounts work even when the
    seed YAML still sits on disk for local development.
    """
    result: dict[str, Credential] = {}

    # 1. credentials.yaml file (legacy seed)
    path = get_settings().data_dir / "credentials.yaml"
    if path.exists():
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for entry in raw.get("accounts") or []:
            cred = Credential(
                member_id=entry["member_id"],
                email=entry["email"],
                name=entry.get("name", entry["email"]),
                password_hash=entry["password_hash"],
            )
            result[cred.email.lower()] = cred

    # 2. Hard-coded demo accounts (only filled in if not already present).
    #    The password is NEVER baked into the source — it must be supplied via
    #    the DEMO_PASSWORD env var. When unset, demo accounts are skipped so
    #    that the only way in is via real Cosmos-stored credentials.
    password = os.environ.get("DEMO_PASSWORD")
    if password:
        salt = bcrypt.gensalt(rounds=10)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        for acc in _DEMO_ACCOUNTS:
            key = acc["email"].lower()
            if key not in result:
                result[key] = Credential(
                    member_id=acc["member_id"],
                    email=acc["email"],
                    name=acc["name"],
                    password_hash=hashed,
                )

    # 3. Cosmos-managed accounts override everything else.
    try:
        from app.core.cosmos_client import cosmos_configured
        from app.services import cosmos_repo

        if cosmos_configured():
            for m in cosmos_repo.all_members():
                if m.email and m.password_hash:
                    result[m.email.lower()] = Credential(
                        member_id=m.id,
                        email=m.email,
                        name=m.name,
                        password_hash=m.password_hash,
                    )
    except Exception:
        pass

    return result


def _role_for_member(member_id: str) -> str:
    """Effective role for a member, consulting Cosmos members.is_admin when available."""
    try:
        from app.core.cosmos_client import cosmos_configured
        from app.services import cosmos_repo

        if cosmos_configured():
            profile = cosmos_repo.get_member(member_id)
            if profile is not None and profile.is_admin:
                return "admin"
    except Exception:
        pass
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
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_expires_minutes)
    payload: dict[str, Any] = {
        "sub": auth.member_id,
        "email": auth.email,
        "name": auth.name,
        "role": auth.role,
        "exp": int(expires_at.timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
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
    # Admin implicitly satisfies EM permissions.
    if auth.role not in ("em", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="EM access required")
    return auth


async def require_admin(auth: AuthContext) -> AuthContext:
    if auth.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return auth
