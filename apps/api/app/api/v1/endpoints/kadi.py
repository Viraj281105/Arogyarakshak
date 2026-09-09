"""
Kadi API Endpoints.

Handles case creation, document uploads (OCR parsing), and entity extraction/retrieval.
"""

from typing import Any, Dict, List, Optional
import uuid
import logging
import json
import asyncio

from contextlib import asynccontextmanager
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db, AsyncSessionLocal
from app.config import settings
from app.models import KadiCase, KadiEntity
# OCR parser and extraction agent from kadi shared layer
from kadi.ocr.ocr_parser import parse_document
from kadi.extraction import extract_entities_from_text

logger = logging.getLogger("arogyarakshak.api.kadi")
router = APIRouter()

# In-memory document processing status stream mapping
processing_status: Dict[str, List[Dict[str, Any]]] = {}


@asynccontextmanager
async def _wrap_session(session: AsyncSession):
    yield session


@asynccontextmanager
async def get_background_session():
    """Context manager for obtaining an async database session in background tasks.
    Honors FastAPI dependency_overrides (e.g. in test suites) and falls back
    to AsyncSessionLocal for local and production/Docker runs."""
    from app.main import app as fastapi_app
    override = fastapi_app.dependency_overrides.get(get_db)
    if override:
        async with asynccontextmanager(override)() as session:
            yield session
    else:
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise



# --- Pydantic Schemas ---------------------------------------------------------
class CaseCreate(BaseModel):
    consent_opt_in: bool = Field(default=False, description="Patient opt-in for cross-module context sharing")


class CaseResponse(BaseModel):
    id: str
    status: str
    consent_opt_in: bool
    total_charged: float
    created_at: Any

    model_config = ConfigDict(from_attributes=True)


class EntityResponse(BaseModel):
    id: str
    name: str
    type: str
    value: Optional[str]
    meta: Optional[Dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)



class CaseDetailResponse(BaseModel):
    case: CaseResponse
    entities: List[EntityResponse]


# --- Async Helper Task --------------------------------------------------------
async def process_document_background(case_id: str, file_bytes: bytes, filename: str, db: Optional[AsyncSession] = None):
    """Processes document upload in a background task, saving extracted entities."""
    logger.info(f"Background task starting: OCR parsing for case={case_id}, file={filename}")
    try:
        # Step 1: OCR parsing
        processing_status[case_id].append({"status": "ocr_start", "progress": 30, "log": "Running document OCR parser..."})
        parsed = parse_document(file_bytes=file_bytes, filename=filename)
        text = parsed.get("full_text_content", "")
        line_items = parsed.get("line_items", [])
        
        # Step 2: Extraction using Kadi shared extraction agent (Groq API or heuristic fallback)
        processing_status[case_id].append({"status": "extraction_start", "progress": 60, "log": "Extracting clinical & billing entities with Kadi agent..."})
        extracted = extract_entities_from_text(text, api_key=settings.groq_api_key, model=settings.groq_model)
        
        # Step 3: Database write using dedicated session
        processing_status[case_id].append({"status": "database_write", "progress": 80, "log": "Saving structured entities to database..."})

        if db is not None and getattr(db, "is_active", False):
            session_cm = _wrap_session(db)
        else:
            session_cm = get_background_session()

        async with session_cm as session:
            result = await session.execute(
                select(KadiCase).options(selectinload(KadiCase.entities)).where(KadiCase.id == case_id)
            )
            case = result.scalar_one_or_none()
            if not case:
                logger.error(f"Case {case_id} not found during background processing.")
                processing_status[case_id].append({"status": "failed", "progress": 100, "log": "Failed: Case not found"})
                return

            entities_to_add: List[KadiEntity] = []
            total_cost = 0.0

            # 1. Billing line items from OCR
            for idx, item in enumerate(line_items):
                entity_id = f"ENT-BILL-{uuid.uuid4().hex[:8]}"
                entity = KadiEntity(
                    id=entity_id,
                    name=item["item"],
                    type="billing_item",
                    value=str(item["charged"]),
                    meta={"charged": item["charged"], "source_file": filename},
                )
                entities_to_add.append(entity)
                total_cost += item["charged"]

            # 2. Structured clinical entities from extraction agent
            if extracted.hospital_name:
                entities_to_add.append(
                    KadiEntity(
                        id=f"ENT-HOSP-{uuid.uuid4().hex[:8]}",
                        name=extracted.hospital_name,
                        type="hospital",
                        value=extracted.hospital_name,
                        meta={"source_file": filename, "source": "kadi_extraction"},
                    )
                )

            if extracted.patient_name:
                entities_to_add.append(
                    KadiEntity(
                        id=f"ENT-PAT-{uuid.uuid4().hex[:8]}",
                        name=extracted.patient_name,
                        type="patient",
                        value=extracted.patient_name,
                        meta={"source_file": filename, "source": "kadi_extraction"},
                    )
                )

            if extracted.diagnosis:
                entities_to_add.append(
                    KadiEntity(
                        id=f"ENT-DIAG-{uuid.uuid4().hex[:8]}",
                        name=extracted.diagnosis,
                        type="diagnosis",
                        value=extracted.diagnosis,
                        meta={"source_file": filename, "source": "kadi_extraction"},
                    )
                )

            for proc in extracted.procedures:
                proc_name = proc.get("name")
                if proc_name and not any(e.name == proc_name for e in entities_to_add):
                    entities_to_add.append(
                        KadiEntity(
                            id=f"ENT-PROC-{uuid.uuid4().hex[:8]}",
                            name=proc_name,
                            type="procedure",
                            value=str(proc.get("amount", 0.0)),
                            meta=proc,
                        )
                    )

            for med in extracted.medicines:
                med_name = med.get("name")
                if med_name:
                    entities_to_add.append(
                        KadiEntity(
                            id=f"ENT-MED-{uuid.uuid4().hex[:8]}",
                            name=med_name,
                            type="medicine",
                            value=str(med.get("cost", 0.0)),
                            meta=med,
                        )
                    )

            # Add general text excerpt
            text_entity = KadiEntity(
                id=f"ENT-TEXT-{uuid.uuid4().hex[:8]}",
                name="Document Text Excerpt",
                type="document_text",
                value=text[:1000],
                meta={"source_file": filename},
            )
            entities_to_add.append(text_entity)

            # Link entities to case
            case.entities.extend(entities_to_add)
            if total_cost > 0:
                case.total_charged += total_cost
            elif extracted.total_amount and extracted.total_amount > 0:
                case.total_charged += extracted.total_amount

            session.add(case)
            session.add_all(entities_to_add)
            await session.commit()

        processing_status[case_id].append({"status": "completed", "progress": 100, "log": "Document processed successfully. Entities extracted."})
        logger.info(f"Background task succeeded for case={case_id}. Extracted {len(entities_to_add)} entities.")
    except Exception as e:
        logger.error(f"Background task failed for case={case_id}: {e}", exc_info=True)
        processing_status[case_id].append({"status": "failed", "progress": 100, "log": f"Failed: {str(e)}"})


