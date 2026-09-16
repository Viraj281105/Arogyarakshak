"""
ArogyaRakshak API — Application Entrypoint.

Main application initialization with CORS configuration, global error handlers,
lifespan hooks, and versioned routing.
"""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import engine, Base
from app.api.v1.api import api_router
from app.rate_limit import limiter, resolve_client_ip

logger = logging.getLogger("arogyarakshak.api")
logging.basicConfig(level=logging.INFO)


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
    logger.info("GROQ_MODEL = %s", settings.groq_model)
    # The URL embeds the database password; log it masked.
    logger.info("DATABASE_URL = %s", redact_database_url(settings.database_url))

    # P0-5: the well-known default dev credentials (docker-compose.yml's fallback)
    # reaching a real deployment would be a critical, silent misconfiguration —
    # surfaced loudly at startup rather than left to be discovered later.
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

    # Establish connection and create schemas on startup if they do not exist
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schemas verified.")
    except Exception as e:
        logger.error("Failed to verify/create database schemas: %s", e)
        
    yield
    logger.info("ArogyaRakshak API shutting down...")


app = FastAPI(
    title="ArogyaRakshak API",
    description="Patient-facing bill audit, scheme eligibility & medicine pricing platform.",
    version="1.0.0",
    lifespan=lifespan,
)

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
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
)


# --- Rate Limiting Middleware ---------------------------------------------------
# See app/rate_limit.py for why this exists (no authentication) and its scope
# limitation (single-process, in-memory).

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    client_key = resolve_client_ip(request)
    allowed, retry_after = limiter.check(client_key)
    if not allowed:
        logger.warning("Rate limit exceeded for client %s on %s", client_key, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Rate limit exceeded. Please slow down and try again shortly.",
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )
    return await call_next(request)


# --- Global Exception Handlers ------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Catches and formats Pydantic validation errors."""
    logger.error("Validation error on %s: %s", request.url, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "message": "Request validation failed"},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Catches deliberate HTTP errors and returns them unchanged.

    `detail` may be a string or a structured object (e.g. a list of missing fields).
    `message` is only populated for string details — stringifying a dict produced a Python
    repr in the response body.
    """
    logger.warning("HTTP %d error on %s: %s", exc.status_code, request.url, exc.detail)
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
        "Unhandled exception [%s] on %s: %s", error_id, request.url, exc, exc_info=True
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
