"""
ArogyaRakshak API — Application Entrypoint.

Main application initialization with CORS configuration, global error handlers,
lifespan hooks, and versioned routing.
"""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.background import register_dependency_overrides
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.case_retention import run_retention_sweep_loop
from app.config import settings
from app.database import AsyncSessionLocal, engine, Base, get_db
from app.api.v1.api import api_router
from app.observability import RequestContextMiddleware, configure_logging, route_template, warm_route_templates
from app.rate_limit import limiter, resolve_client_ip
from app import schema
from app.services import document_jobs

logger = logging.getLogger("arogyarakshak.api")
configure_logging(settings.log_format, settings.log_level, settings.app_env)

# Paths that must answer even when a client is rate limited (orchestrator probes).
PROBE_PATHS = {"/health", "/health/live", "/health/ready"}

# Outcome of the start-up schema step, reported by /health/ready.
schema_state = {"ok": False, "revision": None, "detail": "not checked yet"}


def enforce_production_profile() -> None:
    """APP_ENV=production refuses to start with development defaults (see
    Settings.production_config_errors). Raising here stops uvicorn before it serves."""
    if not settings.is_production:
        return
    errors = settings.production_config_errors()
    for message in errors:
        logger.critical("Refusing to start under APP_ENV=production: %s", message)
    if errors:
        raise RuntimeError(f"{len(errors)} production configuration error(s); see the log above.")


async def apply_schema() -> None:
    """ADR-020: migrations are the schema's source of truth; see app.schema for modes."""
    mode = settings.schema_management
    try:
        if mode == "migrate":
            revision = await asyncio.to_thread(schema.upgrade_to_head, settings.database_url)
            schema_state.update(ok=True, revision=revision, detail="migrated to head")
        elif mode == "none":
            revision = await asyncio.to_thread(schema.current_revision, settings.database_url)
            head = schema.head_revision()
            ok = revision == head
            schema_state.update(ok=ok, revision=revision, detail="at head" if ok else f"behind code (head {head})")
            if not ok:
                logger.error("Database schema is at %s but the code expects %s. Run `alembic upgrade head`.", revision, head)
        else:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            schema_state.update(ok=True, revision=None, detail="create_all (legacy, unversioned)")
        logger.info("Database schema: %s (%s).", schema_state["detail"], mode)
    except Exception as e:
        schema_state.update(ok=False, revision=None, detail="schema step failed")
        logger.error("Database schema step (%s) failed: %s", mode, e)


def redact_database_url(url: str) -> str:
    """The connection URL with its password replaced by ***."""
    from sqlalchemy.engine import make_url

    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        return "<unparseable DATABASE_URL>"


