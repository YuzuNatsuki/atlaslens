"""ASGI middleware that records sensitive HTTP requests into the audit log.

Selective by design: we don't audit every health probe / static fetch.
Instead we whitelist *patterns* that touch member data, admin actions, or
AI generations. Auth is parsed best-effort from the ``Authorization`` header;
unauthenticated requests still record under ``actor_id=anonymous`` so brute
force probes are visible.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.audit import (
    ACTION_AI_ASSISTANT,
    ACTION_AI_GENERATE,
    ACTION_MUTATE,
    ACTION_VIEW,
    record_event,
)
from app.core.auth import decode_token

log = logging.getLogger(__name__)


# Regex → (action, target_kind). Order matters: first match wins.
_RULES: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"^/api/auth/login$"), "login_attempt", "auth"),  # status decides
    (re.compile(r"^/api/admin(/.*)?$"), ACTION_MUTATE, "admin"),
    (re.compile(r"^/api/chat(/.*)?$"), ACTION_AI_ASSISTANT, "chat"),
    (re.compile(r"^/api/members/[^/]+/insights$"), ACTION_AI_GENERATE, "member-insights"),
    (re.compile(r"^/api/members/[^/]+$"), ACTION_VIEW, "member"),
    (re.compile(r"^/api/members$"), ACTION_VIEW, "members"),
    (re.compile(r"^/api/daily-pulse/team-summary"), ACTION_AI_GENERATE, "team-summary"),
    (re.compile(r"^/api/me/growth-summary"), ACTION_AI_GENERATE, "growth-summary"),
    (re.compile(r"^/api/simulator/.*"), ACTION_AI_GENERATE, "org-simulator"),
    (re.compile(r"^/api/one-on-ones/.*"), ACTION_VIEW, "one-on-one"),
]


def _match(path: str) -> tuple[str, str] | None:
    for pattern, action, target_kind in _RULES:
        if pattern.match(path):
            return action, target_kind
    return None


def _extract_actor(request: Request) -> tuple[str, str | None, str | None]:
    """Pull actor_id / email / role out of the Bearer token if present.
    Falls back to anonymous when the header is missing or the token is bogus."""
    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("bearer "):
        return "anonymous", None, None
    token = header.split(None, 1)[1].strip()
    try:
        ctx = decode_token(token)
        return ctx.member_id, ctx.email, ctx.role
    except Exception:  # noqa: BLE001
        return "anonymous", None, None


def _target_id_from_path(path: str) -> str | None:
    """Best-effort extraction of an entity id (mem001, em001, gXX, …)."""
    parts = [p for p in path.split("/") if p]
    for i, p in enumerate(parts):
        if p in {"members", "me", "goals", "one-on-ones"} and i + 1 < len(parts):
            next_part = parts[i + 1]
            if next_part not in {"insights", "growth-summary", "history", "draft-minutes", "records", "packet"}:
                return next_part
    return None


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        match = _match(request.url.path)
        if match is None or request.method == "OPTIONS":
            return await call_next(request)

        action, target_kind = match
        actor_id, actor_email, actor_role = _extract_actor(request)
        try:
            response: Response = await call_next(request)
            status = response.status_code
        except Exception:
            # Still record that a sensitive endpoint blew up, then re-raise.
            record_event(
                actor_id=actor_id,
                actor_email=actor_email,
                actor_role=actor_role,
                action=action,
                target_kind=target_kind,
                target_id=_target_id_from_path(request.url.path),
                path=request.url.path,
                method=request.method,
                status_code=500,
            )
            raise

        # Differentiate login success/failure so admins can scan brute force.
        effective_action = action
        if action == "login_attempt":
            from app.core.audit import ACTION_LOGIN, ACTION_LOGIN_FAILED

            effective_action = ACTION_LOGIN if status < 400 else ACTION_LOGIN_FAILED

        try:
            record_event(
                actor_id=actor_id,
                actor_email=actor_email,
                actor_role=actor_role,
                action=effective_action,
                target_kind=target_kind,
                target_id=_target_id_from_path(request.url.path),
                path=request.url.path,
                method=request.method,
                status_code=status,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("audit middleware: record failed: %s", exc)

        return response


def install(app, *, skip_paths: Iterable[str] | None = None) -> None:
    """Helper to install the middleware on a FastAPI app."""
    app.add_middleware(AuditLogMiddleware)
