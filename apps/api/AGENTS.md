# Scoped Agent Instructions: FastAPI Backend (`apps/api/`)

This directory contains the central REST API gateway and database connection lifecycle for ArogyaRakshak.

## Architectural Guidelines for `apps/api/`

1. **Versioned Route Structure**:
   - All REST endpoints are mounted under `/api/v1` via `app/api/v1/api.py`.
   - Each module gets its own endpoint file in `app/api/v1/endpoints/<module>.py`.
   - Never add business logic directly inside endpoint handlers. Call into the domain logic functions in `packages/<module>`.

2. **Database & Async Sessions**:
   - The API uses asynchronous SQLAlchemy (`asyncpg` driver).
   - Inject the database session into route handlers using FastAPI's dependency injection:
     ```python
     from app.database import get_db
     from sqlalchemy.ext.asyncio import AsyncSession
     from fastapi import Depends

     @router.get("/example")
     async def example_route(db: AsyncSession = Depends(get_db)):
         ...
     ```
   - All persistent tables must be defined in `app/models.py`.

3. **Server-Sent Events (SSE) Streaming**:
   - Long-running document audits must stream status updates using `StreamingResponse` with media type `text/event-stream`.
   - Reference implementation: `app/api/v1/endpoints/kadi.py` (`/api/v1/kadi/cases/{case_id}/stream`).

4. **Testing Requirements**:
   - Tests live in `apps/api/tests/`.
   - Use `FastAPI.testclient.TestClient` or `httpx.AsyncClient`.
   - Execute tests with:
     ```bash
     cd apps/api
     python -m pytest
     ```
