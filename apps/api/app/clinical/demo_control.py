"""
Demo kit control: status, reset and scenario loading (demo mode only).

A judge demo must be recoverable. This module restores a known starting state without
touching anything that is not demo data:

* "Demo cases" are identified by evidence, not by a flag: a case is a demo case when one
  of its ingested documents has the SHA-256 of a committed synthetic demo document
  (`demo/documents/*`). Cases with any other upload are left alone and reported as kept.
* Demo reviewers keep their ids; their credentials are rotated and they are reactivated
  (by the existing seed). Case-scoped review/transcription state goes with the cases.
* Demo safety rules (and any rule a demo persona proposed, e.g. a new version drafted
  during a demo) are removed with their approvals and re-seeded ACTIVE, so a rule retired
  in Scenario D escalates again after a reset.
* Global audit events are append-only and are NOT deleted; a reset adds a DEMO_RESET event.

Every entry point is refused unless `settings.demo_operations_allowed` (demo mode on and
APP_ENV not "production"), and the routes additionally require the governance key.
Operations are serialised by one in-process lock, so double-clicks cannot interleave.
"""

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clinical.audit import record_event
from app.clinical.demo import seed_demo
from app.clinical.demo_ocr import DEMO_PRESCRIPTION_SHA256
from app.config import settings
from app.models import (
    KadiCase,
    KadiCaseDocument,
    KadiClinicalReviewer,
    KadiSafetyRule,
    KadiSafetyRuleApproval,
)

logger = logging.getLogger("arogyarakshak.demo")

# One demo operation at a time per API process (reset, load). A second click waits for
# the first to finish instead of interleaving deletes with inserts.
_demo_lock = asyncio.Lock()

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "A": {
        "title": "Clinical review → doctor-authored statement → appeal PDF",
        "module": "BillNyay",
        "documents": ["A_hospital_bill.txt", "A_discharge_summary.txt"],
        "starting_state": "A new case holding the synthetic hospital bill and its discharge summary, both processed.",
        "actions": [
            "BillNyay → Run CGHS benchmark audit.",
            "Check clinical plausibility (expect: clinical review recommended).",
            "Request a clinical review and assign Dr. Demo Clinician A by reviewer ID.",
            "Reviewer workspace (Clinician A's token): declare conflict of interest, accept, open evidence, write, lock, finalize.",
            "Patient: refresh the review panel, draft the appeal, download the signed PDF.",
        ],
        "expected": "The finalized statement appears badged Human-authored; the PDF annex carries it verbatim.",
    },
    "B": {
        "title": "Pre-authorization readiness + missing clinical confirmation",
        "module": "DaaviSetu",
        "documents": ["B_preauth_request.txt"],
        "starting_state": "A new case holding the synthetic pre-authorization request, processed.",
        "actions": [
            "DaaviSetu → Check documentation readiness with the demo playbook and institution credential.",
            "Ask a doctor to confirm the item marked 'Needs a doctor's confirmation'; assign Dr. Demo Clinician B.",
            "Reviewer (Clinician B): accept, record a decision.",
        ],
        "expected": "USG found (weak keyword evidence), LFT not found, conservative management needs a doctor; no approval probability anywhere.",
    },
    "C": {
        "title": "Uncertain medicine OCR + two-reader agreement / disagreement",
        "module": "DawaCheck",
        "documents": ["C_prescription_uncertain.png"],
        "starting_state": "A new case holding the synthetic prescription, processed with the recorded OCR replay.",
        "actions": [
            "DawaCheck → Medicines from your documents shows each trust decision.",
            "Assign both demo readers (pharmacist, transcriptionist) to the unclear line.",
            "Readers type the line blind; when they agree, Augmentin is price-checked per tablet.",
        ],
        "expected": "Augmentin ₹22.00 per tablet vs ₹20.10 ceiling → above ceiling; Pan 40 / Pan-D / Amoxicillin stay held back; Dolo 650 within ceiling.",
    },
    "D": {
        "title": "Safety escalation",
        "module": "Kadi / BimaNyay",
        "documents": ["D_insurance_denial_letter.txt"],
        "starting_state": "A new case holding the synthetic denial letter, processed; the two demo safety rules are active.",
        "actions": [
            "Observe the red 'Clinical safety check' banner above the modules.",
            "Optional: BimaNyay → analyse the denial.",
            "Optional: reviewer workspace → Safety governance → request retirement (needs a second board member).",
        ],
        "expected": "Escalation 'Possible stroke warning signs (FAST)', severity Urgent, matched words shown, floor disclaimer.",
    },
    "E": {
        "title": "Diabetes admission: documentation readiness + missing document",
        "module": "DaaviSetu",
        "documents": ["E_diabetes_admission_note.txt"],
        "starting_state": "A new case holding the synthetic diabetes admission note, processed.",
        "actions": [
            "DaaviSetu → Check documentation readiness with the demo diabetes playbook ID and institution credential.",
            "Ask a doctor to confirm the item marked 'Needs a doctor's confirmation'; assign Dr. Demo Clinician B.",
            "Reviewer (Clinician B): accept, record a decision; patient re-checks readiness.",
        ],
        "expected": "HbA1c and blood glucose found (weak keyword evidence), renal function not found, treatment history needs a doctor; paperwork only, no interpretation of any value, no approval probability.",
    },
}


