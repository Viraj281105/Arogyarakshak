"""
Kadi API Endpoints.

Handles case creation, document uploads (OCR parsing), and entity extraction/retrieval.
"""

from typing import Any, Dict, List, Optional
import uuid
import logging
import json
import asyncio

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import KadiCase, KadiEntity
# We can import ocr parser from kadi local package!
from kadi.ocr.ocr_parser import parse_document

logger = logging.getLogger("arogyarakshak.api.kadi")
router = APIRouter()

# In-memory document processing status stream mapping
processing_status: Dict[str, List[Dict[str, Any]]] = {}



# --- Pydantic Schemas ---------------------------------------------------------
class CaseCreate(BaseModel):
    consent_opt_in: bool = Field(default=False, description="Patient opt-in for cross-module context sharing")


class CaseResponse(BaseModel):
    id: str
    status: str
    consent_opt_in: bool
    total_charged: float
    created_at: Any

    class Config:
        from_attributes = True


class EntityResponse(BaseModel):
    id: str
    name: str
    type: str
    value: Optional[str]
    meta: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class CaseDetailResponse(BaseModel):
    case: CaseResponse
    entities: List[EntityResponse]


# --- Async Helper Task --------------------------------------------------------
async def process_document_background(case_id: str, file_bytes: bytes, filename: str, db: AsyncSession):
    """Processes document upload in a background task, saving extracted entities."""
    logger.info(f"Background task starting: OCR parsing for case={case_id}, file={filename}")
    try:
        # Step 1: OCR parsing
        processing_status[case_id].append({"status": "ocr_start", "progress": 30, "log": "Running document OCR parser..."})
        parsed = parse_document(file_bytes=file_bytes, filename=filename)
        text = parsed.get("full_text_content", "")
        line_items = parsed.get("line_items", [])
        
        # Step 2: Extraction
        processing_status[case_id].append({"status": "extraction_start", "progress": 60, "log": "Extracting entities from parsed text..."})
        await asyncio.sleep(0.5) # Simulate small latency
        
        async with db.begin_nested() if db.in_nested_transaction() else db as session:
            # 2. Retrieve case
            result = await session.execute(select(KadiCase).where(KadiCase.id == case_id))
            case = result.scalar_one_or_none()
            if not case:
                logger.error(f"Case {case_id} not found during background processing.")
                processing_status[case_id].append({"status": "failed", "progress": 100, "log": "Failed: Case not found"})
                return

            # Step 3: Database write
            processing_status[case_id].append({"status": "database_write", "progress": 80, "log": "Saving structured entities to database..."})
            
            # 3. Create active entities
            entities_to_add = []
            total_cost = 0.0
            
            for idx, item in enumerate(line_items):
                entity_id = f"ENT-{uuid.uuid4().hex[:8]}"
                entity = KadiEntity(
                    id=entity_id,
                    name=item["item"],
                    type="billing_item",
                    value=str(item["charged"]),
                    meta={"charged": item["charged"], "source_file": filename},
                )
                entities_to_add.append(entity)
                total_cost += item["charged"]

            # Add general text block as an entity for reference
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
            case.total_charged += total_cost
            
            session.add(case)
            session.add_all(entities_to_add)
            await session.commit()
            
        processing_status[case_id].append({"status": "completed", "progress": 100, "log": "Document processed successfully."})
        logger.info(f"Background task succeeded for case={case_id}. Extracted {len(line_items)} items.")
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
        filename=file.filename,
        db=db
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

