"""
NetSec Compliance Auditor — FastAPI Application Entry Point

Registers all routers, configures CORS, startup/shutdown lifecycle,
and the /health endpoint.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database.mongo import close_mongo_client
from app.database.postgres import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize DB tables. Shutdown: close MongoDB client."""
    await init_db()
    yield
    await close_mongo_client()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI-Driven Multi-Vendor Network Security Compliance Auditor. "
        "Parses Cisco, Palo Alto, Junos, and SONiC configs, normalizes to a "
        "universal schema, checks against CIS/NIST/STIG frameworks, and "
        "generates actionable PDF remediation reports."
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
from app.auth.router import router as auth_router
from app.ingestion.router import router as ingestion_router
from app.ai_engine.router import router as ai_router
from app.compliance.router import router as compliance_router
from app.remediation.router import router as remediation_router
from app.reporting.router import router as reporting_router

API_PREFIX = "/api/v1"

app.include_router(auth_router,        prefix=API_PREFIX)
app.include_router(ingestion_router,   prefix=API_PREFIX)
app.include_router(ai_router,          prefix=API_PREFIX)
app.include_router(compliance_router,  prefix=API_PREFIX)
app.include_router(remediation_router, prefix=API_PREFIX)
app.include_router(reporting_router,   prefix=API_PREFIX)


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/", tags=["System"])
async def root():
    return {"message": f"Welcome to {settings.app_name}", "docs": "/api/docs"}