def uses_default_database_credentials(url: str) -> bool:
    """True when DATABASE_URL still carries docker-compose.yml's fallback dev
    credentials (arogyarakshak:arogyarakshak) — a critical, silent misconfiguration if
    it reaches a real deployment (P0-5)."""
    return "arogyarakshak:arogyarakshak@" in url


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — runs database creation and logs startup configuration."""
    logger.info("ArogyaRakshak API starting up...")
    enforce_production_profile()
    logger.info("GROQ_MODEL = %s", settings.groq_model)
    # The URL embeds the database password; log it masked.
    logger.info("DATABASE_URL = %s", redact_database_url(settings.database_url))

    # P0-5: the well-known default dev credentials (docker-compose.yml's fallback)
    # reaching a real deployment would be a critical, silent misconfiguration —
    # surfaced loudly at startup rather than left to be discovered later.
    # P2: DOCUMENT_SIGNING_SECRET signs the appeal PDF's integrity HMAC
    # (billnyay.tools.pdf_integrity) — a real, checkable secret whose default value was
    # never flagged at startup the way the database/CORS defaults are.
    if settings.document_signing_secret == "dev-insecure-signing-secret-change-in-production":
        logger.warning(
            "DOCUMENT_SIGNING_SECRET is using the insecure development default. This is "
            "fine for local development only — set DOCUMENT_SIGNING_SECRET to a strong, "
            "unique value before any deployment reachable outside your own machine, or "
            "anyone can forge a valid-looking signature for a tampered appeal PDF."
        )

    if settings.clinical_demo_mode:
        logger.warning(
            "CLINICAL_DEMO_MODE is ON: demo reviewers can be seeded with DEMO_VERIFIED status "
            "and demo safety rules. Never enable this in a real deployment."
        )
    if not settings.clinical_governance_admin_key:
        logger.info(
            "CLINICAL_GOVERNANCE_ADMIN_KEY is not set: safety-board seating, verification "
            "attempts and demo seeding are disabled."
        )

    if uses_default_database_credentials(settings.database_url):
        logger.warning(
            "DATABASE_URL uses the default development credentials "
            "(arogyarakshak:arogyarakshak). This is fine for local development only — "
            "set POSTGRES_PASSWORD (and DATABASE_URL) to a strong, unique value before "
            "any deployment reachable outside your own machine."
        )

    if settings.groq_api_key:
        logger.info("GROQ_API_KEY is configured — LLM-backed extraction and drafting enabled.")
    else:
        logger.warning(
            "GROQ_API_KEY is NOT configured. Running in DEGRADED mode: Kadi entity "
            "extraction falls back to regex heuristics and BillNyay appeal letters are "
            "templated rather than LLM-drafted. Set GROQ_API_KEY in .env to enable "
            "full functionality."
        )

    await apply_schema()

    # ADR-019: this is the only API process (single replica), so any job still queued or
    # processing belonged to a process that died. Report it as interrupted.
    if schema_state["ok"]:
        try:
            async with AsyncSessionLocal() as session:
                marked = await document_jobs.mark_interrupted_jobs(session)
            if marked:
                logger.warning("Marked %d in-flight document job(s) as interrupted after restart.", marked)
        except Exception as e:
            logger.error("Could not reconcile interrupted document jobs: %s", e)

    # SEC-03: server-side case retention sweep — purges expired cases on its own
    # schedule, independent of any client ever presenting its access token again. See
    # app/case_retention.py.
    logger.info(
        "Case retention: TTL=%d day(s), sweep interval=%ds",
        settings.case_ttl_days, settings.case_purge_interval_seconds,
    )
    # Compile the access-log route templates now rather than on the first request.
    warm_route_templates(app)

    retention_stop_event = asyncio.Event()
    retention_task = asyncio.create_task(run_retention_sweep_loop(retention_stop_event))

    yield

    retention_stop_event.set()
    retention_task.cancel()
    try:
        await retention_task
    except (asyncio.CancelledError, Exception):
        pass
    logger.info("ArogyaRakshak API shutting down...")


app = FastAPI(
    title="ArogyaRakshak API",
    description="Patient-facing bill audit, scheme eligibility & medicine pricing platform.",
    version="1.0.0",
    lifespan=lifespan,
    # The interactive docs load assets from a CDN and advertise every route; not on a
    # production deployment. The OpenAPI contract stays in docs/api/openapi.json.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

# Background sessions honour test dependency overrides without importing this module.
register_dependency_overrides(lambda: app.dependency_overrides)

# --- CORS Middleware ----------------------------------------------------------
# A wildcard origin combined with allow_credentials lets any site issue credentialed
# cross-origin requests. Credentials are therefore enabled only when an explicit origin
# allow-list is configured; the permissive default stays credential-free.
origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
wildcard_origins = not origins or "*" in origins

if wildcard_origins:
    logger.warning(
        "CORS_ORIGINS is a wildcard. Credentialed cross-origin requests are disabled. "
        "Set CORS_ORIGINS to an explicit comma-separated list in production."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if wildcard_origins else origins,
    allow_credentials=not wildcard_origins,
    # P2: was missing PUT and DELETE. SchemeSetu's income-profile route (PUT/DELETE) and
    # the case-deletion route (DELETE /kadi/cases/{id}, ADR-009/P1-10) were both
    # completely unreachable from any browser client — a cross-origin PUT/DELETE sends a
    # CORS preflight OPTIONS request first, and the browser refuses the real request
    # when the preflight response's Access-Control-Allow-Methods doesn't list the method
    # actually being used, independent of anything the route itself does.
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Accept",
        "Authorization",
        "X-Case-Access-Token",
        # ADR-011 bearer credentials (reviewer, institution) and the operator-only
        # governance key. Without these the browser's preflight would block the
        # reviewer workspace and playbook screens entirely.
        "X-Reviewer-Token",
        "X-Institution-Token",
        "X-Governance-Admin-Key",
    ],
)


# --- Rate Limiting Middleware ---------------------------------------------------
# See app/rate_limit.py for why this exists (no authentication) and its scope
# limitation (single-process, in-memory).

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in PROBE_PATHS:
        return await call_next(request)

    client_key = resolve_client_ip(request)
    allowed, retry_after = limiter.check(client_key)
    if not allowed:
        logger.warning("Rate limit exceeded for client %s on %s", client_key, route_template(request))
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Rate limit exceeded. Please slow down and try again shortly.",
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )
    return await call_next(request)


# Outermost: every response (including CORS preflights and 429s) gets a request id and
# the hardening headers, and every request one access-log line (app/observability.py).
app.add_middleware(RequestContextMiddleware)


# --- Global Exception Handlers ------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Catches and formats Pydantic validation errors."""
    # Location/type/message only: Pydantic's `input` would copy submitted values (names,
    # incomes, free text) into the log. The client still gets the full errors.
    logger.error(
        "Validation error on %s: %s",
        route_template(request),
        [{k: e.get(k) for k in ("loc", "type", "msg")} for e in exc.errors()],
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": exc.errors(), "message": "Request validation failed"},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Catches deliberate HTTP errors and returns them unchanged.

    `detail` may be a string or a structured object (e.g. a list of missing fields).
    `message` is only populated for string details — stringifying a dict produced a Python
    repr in the response body.
    """
    logger.warning("HTTP %d error on %s: %s", exc.status_code, route_template(request), exc.detail)
    content = {"detail": exc.detail}
    if isinstance(exc.detail, str):
        content["message"] = exc.detail
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catches unhandled errors without leaking internal detail to the caller.

    The exception text previously went back in the response body, disclosing internal
    function names and parameters (e.g. the Barrister Agent TypeError). It is logged with
    a correlation id instead, so operators can still find it.
    """
    error_id = uuid.uuid4().hex[:12]
    logger.error(
        "Unhandled exception [%s] on %s: %s", error_id, route_template(request), exc, exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected server error occurred.",
            "error_id": error_id,
        },
    )


