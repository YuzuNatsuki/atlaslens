"""FastAPI entrypoint for AtlasLens backend."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, daily_pulse, goals, health, me, members, one_on_ones, simulator
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
    description="EM Co-pilot platform — multi-agent Azure backend",
    lifespan=lifespan,
)
instrument_fastapi(app)

# Allow localhost dev + any *.azurestaticapps.net (Static Web Apps default domain).
# Override via CORS_ORIGINS env var if you need a tighter list later.
_default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]
_env_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
_origins = _env_origins or _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"https://.*\.azurestaticapps\.net",
    # JWT in Authorization header — no cookies, no credentials.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(me.router, prefix="/api/me", tags=["me"])
app.include_router(members.router, prefix="/api/members", tags=["members"])
app.include_router(one_on_ones.router, prefix="/api/one-on-ones", tags=["one-on-ones"])
app.include_router(daily_pulse.router, prefix="/api/daily-pulse", tags=["daily-pulse"])
app.include_router(simulator.router, prefix="/api/simulator", tags=["simulator"])
app.include_router(goals.router, prefix="/api/goals", tags=["goals"])
app.include_router(health.router, prefix="/api/health", tags=["health"])


@app.get("/")
async def root() -> dict[str, str]:
    return {"app": "AtlasLens", "version": app.version}
