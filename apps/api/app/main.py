"""
ArogyaRakshak API — Application Entrypoint.

Main application initialization with CORS configuration, global error handlers,
lifespan hooks, and versioned routing.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import engine, Base
from app.api.v1.api import api_router

logger = logging.getLogger("arogyarakshak.api")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — runs database creation and logs startup configuration."""
    logger.info("ArogyaRakshak API starting up...")
    logger.info("GROQ_MODEL = %s", settings.groq_model)
    logger.info("DATABASE_URL = %s", settings.database_url)
    
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
origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    """Catches standard HTTP exceptions."""
    logger.warning("HTTP %d error on %s: %s", exc.status_code, request.url, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "message": str(exc.detail)},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catches unhandled errors to avoid leaking internal trace details."""
    logger.error("Unhandled exception on %s: %s", request.url, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected server error occurred.", "message": str(exc)},
    )


# --- API Routes ---------------------------------------------------------------
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    """Health check endpoint — confirms the API is running."""
    return {"status": "ok", "version": "1.0.0"}