# --- API Routes ---------------------------------------------------------------
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    """Health check endpoint — confirms the API is running and reports LLM availability.

    `groq_configured` is false when GROQ_API_KEY is unset, meaning extraction and appeal
    drafting are running on offline fallbacks. Operators need this to be visible rather
    than buried in logs.
    """
    return {
        "status": "ok",
        "version": "1.0.0",
        "groq_configured": bool(settings.groq_api_key),
        "groq_model": settings.groq_model,
    }


@app.get("/health/live")
async def health_live():
    """Liveness: the process is up and serving. Never touches the database, so a
    database outage does not get the container restarted in a loop."""
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready(db: AsyncSession = Depends(get_db)):
    """Readiness: the database answers and its schema matches this code. 503 otherwise,
    so an orchestrator stops routing traffic here. Reports booleans and the revision
    only — no hostnames, credentials or error text."""
    database_ok = False
    try:
        await db.execute(text("SELECT 1"))
        database_ok = True
    except Exception as e:
        logger.warning("Readiness: database check failed: %s", type(e).__name__)
    ready = database_ok and bool(schema_state["ok"])
    body = {
        "status": "ready" if ready else "not_ready",
        "database": database_ok,
        "schema": {"ok": bool(schema_state["ok"]), "revision": schema_state["revision"]},
    }
    return JSONResponse(status_code=200 if ready else 503, content=body)
