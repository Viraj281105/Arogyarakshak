"""
ArogyaRakshak API — Application entrypoint.

Phase 0: minimal FastAPI app with a health endpoint.
Logs the configured GROQ_MODEL on startup (never calls it).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings

logger = logging.getLogger("arogyarakshak.api")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — runs on startup and shutdown."""
    logger.info("ArogyaRakshak API starting up")
    logger.info("GROQ_MODEL = %s", settings.groq_model)
    logger.info("DATABASE_URL = %s", settings.database_url)
    yield
    logger.info("ArogyaRakshak API shutting down")


app = FastAPI(
    title="ArogyaRakshak API",
    description="Patient-facing bill audit, scheme eligibility & medicine pricing platform.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check endpoint — confirms the API is running."""
    return {"status": "ok"}