# --- Route Implementations ----------------------------------------------------

@router.post("/cases", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(case_in: CaseCreate, db: AsyncSession = Depends(get_db)):
    """Creates a new patient case session."""
    case_id = f"CASE-{uuid.uuid4().hex[:8]}"
    case = KadiCase(
        id=case_id,
        consent_opt_in=case_in.consent_opt_in,
        status="active",
        total_charged=0.0
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return case


@router.post("/cases/{case_id}/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    case_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Uploads a clinical or financial document, scheduling background OCR extraction."""
    # 1. Verify case exists
    result = await db.execute(select(KadiCase).where(KadiCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # 2. Read bytes
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty document uploaded")

    # Initialize status stream logs
    processing_status[case_id] = [{"status": "upload_received", "progress": 10, "log": "Upload received. Queueing document extraction task..."}]

    # 3. Queue processing task
    background_tasks.add_task(
        process_document_background,
        case_id=case_id,
        file_bytes=file_bytes,
        filename=file.filename
    )
    
    return {
        "status": "processing",
        "message": "Document uploaded successfully and queued for OCR extraction.",
        "case_id": case_id,
        "filename": file.filename
    }


@router.get("/cases/{case_id}/stream")
async def stream_processing_status(case_id: str):
    """Event stream route providing real-time document processing updates."""
    async def event_generator():
        last_index = 0
        while True:
            status_list = processing_status.get(case_id, [])
            if last_index < len(status_list):
                for item in status_list[last_index:]:
                    yield f"data: {json.dumps(item)}\n\n"
                last_index = len(status_list)
                if status_list and status_list[-1].get("status") in ["completed", "failed"]:
                    break
            await asyncio.sleep(0.3)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/cases/{case_id}", response_model=CaseDetailResponse)
async def get_case(case_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves case details and all associated extracted entities."""
    result = await db.execute(select(KadiCase).where(KadiCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Load entities
    entities_result = await db.execute(
        select(KadiEntity).join(KadiCase.entities).where(KadiCase.id == case_id)
    )
    entities = entities_result.scalars().all()

    return {
        "case": case,
        "entities": entities
    }

