"""FastAPI entrypoint for AtlasLens backend."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin,
    auth,
    chat,
    daily_pulse,
    goals,
    health,
    insight_actions,
    me,
    members,
    one_on_ones,
    simulator,
)
from app.core.audit_middleware import AuditLogMiddleware
from app.core.config import get_settings
from app.core.cosmos_client import cosmos_configured
from app.core.tracing import instrument_fastapi, setup_tracing

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_tracing()
    if cosmos_configured():
        try:
            from app.services.seed_migration import migrate_if_empty

            results = migrate_if_empty()
            if results:
                log.info("Cosmos seed migration: %s", results)
            else:
                log.info("Cosmos already seeded — skipped migration")
        except Exception as exc:  # noqa: BLE001
            log.exception("Cosmos bootstrap failed: %s", exc)
    else:
        log.warning("COSMOS_* not configured — running in file-only mode")
    yield


app = FastAPI(
    title="AtlasLens API",
    version="0.1.0",
    description="Team Co-pilot platform — multi-agent Azure backend",
    lifespan=lifespan,
)
instrument_fastapi(app)

# Explicit origins only in production. Override via CORS_ORIGINS (comma-separated).
_default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://orange-pond-02df6f200.7.azurestaticapps.net",
]
_env_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
_origins = _env_origins or _default_origins
_settings = get_settings()
# Allow PR-preview wildcards only in local dev. Production/container envs
# rely on explicit CORS_ORIGINS (set by Terraform with the frontend FQDN).
_cors_origin_regex = (
    r"https://.*\.azurestaticapps\.net|https://.*\.azurecontainerapps\.io"
    if _settings.app_env.lower() == "local"
    else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=_cors_origin_regex,
    # JWT in Authorization header — no cookies, no credentials.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit middleware runs after CORS so OPTIONS preflight doesn't get logged.
app.add_middleware(AuditLogMiddleware)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(me.router, prefix="/api/me", tags=["me"])
app.include_router(members.router, prefix="/api/members", tags=["members"])
app.include_router(one_on_ones.router, prefix="/api/one-on-ones", tags=["one-on-ones"])
app.include_router(daily_pulse.router, prefix="/api/daily-pulse", tags=["daily-pulse"])
app.include_router(simulator.router, prefix="/api/simulator", tags=["simulator"])
app.include_router(goals.router, prefix="/api/goals", tags=["goals"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(
    insight_actions.router, prefix="/api/insight-actions", tags=["insight-actions"]
)
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


@app.get("/")
async def root() -> dict[str, str]:
    return {"app": "AtlasLens", "version": app.version}