def demo_documents_path() -> Path:
    if settings.demo_documents_dir:
        return Path(settings.demo_documents_dir)
    # Local checkout: <repo>/apps/api/app/clinical/demo_control.py -> <repo>/demo/documents.
    # API image: the Dockerfile copies them to /app/demo/documents.
    parents = Path(__file__).resolve().parents
    local = parents[4] / "demo" / "documents" if len(parents) > 4 else None
    if local is not None and local.is_dir():
        return local
    return Path("/app/demo/documents")


def _document_digests() -> Set[str]:
    digests = {DEMO_PRESCRIPTION_SHA256}
    root = demo_documents_path()
    names = {name for spec in SCENARIOS.values() for name in spec["documents"]}
    for name in names:
        path = root / name
        if path.is_file():
            digests.add(hashlib.sha256(path.read_bytes()).hexdigest())
    return digests


def simulated_components() -> List[Dict[str, str]]:
    """What is real and what is simulated in THIS running configuration (the extraction
    line depends on whether a Groq key is configured)."""
    groq = bool(settings.groq_api_key)
    return [
        {
            "item": "Patients, hospitals, insurers and documents",
            "status": "SIMULATED",
            "detail": "Every demo document is synthetic and labelled so. No real person or organisation is represented.",
        },
        {
            "item": "Scenario C OCR confidences and extraction",
            "status": "SIMULATED",
            "detail": "Replayed from a recorded fixture for the committed prescription image only, so the demo is reproducible. Everything after extraction is the real pipeline.",
        },
        {
            "item": "Reviewer personas and their verification",
            "status": "SIMULATED",
            "detail": "Dr. Demo Clinician A/B are demo personas labelled 'Demo verification only'. No reviewer is checked against a real medical or pharmacy council.",
        },
        {
            "item": "Safety rules",
            "status": "SIMULATED",
            "detail": "Two demo rules (FAST stroke signs, WHO ETAT emergency signs) approved by demo personas; sources cited by title only.",
        },
        {
            "item": "Demo institution and pre-auth playbook",
            "status": "SIMULATED",
            "detail": "A fictional insurance desk and an illustrative checklist — not real insurer guidance.",
        },
        {
            "item": "Entity extraction",
            "status": "REAL" if groq else "REAL (rule-based)",
            "detail": (
                "Groq LLM extraction — output can vary between runs."
                if groq
                else "Deterministic rule-based extraction (GROQ_API_KEY is not set on this server)."
            ),
        },
        {
            "item": "Everything else",
            "status": "REAL",
            "detail": "Upload, transient processing, entity resolution, trust gate, human-reading consensus, DawaCheck price-basis check, CGHS audit, plausibility, safety evaluation, review lifecycle, audit trail, PDF signing.",
        },
    ]


def demo_status() -> Dict[str, Any]:
    enabled = settings.demo_operations_allowed
    return {
        "demo_mode": enabled,
        "banner": "DEMO MODE — synthetic patient data · deterministic OCR replay for Scenario C" if enabled else None,
        "simulated": simulated_components() if enabled else [],
        "scenarios": (
            [{"id": sid, **{k: v for k, v in spec.items()}} for sid, spec in SCENARIOS.items()] if enabled else []
        ),
        # Only meaningful (and only disclosed) on a demo server.
        "governance_configured": bool(settings.clinical_governance_admin_key) if enabled else False,
    }


