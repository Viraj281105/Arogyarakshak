"""
DaaviSetu API Endpoints.

Handles claim and pre-authorization document generation.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.case_auth import require_case_access
from app.config import settings
from app.consent import require_case_consent
from app.database import get_db
from app.models import DaaviSetuClaim, KadiCase, KadiEntity
# Import daavisetu packages
from daavisetu.generator import generate_claim_package, generate_preauth_pdf, ClaimData, ClaimPackage
from daavisetu.package_assembler import build_claim_package_zip
from daavisetu.schema import get_claim_form_json_schema
from daavisetu.form_filler import fill_pdf_form, list_form_fields, FormFieldInfo, MalformedPdfError

logger = logging.getLogger("arogyarakshak.api.daavisetu")
router = APIRouter()


# --- Pydantic Schemas ---------------------------------------------------------
class PreAuthFormRequest(BaseModel):
    """Pre-authorization intake.

    Optional fields fall back to entities extracted from the case, never to invented
    values. If a field resolves to nothing the request is rejected with 422.
    """

    policy_number: str = Field(..., min_length=1, description="Insurance policy ID")
    patient_name: str = Field(..., min_length=1, description="Full name of the patient")
    hospital_name: Optional[str] = Field(None, description="Network hospital name")
    diagnosis: Optional[str] = Field(None, description="Clinical diagnosis or ICD-10 code")
    treatment_plan: Optional[str] = Field(None, description="Proposed surgical/medical procedure")
    estimated_cost: Optional[float] = Field(
        None, ge=0, description="Estimated treatment cost; defaults to the audited case total"
    )
    sum_insured: Optional[float] = Field(
        None,
        ge=0,
        description="Policy's maximum sum insured, as declared by the policyholder. "
        "Policy-limit validation (#84) is skipped when omitted.",
    )


def _first_entity(entities, entity_type: str) -> Optional[str]:
    """Returns the first extracted entity name of a given type, if any."""
    for entity in entities:
        if entity.type == entity_type and entity.name:
            return entity.name
    return None



# --- Route Implementations ----------------------------------------------------

@router.post("/cases/{case_id}/claim", response_model=ClaimPackage, status_code=status.HTTP_200_OK)
async def generate_pre_auth_form(
    case_id: str,
    req: PreAuthFormRequest,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Pre-populates a cashless pre-authorization form based on user input and case entities."""
    case = require_case_consent(case)

    # 2. Gather entities extracted from this case's uploaded documents.
    entities_result = await db.execute(
        select(KadiEntity).join(KadiCase.entities).where(KadiCase.id == case_id)
    )
    entities = entities_result.scalars().all()
    
    # Resolve each field: caller-supplied value, else an entity actually extracted from
    # the uploaded document. There is no third tier — a pre-authorization form is filed
    # with an insurer, so an invented hospital, diagnosis, treatment or cost is worse than
    # refusing to generate the form.
    hospital = req.hospital_name or _first_entity(entities, "hospital")
    diagnosis = req.diagnosis or _first_entity(entities, "diagnosis")
    treatment = req.treatment_plan or _first_entity(entities, "procedure")

    estimated_cost = req.estimated_cost
    if estimated_cost is None and case.total_charged > 0:
        estimated_cost = case.total_charged

    missing = [
        name
        for name, value in (
            ("hospital_name", hospital),
            ("diagnosis", diagnosis),
            ("treatment_plan", treatment),
            ("estimated_cost", estimated_cost),
        )
        if not value
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": (
                    "Cannot generate a pre-authorization form: these fields were neither "
                    "supplied nor found in the uploaded document. Provide them explicitly "
                    "rather than accepting a default."
                ),
                "missing_fields": missing,
            },
        )

    # 3. Create input and execute daavisetu claim generation
    claim_input = ClaimData(
        policy_number=req.policy_number,
        patient_name=req.patient_name,
        hospital_name=hospital,
        diagnosis=diagnosis,
        estimated_cost=estimated_cost,
        treatment_plan=treatment,
        sum_insured=req.sum_insured,
    )

    package = generate_claim_package(case_id=case_id, claim_input=claim_input)

    # 4. Persist the submitted form. This is what the PDF download renders, so the
    #    document the patient signs matches exactly what they submitted here.
    existing = await db.execute(
        select(DaaviSetuClaim).where(DaaviSetuClaim.case_id == case_id)
    )
    claim_record = existing.scalar_one_or_none()

    if claim_record is None:
        claim_record = DaaviSetuClaim(id=package.claim_id, case_id=case_id)
        db.add(claim_record)

    claim_record.policy_number = claim_input.policy_number
    claim_record.patient_name = claim_input.patient_name
    claim_record.hospital_name = claim_input.hospital_name
    claim_record.diagnosis = claim_input.diagnosis
    claim_record.estimated_cost = claim_input.estimated_cost
    claim_record.treatment_plan = claim_input.treatment_plan
    claim_record.sum_insured = claim_input.sum_insured
    claim_record.status = package.status

    await db.commit()

    logger.info(
        "[DaaviSetu] Persisted claim %s for case %s", claim_record.id, case_id
    )
    return package


async def _load_submitted_claim(case_id: str, db: AsyncSession) -> DaaviSetuClaim:
    """Fetches the case's submitted claim, or raises 409 rather than guessing.

    Shared by the PDF and ZIP-package downloads (#81): both must render strictly from
    what was actually submitted via POST .../claim, never from a reconstructed default.
    """
    claim_result = await db.execute(
        select(DaaviSetuClaim).where(DaaviSetuClaim.case_id == case_id)
    )
    claim_record = claim_result.scalar_one_or_none()
    if claim_record is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No pre-authorization claim has been submitted for this case. "
                f"POST /api/v1/daavisetu/cases/{case_id}/claim first."
            ),
        )
    return claim_record