async def _demo_case_ids(db: AsyncSession) -> List[str]:
    digests = _document_digests()
    rows = await db.execute(select(KadiCaseDocument.case_id).where(KadiCaseDocument.sha256.in_(digests)).distinct())
    return sorted({r[0] for r in rows.all()})


async def _demo_reviewer_ids(db: AsyncSession) -> List[str]:
    rows = await db.execute(select(KadiClinicalReviewer.id).where(KadiClinicalReviewer.is_demo.is_(True)))
    return [r[0] for r in rows.all()]


async def _remove_demo_rules(db: AsyncSession, demo_reviewer_ids: List[str]) -> int:
    cond = KadiSafetyRule.is_demo.is_(True)
    if demo_reviewer_ids:
        cond = cond | KadiSafetyRule.proposed_by.in_(demo_reviewer_ids)
    rule_ids = [r[0] for r in (await db.execute(select(KadiSafetyRule.id).where(cond))).all()]
    if rule_ids:
        await db.execute(delete(KadiSafetyRuleApproval).where(KadiSafetyRuleApproval.rule_id.in_(rule_ids)))
        await db.execute(delete(KadiSafetyRule).where(KadiSafetyRule.id.in_(rule_ids)))
    return len(rule_ids)


def _require_allowed() -> None:
    if not settings.demo_operations_allowed:
        raise PermissionError(
            "Demo operations are disabled: CLINICAL_DEMO_MODE is off or APP_ENV is production."
        )


async def reset_demo(db: AsyncSession) -> Dict[str, Any]:
    """Deletes demo cases, restores demo rules and rotates demo credentials. Idempotent:
    a second reset finds no demo cases and restores the same rule set."""
    _require_allowed()
    # Local import: the purge cascade lives with the case routes (shared with DELETE and
    # the retention sweep); importing at module load would be circular.
    from app.api.v1.endpoints.kadi import processing_status, purge_case

    async with _demo_lock:
        case_ids = await _demo_case_ids(db)
        for case_id in case_ids:
            await purge_case(db, case_id)
            processing_status.pop(case_id, None)
        other_cases = len((await db.execute(select(KadiCase.id))).all())  # what is left
        rules_removed = await _remove_demo_rules(db, await _demo_reviewer_ids(db))
        await db.flush()
        seeded = await seed_demo(db)  # commits
        record_event(
            db,
            event_type="DEMO_RESET",
            subject_type="demo_kit",
            subject_id="demo",
            actor_type="governance_admin",
            details={"cases_removed": len(case_ids), "rules_reseeded": len(seeded.get("safety_rules_created", []))},
        )
        await db.commit()
        logger.info("Demo reset: %d demo case(s) removed, %d demo rule(s) re-seeded.", len(case_ids), rules_removed)
        return {
            "status": "reset",
            "demo_cases_removed": len(case_ids),
            "other_cases_kept": other_cases,
            "demo_rules_restored": len(seeded.get("safety_rules_created", [])),
            "credentials": seeded,
        }


async def load_scenario(db: AsyncSession, scenario_id: str) -> Dict[str, Any]:
    """Creates a fresh case for the scenario and runs its synthetic documents through the
    real upload pipeline (the same `process_document_background` a patient upload uses),
    returning once processing has finished."""
    _require_allowed()
    from app.api.v1.endpoints.kadi import create_case_record, ingest_document_now

    spec = SCENARIOS.get(scenario_id.upper())
    if spec is None:
        raise KeyError(scenario_id)
    root = demo_documents_path()
    missing = [n for n in spec["documents"] if not (root / n).is_file()]
    if missing:
        raise FileNotFoundError(f"Demo documents not found in {root}: {', '.join(missing)}")

    async with _demo_lock:
        seeded: Optional[Dict[str, Any]] = None
        if not await _demo_reviewer_ids(db):
            # First use: nothing seeded yet. Seed so the scenario's reviewers and rules exist.
            seeded = await seed_demo(db)
        case, token = await create_case_record(db, consent_opt_in=True)
        outcomes = []
        for name in spec["documents"]:
            outcomes.append(await ingest_document_now(db, case.id, (root / name).read_bytes(), name))
        return {
            "scenario": scenario_id.upper(),
            "title": spec["title"],
            "case_id": case.id,
            "access_token": token,
            "documents": spec["documents"],
            "processing": outcomes,
            "credentials": seeded,
        }