def _claim_data_from_record(claim_record: DaaviSetuClaim) -> ClaimData:
    return ClaimData(
        policy_number=claim_record.policy_number,
        patient_name=claim_record.patient_name,
        hospital_name=claim_record.hospital_name,
        diagnosis=claim_record.diagnosis,
        estimated_cost=claim_record.estimated_cost,
        treatment_plan=claim_record.treatment_plan,
        sum_insured=claim_record.sum_insured,
    )


@router.get("/cases/{case_id}/claim/pdf")
async def download_preauth_pdf(
    case_id: str,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Downloads the compiled IRDAI Standard Pre-Authorization Form (Annexure-B) PDF.

    Renders strictly from the claim submitted via POST .../claim. Nothing on this form is
    invented: a pre-authorization form is signed and filed with an insurer, so a
    fabricated policy number or a placeholder patient name would be worse than no form.
    If no claim has been submitted yet, this returns 409 rather than guessing.
    """
    require_case_consent(case)
    claim_record = await _load_submitted_claim(case_id, db)
    claim_input = _claim_data_from_record(claim_record)

    pdf_bytes = generate_preauth_pdf(claim_id=claim_record.id, claim_input=claim_input)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=preauth_{case_id}.pdf"},
    )


@router.get("/cases/{case_id}/claim/package")
async def download_claim_package(
    case_id: str,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Downloads a ZIP claim package (#81): the pre-auth PDF, a redacted case-summary
    text excerpt (if Kadi extracted one), and a manifest disclosing exactly what is and
    is not included — see daavisetu.package_assembler for why the original scanned bill
    cannot be included (ArogyaRakshak's zero-retention policy never stores it).
    """
    require_case_consent(case)
    claim_record = await _load_submitted_claim(case_id, db)
    claim_input = _claim_data_from_record(claim_record)
    pdf_bytes = generate_preauth_pdf(claim_id=claim_record.id, claim_input=claim_input)

    text_entity_result = await db.execute(
        select(KadiEntity)
        .join(KadiCase.entities)
        .where(KadiCase.id == case_id, KadiEntity.type == "document_text")
    )
    text_entity = text_entity_result.scalars().first()
    case_summary_text = text_entity.value if text_entity else None

    zip_bytes = build_claim_package_zip(
        claim_id=claim_record.id,
        case_id=case_id,
        preauth_pdf_bytes=pdf_bytes,
        case_summary_text=case_summary_text,
    )
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=claim_package_{case_id}.zip"},
    )


@router.get("/claim-form-schema")
async def claim_form_schema() -> Dict[str, Any]:
    """Returns the universal claim form JSON Schema (#79): DaaviSetu's canonical claim
    fields, annotated with the Annexure-B form section each maps to. Static and
    case-independent, so it takes no case_id and no consent check."""
    return get_claim_form_json_schema()


async def _read_template_upload(template: UploadFile) -> bytes:
    """Reads an uploaded template PDF with the same size guard Kadi's document
    upload uses — an unbounded read here is the same DoS vector, just on a
    different endpoint."""
    template_bytes = await template.read(settings.max_upload_bytes + 1)
    if len(template_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Template exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit.",
        )
    return template_bytes


@router.post("/claim-template/inspect", response_model=List[FormFieldInfo])
async def inspect_claim_template(template: UploadFile = File(...)):
    """Lists the fillable AcroForm field names in a caller-supplied PDF (#80), so a
    user can map DaaviSetu's canonical field names (see /claim-form-schema, #79) onto
    their own insurer's real template. ArogyaRakshak ships no insurer's proprietary
    form of its own — the caller supplies their own."""
    template_bytes = await _read_template_upload(template)
    try:
        return list_form_fields(template_bytes)
    except MalformedPdfError as e:
        # SEC-12: a corrupted/non-PDF upload is a client error, not a server crash.
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/cases/{case_id}/claim/fill-template")
async def fill_claim_template(
    case_id: str,
    template: UploadFile = File(...),
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
):
    """Fills a caller-supplied fillable PDF template with this case's submitted claim
    fields (#80). The template's AcroForm field names must match DaaviSetu's canonical
    names (patient_name, policy_number, hospital_name, diagnosis, treatment_plan,
    estimated_cost) — use POST /claim-template/inspect first to check a template's
    actual field names before relying on this to fill it correctly."""
    require_case_consent(case)
    claim_record = await _load_submitted_claim(case_id, db)
    claim_input = _claim_data_from_record(claim_record)

    template_bytes = await _read_template_upload(template)
    field_values = {
        "patient_name": claim_input.patient_name,
        "policy_number": claim_input.policy_number,
        "hospital_name": claim_input.hospital_name,
        "diagnosis": claim_input.diagnosis,
        "treatment_plan": claim_input.treatment_plan,
        "estimated_cost": f"{claim_input.estimated_cost:,.2f}",
    }
    try:
        filled_bytes = fill_pdf_form(template_bytes, field_values)
    except MalformedPdfError as e:
        # SEC-12: a corrupted/non-PDF upload is a client error, not a server crash.
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    return Response(
        content=filled_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=filled_template_{case_id}.pdf"},
    )
